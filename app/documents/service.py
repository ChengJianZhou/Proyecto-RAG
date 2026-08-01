from pathlib import Path
import json
import uuid

from fastapi import UploadFile

from app.core.config import settings
from app.documents.schemas import (
    UploadResponse,
    ChunkMetadata,
    DocumentChunk,
    ProcessedDocument,
)
from app.documents.exceptions import InvalidFileTypeException, FileTooLargeException
from app.documents.text_extractor import extract_text_from_pdf_bytes
from app.documents.chunking import chunk_text
from app.documents.session import utc_now, get_session_expiration, to_iso
from app.documents.cleanup import cleanup_expired_documents


PDF_MAGIC_NUMBER = b"%PDF-"


def save_processed_document(processed_document: ProcessedDocument) -> str:
    """
    Guarda el documento procesado como JSON en data/processed.
    """
    processed_dir = Path(settings.processed_dir)

    if processed_dir.exists() and not processed_dir.is_dir():
        raise RuntimeError(f"La ruta '{processed_dir}' existe pero no es una carpeta")

    processed_dir.mkdir(parents=True, exist_ok=True)

    processed_file_path = processed_dir / f"{processed_document.document_id}.json"

    with processed_file_path.open("w", encoding="utf-8") as f:
        json.dump(
            processed_document.model_dump(),
            f,
            indent=2,
            ensure_ascii=False
        )

    return str(processed_file_path)


async def save_pdf(file: UploadFile, session_id: str) -> UploadResponse:
    """
    Valida, procesa y persiste un PDF subido por un usuario anónimo con sesión temporal.
    """
    # Antes de procesar nada, borramos documentos caducados (no debería ser necesario, pero por si acaso)
    cleanup_expired_documents()

    content = await file.read()

    # Comprobamos que el archivo sea realmente un PDF por su firma binaria
    if not content.startswith(PDF_MAGIC_NUMBER):
        raise InvalidFileTypeException()

    # Comprobamos que el archivo no supere el tamaño permitido
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise FileTooLargeException(settings.max_upload_size_mb)

    # Extraemos el texto y lo dividimos en chunks
    extracted_text = extract_text_from_pdf_bytes(content)
    raw_chunks = chunk_text(extracted_text)

    upload_dir = Path(settings.upload_dir)
    if upload_dir.exists() and not upload_dir.is_dir():
        raise RuntimeError(f"La ruta '{upload_dir}' existe pero no es una carpeta")

    upload_dir.mkdir(parents=True, exist_ok=True)

    document_id = str(uuid.uuid4())
    safe_filename = f"{document_id}.pdf"
    file_path = upload_dir / safe_filename

    # Guardamos el PDF original
    with file_path.open("wb") as f:
        f.write(content)

    created_at = utc_now()
    expires_at = get_session_expiration()

    chunks = []
    for index, chunk_text_value in enumerate(raw_chunks):
        metadata = ChunkMetadata(
            chunk_id=f"{document_id}-{index}",
            document_id=document_id,
            session_id=session_id,
            filename=safe_filename,
            chunk_index=index,
            length=len(chunk_text_value),
        )

        chunk = DocumentChunk(
            metadata=metadata,
            text=chunk_text_value,
        )

        chunks.append(chunk)

    processed_document = ProcessedDocument(
        document_id=document_id,
        session_id=session_id,
        filename=safe_filename,
        original_path=str(file_path),
        created_at=to_iso(created_at),
        expires_at=to_iso(expires_at),
        extracted_characters=len(extracted_text),
        chunks_count=len(chunks),
        chunks=chunks,
    )

    processed_file_path = save_processed_document(processed_document)

    return UploadResponse(
        document_id=document_id,
        session_id=session_id,
        filename=safe_filename,
        size_kb=round(len(content) / 1024, 2),
        path=str(file_path),
        created_at=to_iso(created_at),
        expires_at=to_iso(expires_at),
        extracted_characters=len(extracted_text),
        chunks=len(chunks),
        processed_file=processed_file_path,
    )