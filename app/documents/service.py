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
from app.documents.text_extractor import extract_text_from_pdf_bytes, normalize_text
from app.documents.chunking import chunk_text
from app.documents.session import utc_now, get_session_expiration, to_iso
from app.documents.cleanup import cleanup_expired_documents
from app.embeddings.service import embed_texts
from app.vectorstore.qdrant import upsert_chunks


# Firma binaria básica de un PDF real.
# Nos sirve para validar que el archivo empieza por %PDF-
PDF_MAGIC_NUMBER = b"%PDF-"


def save_processed_document(processed_document: ProcessedDocument) -> str:
    """
    Guarda el documento procesado como JSON en data/processed.
    Devuelve la ruta del archivo generado.
    """
    processed_dir = Path(settings.processed_dir)

    # Si la ruta existe pero no es una carpeta, detenemos la ejecución
    # porque guardar ahí produciría errores difíciles de depurar.
    if processed_dir.exists() and not processed_dir.is_dir():
        raise RuntimeError(f"La ruta '{processed_dir}' existe pero no es una carpeta")

    # Creamos la carpeta si todavía no existe.
    processed_dir.mkdir(parents=True, exist_ok=True)

    # El nombre del JSON procesado será el document_id.
    processed_file_path = processed_dir / f"{processed_document.document_id}.json"

    # Pydantic convierte todo el modelo anidado a tipos serializables.
    with processed_file_path.open("w", encoding="utf-8") as f:
        json.dump(
            processed_document.model_dump(),
            f,
            indent=2,
            ensure_ascii=False,
        )

    return str(processed_file_path)


async def save_pdf(file: UploadFile, session_id: str) -> UploadResponse:
    """
    Valida, procesa y persiste un PDF subido por un usuario anónimo con sesión temporal.

    Flujo:
    1. Limpia documentos expirados.
    2. Lee el contenido del archivo subido.
    3. Valida que sea un PDF real y que no supere el tamaño máximo.
    4. Extrae texto.
    5. Divide el texto en chunks.
    6. Genera embeddings locales para cada chunk.
    7. Guarda el PDF original.
    8. Guarda un JSON procesado con metadatos, chunks y embeddings.
    9. Devuelve la respuesta del upload.
    """
    # Limpieza preventiva, solo si está activada en configuración.
    if settings.enable_cleanup:
        cleanup_expired_documents()

    # Leemos el contenido completo del archivo subido.
    content = await file.read()

    # Validación real por magic number.
    # No confiamos solo en content-type o extensión del archivo.
    if not content.startswith(PDF_MAGIC_NUMBER):
        raise InvalidFileTypeException()

    # Validamos tamaño máximo según configuración.
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(content) > max_bytes:
        raise FileTooLargeException(settings.max_upload_size_mb)

    # Extraemos el texto del PDF.
    extracted_text = normalize_text(extract_text_from_pdf_bytes(content))

    # Dividimos el texto en chunks para prepararlo para RAG.
    raw_chunks = chunk_text(extracted_text)

    # Generamos embeddings locales para todos los chunks.
    # Si no hay chunks, embed_texts devolverá una lista vacía.
    chunk_embeddings = embed_texts(raw_chunks)

    upload_dir = Path(settings.upload_dir)

    # Validamos también la carpeta de uploads por seguridad.
    if upload_dir.exists() and not upload_dir.is_dir():
        raise RuntimeError(f"La ruta '{upload_dir}' existe pero no es una carpeta")

    # Creamos la carpeta si no existe.
    upload_dir.mkdir(parents=True, exist_ok=True)

    # Generamos un ID único para el documento.
    document_id = str(uuid.uuid4())

    # Guardamos el archivo con nombre seguro para evitar problemas
    # con nombres originales raros o colisiones.
    safe_filename = f"{document_id}.pdf"
    file_path = upload_dir / safe_filename

    # Guardamos el PDF original en disco.
    with file_path.open("wb") as f:
        f.write(content)

    created_at = utc_now()
    expires_at = get_session_expiration()

    chunks = []

    # Recorremos cada chunk de texto y le asociamos sus metadatos
    # y su embedding correspondiente.
    for index, chunk_text_value in enumerate(raw_chunks):
        metadata = ChunkMetadata(
            chunk_id=f"{document_id}-{index}",
            document_id=document_id,
            session_id=session_id,
            filename=safe_filename,
            chunk_index=index,
            length=len(chunk_text_value),
        )

        # Intentamos emparejar el chunk con su embedding por posición.
        # Si por cualquier motivo no existe, lo dejamos como None
        # para que el sistema no reviente y podamos depurarlo.
        embedding_value = (
            chunk_embeddings[index]
            if index < len(chunk_embeddings) and chunk_embeddings[index]
            else None
        )

        chunk = DocumentChunk(
            metadata=metadata,
            text=chunk_text_value,
            embedding=embedding_value,
        )

        chunks.append(chunk)
    # Indexamos los chunks con embedding en Qdrant para retrieval semántico.
    upsert_chunks(chunks)

    # Construimos la representación procesada completa del documento.
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

    # Guardamos el JSON procesado.
    processed_file_path = save_processed_document(processed_document)

    # Respuesta ligera para el cliente.
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