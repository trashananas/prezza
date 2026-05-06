# Модуль для генерации плана и текста с помощью локальной LLM (llama-cpp-python)
import os
import difflib
from pathlib import Path

MODEL_DIR = Path(__file__).parent.parent / "models"
MODEL_REPO = "bartowski/Llama-3.2-3B-Instruct-GGUF"
MODEL_FILENAME = "Llama-3.2-3B-Instruct-Q4_K_M.gguf"
MODEL_PATH = MODEL_DIR / MODEL_FILENAME

_llm = None


def _ensure_model_downloaded():
    """Загружает модель из HuggingFace, если она ещё не скачана."""
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    if not MODEL_PATH.exists():
        from huggingface_hub import hf_hub_download
        print(f"[AI] Модель не найдена. Загрузка {MODEL_FILENAME} из {MODEL_REPO}...")
        hf_hub_download(
            repo_id=MODEL_REPO,
            filename=MODEL_FILENAME,
            local_dir=str(MODEL_DIR),
        )
        print("[AI] Модель успешно загружена.")


def get_llm():
    """Возвращает инициализированный экземпляр Llama (singleton)."""
    global _llm
    if _llm is None:
        _ensure_model_downloaded()
        from llama_cpp import Llama
        print("[AI] Инициализация модели...")
        _llm = Llama(
            model_path=str(MODEL_PATH),
            n_ctx=4096,
            n_threads=max(1, (os.cpu_count() or 4) // 2),
            verbose=False,
        )
        print("[AI] Модель готова.")
    return _llm


def _build_prompt(slide_content, slide_num, total, special="", history=""):
    return (
        f"Ты — ассистент для подготовки презентаций. Сейчас ты пишешь сценарий для слайда {slide_num} из {total}.\n"
        f"Текст слайда:\n{slide_content}\n"
        "1. Сначала выдели отдельным списком (TOSAY) ключевые тезисы, которые обязательно нужно озвучить на этом слайде. Не повторяй текст слайда, а переформулируй тезисы своими словами, но по смыслу.\n"
        "2. Затем сгенерируй подробный текст рассказчика на русском языке, который связывает эти тезисы между собой, добавляет плавные переходы, пояснения, примеры, чтобы речь звучала живо и не как чтение со слайда.\n"
        "3. Весь текст рассказчика (SCRIPT) должен быть только на русском языке. Английские слова и выражения допускаются только как цитаты из слайда, если они есть в материале. Не пиши сценарий на английском.\n"
        "4. Обязательно сохраняй и проговаривай все числа, проценты, суммы, даты и другие конкретные данные, которые есть на слайде. Не теряй важные цифры и факты из исходного материала.\n"
        "5. Не используй иностранные языки, кроме цитирования текста слайда, если он не на русском.\n"
        "6. Строго соблюдай структуру ответа:\n"
        "TOSAY:\n- тезис 1\n- тезис 2\n...\nSCRIPT:\nТекст рассказчика...\n"
        f"{special}"
        f"{history}"
    )


def _parse_partial(partial):
    """Разбирает накопленный текст ответа на tosay и script."""
    tosay, script = [], ""
    if "TOSAY:" in partial and "SCRIPT:" in partial:
        tosay_part = partial.split("TOSAY:", 1)[1].split("SCRIPT:", 1)[0]
        script = partial.split("SCRIPT:", 1)[1].strip()
        tosay = [
            line.strip("-• ").strip()
            for line in tosay_part.strip().splitlines()
            if line.strip("-• ").strip()
        ]
    else:
        script = partial.strip()
    return tosay, script


def stream_generate_plan_and_script(slides):
    """
    Генерирует план и текст для слайдов в режиме стриминга.
    На первом слайде — приветствие и представление, на последнем — прощание
    и приглашение к вопросам, в середине — без повторов.
    Если слайд похож на предыдущий, объединяет их для генерации одного сценария.
    """
    llm = get_llm()
    total = len(slides)
    prev_scripts = []
    skip_next = False

    for idx, slide in enumerate(slides):
        if skip_next:
            skip_next = False
            continue
        if not slide["content"].strip():
            yield idx, {"tosay": ["[Нет текста на слайде]"], "script": "[Нет текста на слайде]"}
            continue

        # Проверка на почти одинаковые слайды
        if idx > 0:
            prev = slides[idx - 1]["content"]
            curr = slide["content"]
            sm = difflib.SequenceMatcher(None, prev, curr)
            if sm.ratio() > 0.85:
                prompt_content = prev + "\n" + curr
                slide_num = f"{idx}/{total} (объединён с предыдущим)"
                skip_next = True
            else:
                prompt_content = slide["content"]
                slide_num = f"{idx + 1}/{total}"
        else:
            prompt_content = slide["content"]
            slide_num = f"{idx + 1}/{total}"

        history = ""
        if prev_scripts:
            history = "\n\nТексты рассказчика предыдущих слайдов:\n" + "\n---\n".join(prev_scripts[-3:])

        special = ""
        if idx == 0:
            special = (
                "\nВ начале поприветствуй аудиторию и представься так, будто ты докладчик "
                "(не ассистент, не бот, не AI). Не упоминай, что ты ассистент или бот. "
                "Просто начни с приветствия и краткого представления от лица выступающего."
            )
        elif idx == total - 1:
            special = (
                "\nВ конце сценария корректно попрощайся и пригласи слушателей задать вопросы, "
                "например: 'Если у вас есть вопросы — с радостью отвечу!' или "
                "'Буду рад ответить на ваши вопросы'. Не пиши вопросы сам себе. "
                "Всё прощание и приглашение к вопросам — только на русском языке."
            )

        prompt = _build_prompt(prompt_content, slide_num, total, special, history)

        stream = llm.create_chat_completion(
            messages=[{"role": "user", "content": prompt}],
            stream=True,
            max_tokens=2048,
        )

        partial = ""
        for chunk in stream:
            delta = chunk["choices"][0]["delta"].get("content", "")
            if delta:
                partial += delta
                tosay, script = _parse_partial(partial)
                if script and len(prev_scripts) <= idx:
                    prev_scripts.append(script)
                yield idx, {"tosay": tosay, "script": script}


def generate_plan_and_script(slides):
    """Генерирует план и текст для всех слайдов (без стриминга)."""
    llm = get_llm()
    total = len(slides)
    result = []

    for idx, slide in enumerate(slides):
        if not slide["content"].strip():
            result.append({"tosay": ["[Нет текста на слайде]"], "script": "[Нет текста на слайде]"})
            continue

        slide_num = f"{idx + 1}/{total}"
        prompt = _build_prompt(slide["content"], slide_num, total)

        response = llm.create_chat_completion(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2048,
        )
        text = response["choices"][0]["message"]["content"]
        tosay, script = _parse_partial(text)
        result.append({"tosay": tosay, "script": script})

    return result
