# AI Суфлёр для презентаций

Инструмент для автоматической генерации сценария выступления и ключевых тезисов на основе слайдов (PDF/PPTX) с использованием локальной LLM.

## Установка

Для работы приложения необходим Python 3.10+.

1. Клонируйте репозиторий.
2. Создайте виртуальное окружение:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Для Linux/macOS
   # или
   .venv\Scripts\activate     # Для Windows
   ```
3. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

### Особенности установки llama-cpp-python

Библиотека `llama-cpp-python` компилируется при установке, поэтому:

- **На Windows**: У вас должен быть установлен [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/) с компонентом "C++ build tools".
  Если установка через `pip install -r requirements.txt` не удается, попробуйте:
  ```bash
  pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
  ```
- **На macOS (M1/M2/M3)**:
  ```bash
  CMAKE_ARGS="-DLLAMA_METAL=on" pip install llama-cpp-python
  ```

## Запуск

```bash
streamlit run app.py
```

## Использование

1. Перейдите во вкладку **Загрузка** и выберите файл презентации.
2. Нажмите кнопку "Обработать и сгенерировать план".
3. Дождитесь завершения генерации (первый запуск может быть долгим из-за скачивания модели ~2ГБ).
4. Проверьте и отредактируйте сценарий во вкладке **Редактор**.
5. Используйте вкладку **Суфлёр** для выступления!
