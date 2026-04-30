# Основной файл Streamlit-приложения для MVP AI-суфлёра презентаций

import streamlit as st


from modules.ai import stream_generate_plan_and_script
from modules.presentation import parse_presentation
from modules.speech import listen_and_suggest

st.set_page_config(page_title="AI Суфлёр для презентаций", layout="wide")
st.title("AI Суфлёр для презентаций")


import json
from io import StringIO

uploaded_file = st.file_uploader("Загрузите презентацию (PDF, PPTX или экспортированный TXT)", type=["pdf", "pptx", "txt"])




if uploaded_file:
    if uploaded_file.name.lower().endswith('.txt'):
        # Импорт из txt/json
        try:
            imported = json.load(uploaded_file)
            if isinstance(imported, list) and all(isinstance(x, dict) for x in imported):
                st.session_state["plan_and_script"] = imported
                st.success("План и сценарий успешно импортированы!")
            else:
                st.error("Файл не содержит корректный план и сценарий!")
        except Exception as e:
            st.error(f"Ошибка при импорте: {e}")
        slides = []
    else:
        slides = parse_presentation(uploaded_file)
        if len(slides) > 20:
            st.warning("Слишком много слайдов! Для теста обработаем только первые 20.")
            slides = slides[:20]

    if slides and st.button("Сгенерировать план и текст для слайдов (стриминг через Ollama)"):
        if all(not s["content"].strip() for s in slides):
            st.error("Не удалось извлечь текст из презентации. Проверьте файл.")
        else:
            st.session_state["plan_and_script"] = [{} for _ in slides]

            placeholder = st.empty()

            for idx, partial in stream_generate_plan_and_script(slides):
                st.session_state["plan_and_script"][idx] = partial

                with placeholder.container():
                    st.header("Суфлёр (генерация в реальном времени)")
                    for i, slide in enumerate(st.session_state["plan_and_script"], 1):
                        st.subheader(f"Слайд {i}")
                        tosay_list = slide.get("tosay", []) or []
                        if tosay_list:
                            st.markdown("**TOSAY (тезисы, которые надо обязательно сказать):**\n" + "\n".join(f"- {thesis}" for thesis in tosay_list))

            # После завершения генерации показать уведомление
            st.success("Генерация плана и текста завершена!")

    if "plan_and_script" in st.session_state:
        st.header("Суфлёр")
        for idx, slide in enumerate(st.session_state["plan_and_script"], 1):
            st.subheader(f"Слайд {idx}")

            tosay_list = slide.get("tosay", []) or []
            tosay_key = f"tosay_{idx}"
            if tosay_key not in st.session_state or len(st.session_state[tosay_key]) != len(tosay_list):
                st.session_state[tosay_key] = [False] * len(tosay_list)

            st.markdown("**TOSAY (тезисы, которые надо обязательно сказать):**")
            for i, thesis in enumerate(tosay_list):
                if st.session_state[tosay_key][i]:
                    st.markdown(f"- ~~{thesis}~~")
                else:
                    st.markdown(f"- {thesis}")

            if "script" in slide:
                st.markdown("**Текст рассказчика:**")
                st.write(slide["script"])

        # Кнопка для скачивания плана и сценария
        st.markdown("---")
        buf = StringIO()
        json.dump(st.session_state["plan_and_script"], buf, ensure_ascii=False, indent=2)
        st.download_button(
            label="Скачать план и сценарий (txt)",
            data=buf.getvalue(),
            file_name="plan_and_script.txt",
            mime="text/plain"
        )

        if st.button("Включить режим прослушивания речи"):
            listen_and_suggest(st.session_state["plan_and_script"])
