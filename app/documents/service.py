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


PDF_MAGIC_NUMBER = b"%PDF-"


def save_processed_document(processed_document: ProcessedDocument) -> str:
    """
    Guarda en disco el documento procesado como JSON.
    Devuelve la ruta del archivo generado.
    """
    processed_dir = Path(settings.processed_dir)

    # Si la ruta existe pero no es carpeta, algo está mal en la configuración
    if processed_dir.exists() and not processed_dir.is_dir():
        raise RuntimeError(f"La ruta '{processed_dir}' existe pero no es una carpeta")

    processed_dir.mkdir(parents=True, exist_ok=True)

    # Usamos el document_id como nombre base para que PDF y JSON queden relacionados
    processed_file_path = processed_dir / f"{processed_document.document_id}.json"

    # model_dump() convierte el modelo Pydantic a dict serializable
    with processed_file_path.open("w", encoding="utf-8") as f:
        json.dump(
            processed_document.model_dump(),
            f,
            indent=2,
            ensure_ascii=False
        )

    return str(processed_file_path)


async def save_pdf(file: UploadFile) -> UploadResponse:
    # Leemos todo el contenido del archivo subido
    content = await file.read()

    # Verificación real del formato PDF por magic number
    if not content.startswith(PDF_MAGIC_NUMBER):
        raise InvalidFileTypeException()

    # Límite máximo de tamaño
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise FileTooLargeException(settings.max_upload_size_mb)

    # Extraemos texto del PDF
    extracted_text = extract_text_from_pdf_bytes(content)

    # Lo troceamos en chunks para prepararlo para embeddings/retrieval
    raw_chunks = chunk_text(extracted_text)

    # Directorio donde se guardan los PDFs originales
    upload_dir = Path(settings.upload_dir)
    if upload_dir.exists() and not upload_dir.is_dir():
        raise RuntimeError(f"La ruta '{upload_dir}' existe pero no es una carpeta")

    upload_dir.mkdir(parents=True, exist_ok=True)

    # UUID para evitar colisiones y no confiar en el nombre original del cliente
    document_id = str(uuid.uuid4())
    safe_filename = f"{document_id}.pdf"
    file_path = upload_dir / safe_filename

    # Guardamos el PDF original
    with file_path.open("wb") as f:
        f.write(content)

    # Construimos los chunks enriquecidos con metadata
    chunks = []
    for index, chunk_text_value in enumerate(raw_chunks):
        metadata = ChunkMetadata(
            chunk_id=f"{document_id}-{index}",
            document_id=document_id,
            filename=safe_filename,
            chunk_index=index,
            length=len(chunk_text_value),
        )

        chunk = DocumentChunk(
            metadata=metadata,
            text=chunk_text_value,
        )

        chunks.append(chunk)

    # Construimos la representación completa del documento procesado
    processed_document = ProcessedDocument(
        document_id=document_id,
        filename=safe_filename,
        original_path=str(file_path),
        extracted_characters=len(extracted_text),
        chunks_count=len(chunks),
        chunks=chunks,
    )

    # Guardamos el JSON procesado para futuras fases del pipeline
    processed_file_path = save_processed_document(processed_document)

    # Devolvemos una respuesta resumida al cliente
    return UploadResponse(
        document_id=document_id,
        filename=safe_filename,
        size_kb=round(len(content) / 1024, 2),
        path=str(file_path),
        extracted_characters=len(extracted_text),
        chunks=len(chunks),
        processed_file=processed_file_path,
    )