from io import BytesIO
from pypdf import PdfReader

def extract_text_from_pdf_bytes(content: bytes) -> str:
    reader = PdfReader(BytesIO(content))
    pages_text = []

    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            pages_text.append(text.strip())

    return "\n\n".join(pages_text)