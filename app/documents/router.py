from fastapi import APIRouter, UploadFile, File
from app.documents.service import save_pdf
from app.documents.schemas import UploadResponse
from app.documents.exceptions import InvalidFileTypeException

router = APIRouter(prefix="/documents", tags=["documents"])

@router.post("/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise InvalidFileTypeException()

    return await save_pdf(file)