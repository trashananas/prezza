import streamlit as st
import json
from io import StringIO
from modules.ai import stream_generate_plan_and_script
from modules.presentation import parse_presentation

st.set_page_config(page_title="AI Суфлёр", layout="wide", initial_sidebar_state="collapsed")

# Custom CSS for better UI
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
    .tosay-box {
        background-color: #e9ecef;
        padding: 15px;
        border-left: 5px solid #007bff;
        border-radius: 5px;
        margin-bottom: 20px;
    }
    .script-box {
        background-color: white;
        padding: 20px;
        border: 1px solid #dee2e6;
        border-radius: 5px;
        font-size: 1.2em;
        line-height: 1.6;
    }
    .teleprompter-text {
        font-size: 2.5em;
        font-weight: 500;
        text-align: center;
        padding: 40px;
        min-height: 400px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    .thesis-item {
        font-size: 1.5em;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

if "plan_and_script" not in st.session_state:
    st.session_state["plan_and_script"] = []
if "current_slide" not in st.session_state:
    st.session_state["current_slide"] = 0

st.title("🚀 AI Суфлёр для презентаций")

tabs = st.tabs(["📁 Загрузка", "📝 Редактор", "📺 Суфлёр"])

with tabs[0]:
    st.header("Загрузка презентации")
    uploaded_file = st.file_uploader("Выберите файл (PDF, PPTX или TXT с планом)", type=["pdf", "pptx", "txt"])

    col1, col2 = st.columns(2)

    if uploaded_file:
        if uploaded_file.name.lower().endswith('.txt'):
            try:
                imported = json.load(uploaded_file)
                st.session_state["plan_and_script"] = imported
                st.success("План успешно импортирован!")
            except:
                st.error("Ошибка формата файла!")
        else:
            if st.button("Обработать и сгенерировать план"):
                with st.spinner("Извлечение текста и генерация сценария..."):
                    slides = parse_presentation(uploaded_file)
                    st.session_state["plan_and_script"] = [{"tosay": [], "script": "Генерируется..."} for _ in slides]

                    placeholder = st.empty()
                    for idx, partial in stream_generate_plan_and_script(slides):
                        st.session_state["plan_and_script"][idx] = partial
                        with placeholder.container():
                            st.info(f"Генерация слайда {idx+1}/{len(slides)}...")
                    st.success("Готово! Перейдите во вкладку 'Редактор' или 'Суфлёр'.")

with tabs[1]:
    st.header("Редактирование сценария")
    if not st.session_state["plan_and_script"]:
        st.info("Сначала загрузите презентацию.")
    else:
        for i, slide in enumerate(st.session_state["plan_and_script"]):
            with st.expander(f"Слайд {i+1}", expanded=(i == 0)):
                # Edit TOSAY
                tosay_str = "\n".join([f"- {t}" for t in slide.get("tosay", [])])
                new_tosay = st.text_area(f"Тезисы (TOSAY) для слайда {i+1}", tosay_str, key=f"edit_tosay_{i}")

                # Edit SCRIPT
                new_script = st.text_area(f"Текст (SCRIPT) для слайда {i+1}", slide.get("script", ""), key=f"edit_script_{i}", height=200)

                # Update session state
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

        # Navigation
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

        # UI for Teleprompter
        col_left, col_right = st.columns([1, 2])

        with col_left:
            st.subheader("📌 Тезисы (TOSAY)")
            tosay_list = slides[curr_idx].get("tosay", [])
            for i, thesis in enumerate(tosay_list):
                st.checkbox(thesis, key=f"check_{curr_idx}_{i}")

        with col_right:
            st.subheader("🎤 Текст выступления")
            st.markdown(f"""
            <div class="script-box">
                {slides[curr_idx].get("script", "").replace('\n', '<br>')}
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")
        if st.button("🔄 Сбросить прогресс"):
            st.session_state["current_slide"] = 0
            st.rerun()
