def stream_generate_plan_and_script(slides):
    """
    Генерирует план и текст для слайдов в режиме стриминга с учетом номера слайда, общего количества слайдов и истории сценариев.
    На первом слайде — приветствие и представление, на последнем — прощание и приглашение к вопросам, в середине — без повторов.
    Если слайд похож на предыдущий (разница текста минимальна), объединяет их для генерации одного сценария.
    """
    import ollama
    import difflib
    total = len(slides)
    prev_scripts = []
    skip_next = False
    for idx, slide in enumerate(slides):
        if skip_next:
            skip_next = False
            continue
        if not slide['content'].strip():
            yield idx, {"tosay": ["[Нет текста на слайде]"], "script": "[Нет текста на слайде]"}
            continue
        # Проверка на почти одинаковые слайды (например, добавлена только картинка или один тезис)
        if idx > 0:
            prev = slides[idx-1]['content']
            curr = slide['content']
            sm = difflib.SequenceMatcher(None, prev, curr)
            if sm.ratio() > 0.85:
                # Объединяем с предыдущим слайдом
                merged_content = prev + "\n" + curr
                prompt_content = merged_content
                slide_num = f"{idx}/{total} (объединён с предыдущим)"
                skip_next = True
            else:
                prompt_content = slide['content']
                slide_num = f"{idx+1}/{total}"
        else:
            prompt_content = slide['content']
            slide_num = f"{idx+1}/{total}"

        # Формируем историю сценариев
        history = ""
        if prev_scripts:
            history = "\n\nТексты рассказчика предыдущих слайдов:\n" + "\n---\n".join(prev_scripts[-3:])

        # Формируем специальные инструкции для первого и последнего слайда
        special = ""
        if idx == 0:
            special = ("\nВ начале поприветствуй аудиторию и представься так, будто ты докладчик (не ассистент, не бот, не AI). Не упоминай, что ты ассистент или бот. Не пиши 'Меня зовут ... и я ваш ассистент'. Просто начни с приветствия и краткого представления от лица выступающего.")
        elif idx == total-1:
            special = ("\nВ конце сценария корректно попрощайся и пригласи слушателей задать вопросы, например: 'Если у вас есть вопросы — с радостью отвечу!' или 'Буду рад ответить на ваши вопросы'. Не пиши вопросы сам себе. Всё прощание и приглашение к вопросам — только на русском языке.")

        prompt = (
            f"Ты — ассистент для подготовки презентаций. Сейчас ты пишешь сценарий для слайда {slide_num} из {total}.\n"
            f"Текст слайда:\n{prompt_content}\n"
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
        stream = ollama.chat(
            model='llama3',
            messages=[{'role': 'user', 'content': prompt}],
            stream=True
        )
        partial = ""
        for chunk in stream:
            if 'message' in chunk and 'content' in chunk['message']:
                partial += chunk['message']['content']
                # Парсим результат: ищем блоки TOSAY и SCRIPT
                tosay, script = [], ""
                if "TOSAY:" in partial and "SCRIPT:" in partial:
                    tosay_part = partial.split("TOSAY:",1)[1].split("SCRIPT:",1)[0]
                    script = partial.split("SCRIPT:",1)[1].strip()
                    tosay = [line.strip('-• ').strip() for line in tosay_part.strip().splitlines() if line.strip('-• ').strip()]
                else:
                    script = partial.strip()
                # Сохраняем сценарий для истории
                if script and (len(prev_scripts) <= idx):
                    prev_scripts.append(script)
                yield idx, {"tosay": tosay, "script": script}

# Модуль для генерации плана и текста с помощью AI (локальная LLM + Gemini API fallback)
import os
from dotenv import load_dotenv

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# TODO: Подключить локальную open-source LLM (например, через llama-cpp-python или transformers)
# Пример функции для генерации плана и текста с fallback на Gemini API

def generate_plan_and_script(slides):
    import requests
    result = []
    for slide in slides:
        if not slide['content'].strip():
            result.append({
                "tosay": ["[Нет текста на слайде]"],
                "script": "[Нет текста на слайде]"
            })
            continue
        prompt = (
            f"Ты — ассистент для подготовки презентаций. Тебе дан текст слайда: {slide['content']}\n"
            "1. Сначала выдели отдельным списком (TOSAY) ключевые тезисы, которые обязательно нужно озвучить на этом слайде. Не повторяй текст слайда, а переформулируй тезисы своими словами, но по смыслу.\n"
            "2. Затем сгенерируй подробный текст рассказчика на русском языке, который связывает эти тезисы между собой, добавляет плавные переходы, пояснения, примеры, чтобы речь звучала живо и не как чтение со слайда.\n"
            "3. Не используй иностранные языки, кроме цитирования текста слайда, если он не на русском.\n"
            "4. Строго соблюдай структуру ответа:\n"
            "TOSAY:\n- тезис 1\n- тезис 2\n...\nSCRIPT:\nТекст рассказчика...\n"
        )
        print(f"[DEBUG] PROMPT: {prompt}")
        # Сначала пробуем Gemini API
        try:
            api_response = requests.post(
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent",
                params={"key": GEMINI_API_KEY},
                json={"contents": [{"parts": [{"text": prompt}]}]}
            )
            if api_response.ok:
                text = api_response.json()["candidates"][0]["content"]["parts"][0]["text"]
            else:
                raise Exception(f"Ошибка Gemini: {api_response.text}")
        except Exception as e:
            # Fallback на Ollama (Llama3)
            try:
                import ollama
                response = ollama.chat(model='llama3', messages=[{'role': 'user', 'content': prompt}])
                text = response['message']['content']
            except Exception as ollama_e:
                text = f"[Ошибка Gemini: {e}] [Ошибка Ollama: {ollama_e}]"
        # Парсим результат: ищем блоки TOSAY и SCRIPT
        tosay, script = [], ""
        if "TOSAY:" in text and "SCRIPT:" in text:
            tosay_part = text.split("TOSAY:",1)[1].split("SCRIPT:",1)[0]
            script = text.split("SCRIPT:",1)[1].strip()
            tosay = [line.strip('-• ').strip() for line in tosay_part.strip().splitlines() if line.strip('-• ').strip()]
        else:
            script = text.strip()
        result.append({
            "tosay": tosay,
            "script": script
        })
    return result
