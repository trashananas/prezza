import streamlit as st
import json
import html
from io import StringIO
from modules.ai import stream_generate_plan_and_script
from modules.presentation import parse_presentation

st.set_page_config(page_title="AI Суфлёр", layout="wide", initial_sidebar_state="collapsed")

# Кастомный CSS для улучшения интерфейса
st.markdown("""
<style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        height: 3em;
        background-color: #007bff;
        color: white;
    }
    .script-box {
        background-color: white;
        padding: 20px;
        border: 1px solid #dee2e6;
        border-radius: 5px;
        font-size: 1.2em;
        line-height: 1.6;
        white-space: pre-wrap;
    }
</style>
""", unsafe_allow_html=True)

if "plan_and_script" not in st.session_state:
    st.session_state["plan_and_script"] = []
if "current_slide" not in st.session_state:
    st.session_state["current_slide"] = 0

def validate_plan(data):
    """Проверяет структуру импортируемого плана."""
    if not isinstance(data, list):
        return False
    for item in data:
        if not isinstance(item, dict):
            return False
        if "tosay" not in item or "script" not in item:
            return False
    return True

def reset_progress():
    """Сбрасывает текущий слайд и состояние всех чекбоксов."""
    st.session_state["current_slide"] = 0
    # Удаляем ключи чекбоксов из session_state
    keys_to_delete = [key for key in st.session_state.keys() if key.startswith("check_")]
    for key in keys_to_delete:
        del st.session_state[key]

st.title("🚀 AI Суфлёр для презентаций")

# Проверка наличия критических библиотек
libs_ok = True
try:
    import llama_cpp
except ImportError:
    st.error("""
    **Ошибка: Библиотека `llama-cpp-python` не установлена.**

    Для исправления выполните в терминале:
    ```bash
    pip install llama-cpp-python --extra-index-url https://abetlen.github.io/llama-cpp-python/whl/cpu
    ```
    Подробные инструкции в файле `README.md`.
    """)
    libs_ok = False

tabs = st.tabs(["📁 Загрузка", "📝 Редактор", "📺 Суфлёр"])

with tabs[0]:
    st.header("Загрузка презентации")
    uploaded_file = st.file_uploader("Выберите файл (PDF, PPTX или TXT с планом)", type=["pdf", "pptx", "txt"])

    if uploaded_file:
        if uploaded_file.name.lower().endswith('.txt'):
            try:
                imported = json.load(uploaded_file)
                if validate_plan(imported):
                    st.session_state["plan_and_script"] = imported
                    st.success("План успешно импортирован!")
                else:
                    st.error("Неверная структура файла. Ожидался список объектов с полями 'tosay' и 'script'.")
            except Exception as e:
                st.error(f"Ошибка при чтении JSON: {e}")
        else:
            if st.button("Обработать и сгенерировать план", disabled=not libs_ok):
                with st.spinner("Извлечение текста и генерация сценария..."):
                    try:
                        slides = parse_presentation(uploaded_file)
                        st.session_state["plan_and_script"] = [{"tosay": [], "script": "Генерируется..."} for _ in slides]

                        placeholder = st.empty()
                        for idx, partial in stream_generate_plan_and_script(slides):
                            st.session_state["plan_and_script"][idx] = partial
                            with placeholder.container():
                                st.info(f"Генерация слайда {idx+1}/{len(slides)}...")
                        st.success("Готово! Перейдите во вкладку 'Редактор' или 'Суфлёр'.")
                    except Exception as e:
                        st.error(f"Произошла ошибка при генерации: {e}")

with tabs[1]:
    st.header("Редактирование сценария")
    if not st.session_state["plan_and_script"]:
        st.info("Сначала загрузите презентацию.")
    else:
        for i, slide in enumerate(st.session_state["plan_and_script"]):
            with st.expander(f"Слайд {i+1}", expanded=(i == 0)):
                # Редактирование TOSAY
                tosay_list = slide.get("tosay", [])
                tosay_str = "\n".join([f"- {t}" for t in tosay_list])
                new_tosay = st.text_area(f"Тезисы (TOSAY) для слайда {i+1}", tosay_str, key=f"edit_tosay_{i}")

                # Редактирование SCRIPT
                new_script = st.text_area(f"Текст (SCRIPT) для слайда {i+1}", slide.get("script", ""), key=f"edit_script_{i}", height=200)

                # Обновление состояния
                st.session_state["plan_and_script"][i]["tosay"] = [t.strip("- ").strip() for t in new_tosay.splitlines() if t.strip()]
                st.session_state["plan_and_script"][i]["script"] = new_script

        buf = StringIO()
        json.dump(st.session_state["plan_and_script"], buf, ensure_ascii=False, indent=2)
        st.download_button("💾 Скачать план (JSON)", buf.getvalue(), "plan.json", "application/json")

with tabs[2]:
    if not st.session_state["plan_and_script"]:
        st.info("Сначала загрузите презентацию.")
    else:
        slides = st.session_state["plan_and_script"]
        curr_idx = st.session_state["current_slide"]

        # Навигация
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("⬅️ Назад") and curr_idx > 0:
                st.session_state["current_slide"] -= 1
                st.rerun()
        with col2:
            st.markdown(f"<h3 style='text-align: center;'>Слайд {curr_idx + 1} из {len(slides)}</h3>", unsafe_allow_html=True)
            st.progress((curr_idx + 1) / len(slides))
        with col3:
            if st.button("Вперед ➡️") and curr_idx < len(slides) - 1:
                st.session_state["current_slide"] += 1
                st.rerun()

        st.markdown("---")

        # Интерфейс суфлёра
        col_left, col_right = st.columns([1, 2])

        with col_left:
            st.subheader("📌 Тезисы (TOSAY)")
            tosay_list = slides[curr_idx].get("tosay", [])
            for i, thesis in enumerate(tosay_list):
                st.checkbox(thesis, key=f"check_{curr_idx}_{i}")

        with col_right:
            st.subheader("🎤 Текст выступления")
            # Безопасный вывод текста с экранированием HTML
            safe_script = html.escape(slides[curr_idx].get("script", ""))
            st.markdown(f"""
            <div class="script-box">{safe_script}</div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        if st.button("🔄 Сбросить прогресс"):
            reset_progress()
            st.rerun()
