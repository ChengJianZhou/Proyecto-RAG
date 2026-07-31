from fastapi import APIRouter, UploadFile, File, Depends, Request
from app.documents.service import save_pdf
from app.documents.schemas import UploadResponse
from app.documents.exceptions import InvalidFileTypeException
from app.core.security import verify_api_key
from app.core.limiter import limiter

router = APIRouter(prefix="/documents", tags=["documents"])

@router.post("/upload", response_model=UploadResponse)
@limiter.limit("20/hour")  # Máximo 20 peticiones por hora por dirección IP
async def upload_pdf(
    request: Request,               # slowapi necesita el Request para identificar la IP
    file: UploadFile = File(...),
    _: str = Depends(verify_api_key)  # Se ejecuta antes del cuerpo; si falla, corta aquí
):
    # Validación rápida por content-type declarado (primera barrera, no la única)
    if file.content_type != "application/pdf":
        raise InvalidFileTypeException()

    return await save_pdf(file)