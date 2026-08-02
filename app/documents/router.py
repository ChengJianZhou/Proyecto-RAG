from typing import Optional

from fastapi import APIRouter, UploadFile, File, Response, Cookie, Security, Request

from app.core.config import settings
from app.core.security import verify_api_key
from app.core.limiter import limiter
from app.documents.schemas import UploadResponse
from app.documents.service import save_pdf
from app.documents.session import generate_session_id


router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("/upload", response_model=UploadResponse)
@limiter.limit("10/minute")
async def upload_document(
    request: Request,
    response: Response,
    file: UploadFile = File(...),
    _: str = Security(verify_api_key),
    session_id: Optional[str] = Cookie(default=None, alias=settings.session_cookie_name),
):
    """
    Sube un PDF, lo procesa y lo asocia a una sesión temporal.
    La cookie solo se crea cuando no existe una sesión previa.
    """
    is_new_session = session_id is None
    current_session_id = session_id or generate_session_id()

    result = await save_pdf(file, current_session_id)

    if is_new_session:
        response.set_cookie(
            key=settings.session_cookie_name,
            value=current_session_id,
            max_age=settings.session_ttl_minutes * 60,
            httponly=True,
            secure=settings.secure_cookies,
            samesite="lax",
            path="/",
        )

    return result