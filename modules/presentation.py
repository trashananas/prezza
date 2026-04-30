# Модуль для парсинга презентаций (PDF/PPTX)
import io
import fitz  # PyMuPDF
from pptx import Presentation

def parse_presentation(uploaded_file):
    filename = uploaded_file.name.lower()
    slides = []
    if filename.endswith('.pdf'):
        pdf_bytes = uploaded_file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for i, page in enumerate(doc, 1):
            text = page.get_text().strip()
            slides.append({"title": f"Слайд {i}", "content": text})
    elif filename.endswith('.pptx'):
        pptx_bytes = uploaded_file.read()
        prs = Presentation(io.BytesIO(pptx_bytes))
        for i, slide in enumerate(prs.slides, 1):
            texts = []
            for shape in slide.shapes:
                if hasattr(shape, "text"):
                    texts.append(shape.text)
            slide_text = "\n".join(texts).strip()
            slides.append({"title": f"Слайд {i}", "content": slide_text})
    else:
        slides.append({"title": "Ошибка", "content": "Неподдерживаемый формат файла"})
    return slides
