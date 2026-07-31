import os
import uuid
from fastapi import UploadFile
from app.core.config import settings
from app.documents.schemas import UploadResponse
from app.documents.exceptions import InvalidFileTypeException, FileTooLargeException

# Todo PDF real empieza con estos bytes; sirve para validar el contenido real,
# no solo el content-type que declara el cliente (que se puede falsificar)
PDF_MAGIC_NUMBER = b"%PDF-"

async def save_pdf(file: UploadFile) -> UploadResponse:
    content = await file.read()  # Lee el archivo completo en memoria

    # Valida el contenido real del archivo, no solo su extensión o content-type
    if not content.startswith(PDF_MAGIC_NUMBER):
        raise InvalidFileTypeException()

    # Convierte el límite de MB a bytes para comparar
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise FileTooLargeException(settings.max_upload_size_mb)

    os.makedirs(settings.upload_dir, exist_ok=True)

    # uuid4() genera un nombre único e impredecible, evitando:
    # 1. Path traversal (alguien enviando "../../etc/passwd.pdf" como nombre)
    # 2. Colisiones si dos usuarios suben archivos con el mismo nombre
    safe_filename = f"{uuid.uuid4()}.pdf"
    file_path = os.path.join(settings.upload_dir, safe_filename)

    with open(file_path, "wb") as f:
        f.write(content)

    return UploadResponse(
        filename=safe_filename,
        size_kb=round(len(content) / 1024, 2),
        path=file_path
    )