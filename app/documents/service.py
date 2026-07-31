import os
from fastapi import UploadFile
from app.core.config import settings
from app.documents.schemas import UploadResponse

async def save_pdf(file: UploadFile) -> UploadResponse:
    os.makedirs(settings.upload_dir, exist_ok=True)
    file_path = os.path.join(settings.upload_dir, file.filename)
    content = await file.read()

    with open(file_path, "wb") as f:
        f.write(content)

    return UploadResponse(
        filename=file.filename,
        size_kb=round(len(content) / 1024, 2),
        path=file_path
    )