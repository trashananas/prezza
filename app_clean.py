# Основной файл Streamlit-приложения для MVP AI-суфлёра презентаций
import streamlit as st
import streamlit.components.v1 as components
from modules.presentation import parse_presentation
from modules.ai import generate_plan_and_script, stream_generate_plan_and_script
from modules.speech import listen_and_suggest
import hashlib
import uuid

st.set_page_config(page_title="AI Суфлёр для презентаций", layout="wide")
st.title("AI Суфлёр для презентаций")

uploaded_file = st.file_uploader("Загрузите презентацию (PDF или PPTX)", type=["pdf", "pptx"])

if uploaded_file:
    slides = parse_presentation(uploaded_file)
    if len(slides) > 10:
        st.warning("Слишком много слайдов! Для теста обработаем только первые 10.")
        slides = slides[:10]
    if st.button("Сгенерировать план и текст для слайдов (стриминг через Ollama)"):
        if all(not s['content'].strip() for s in slides):
            st.error("Не удалось извлечь текст из презентации. Проверьте файл.")
        else:
            import streamlit_notify as notify
            st.session_state["plan_and_script"] = [{} for _ in slides]
            placeholder = st.empty()
            for idx, partial in stream_generate_plan_and_script(slides):
                st.session_state["plan_and_script"][idx] = partial
                with placeholder.container():
                    st.header("Суфлёр (генерация в реальном времени)")
                    for i, slide in enumerate(st.session_state["plan_and_script"], 1):
                        st.subheader(f"Слайд {i}")
                        if "tosay" in slide:
                            tosay_list = slide['tosay'] if slide['tosay'] else []
                            tosay_hash = hashlib.md5("|".join(tosay_list).encode('utf-8')).hexdigest()[:8] if tosay_list else str(uuid.uuid4())
                            multiselect_key = f"multitosay_{i}_{tosay_hash}"
                            selected = st.multiselect(
                                "Отметьте сказанные тезисы:",
                                options=tosay_list,
                                default=st.session_state.get(multiselect_key, []),
                                key=multiselect_key
                            )
                            st.markdown("**TOSAY (тезисы, которые надо обязательно сказать):**")
                            for thesis in tosay_list:
                                if thesis in selected:
                                    st.markdown(f"- ~~{thesis}~~")
                                else:
                                    st.markdown(f"- {thesis}")
                            components.html("""
                            <script>
                            window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' });
                            </script>
                            """, height=0)
                        if "script" in slide:
                            st.markdown("**Текст рассказчика:**")
                            st.write(slide['script'])
            # notify.notify("Генерация завершена!")

if "plan_and_script" in st.session_state:
    st.header("Суфлёр")
    for idx, slide in enumerate(st.session_state["plan_and_script"], 1):
        st.subheader(f"Слайд {idx}")
        tosay_key = f'tosay_{idx}'
        tosay_len = len(slide['tosay'])
        if tosay_key not in st.session_state or len(st.session_state[tosay_key]) != tosay_len:
            st.session_state[tosay_key] = [False] * tosay_len
        st.markdown("**TOSAY (тезисы, которые надо обязательно сказать):**")
        for i, thesis in enumerate(slide['tosay']):
            key = f'{tosay_key}_{i}'
            # Клик по строке меняет состояние зачёркивания
            if st.button(f"{'~~' if st.session_state[tosay_key][i] else ''}{thesis}{'~~' if st.session_state[tosay_key][i] else ''}", key=key):
                st.session_state[tosay_key][i] = not st.session_state[tosay_key][i]
            # Визуализация зачёркнутого или обычного тезиса
            if st.session_state[tosay_key][i]:
                st.markdown(f"- ~~{thesis}~~")
            else:
                st.markdown(f"- {thesis}")
