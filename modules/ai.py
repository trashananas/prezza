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
        try:
            from llama_cpp import Llama
        except ImportError:
            msg = (
                "\n[Ошибка] Библиотека 'llama-cpp-python' не установлена или не скомпилирована.\n"
                "Пожалуйста, выполните команду:\n"
                "pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu\n"
                "Подробности в README.md"
            )
            print(msg)
            raise ImportError(msg)

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
        "Ты — профессиональный ассистент по подготовке презентаций.\n"
        f"Твоя задача: подготовить план-суфлер для слайда номер {slide_num} (всего слайдов: {total}).\n\n"
        "### ПРАВИЛА:\n"
        "1. ВЕСЬ ответ должен быть СТРОГО НА РУССКОМ ЯЗЫКЕ.\n"
        "2. НЕ используй английский или другие языки, даже для терминов.\n"
        "3. Обязательно сохрани все цифры, даты, проценты и факты из текста слайда.\n"
        "4. Если на слайде есть таблица — обязательно прокомментируй её ключевые показатели.\n\n"
        "### ФОРМАТ ОТВЕТА (СТРОГО):\n"
        "TOSAY:\n"
        "- Тезис 1\n"
        "- Тезис 2\n"
        "...\n"
        "SCRIPT:\n"
        "Полный текст выступления для этого слайда. Речь должна быть живой и связной.\n\n"
        "### КОНТЕНТ СЛАЙДА:\n"
        f"{slide_content}\n\n"
        f"{history}\n"
        f"{special}\n"
        "---"
    )


def _parse_partial(partial):
    """Разбирает накопленный текст ответа на tosay и script."""
    tosay, script = [], ""
    if "TOSAY:" in partial:
        parts = partial.split("TOSAY:", 1)[1]
        if "SCRIPT:" in parts:
            tosay_part, script_part = parts.split("SCRIPT:", 1)
            tosay = [
                line.strip("-• ").strip()
                for line in tosay_part.strip().splitlines()
                if line.strip("-• ").strip()
            ]
            script = script_part.strip()
        else:
            tosay = [
                line.strip("-• ").strip()
                for line in parts.strip().splitlines()
                if line.strip("-• ").strip()
            ]
    else:
        script = partial.strip()
    return tosay, script


def stream_generate_plan_and_script(slides):
    """Генерирует план и текст для слайдов в режиме стриминга."""
    llm = get_llm()
    total = len(slides)
    prev_scripts = []

    for idx, slide in enumerate(slides):
        if not slide["content"].strip():
            yield idx, {"tosay": ["[Слайд пуст]"], "script": "На этом слайде нет текста."}
            continue

        slide_num = idx + 1
        prompt_content = slide["content"]

        history = ""
        if prev_scripts:
            history = "### ПРЕДЫДУЩИЙ КОНТЕКСТ:\n" + prev_scripts[-1][:200] + "..."

        special = ""
        if idx == 0:
            special = "### ДОПОЛНИТЕЛЬНО: Начни с приветствия аудитории."
        elif idx == total - 1:
            special = "### ДОПОЛНИТЕЛЬНО: В конце поблагодари за внимание."

        prompt = _build_prompt(prompt_content, slide_num, total, special, history)

        stream = llm.create_chat_completion(
            messages=[{"role": "user", "content": prompt}],
            stream=True,
            max_tokens=1500,
            temperature=0.7,
        )

        partial = ""
        for chunk in stream:
            delta = chunk["choices"][0]["delta"].get("content", "")
            if delta:
                partial += delta
                tosay, script = _parse_partial(partial)
                yield idx, {"tosay": tosay, "script": script}

        _, final_script = _parse_partial(partial)
        prev_scripts.append(final_script)
