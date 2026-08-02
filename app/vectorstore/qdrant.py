"""
Cliente y operaciones sobre Qdrant para el pipeline RAG.

Este módulo se encarga de:
- Crear/obtener el cliente Qdrant (cacheado).
- Crear la colección si no existe, con el tamaño de vector correcto.
- Subir (upsert) los chunks con su embedding y metadatos como payload.
- Buscar los chunks más similares a una query, con filtros opcionales.
"""

import uuid
from functools import lru_cache
from typing import List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.core.config import settings
from app.documents.schemas import DocumentChunk


@lru_cache
def get_qdrant_client() -> QdrantClient:
    """
    Devuelve una única instancia cacheada del cliente Qdrant.

    Igual que con el modelo de embeddings, evitamos reconectar
    en cada llamada reutilizando la misma instancia durante
    la vida del proceso.
    """
    return QdrantClient(url=settings.qdrant_url)


def chunk_id_to_point_id(chunk_id: str) -> str:
    """
    Convierte nuestro chunk_id (formato "{document_id}-{index}") en un
    UUID determinista válido para Qdrant.

    Qdrant solo acepta como ID de punto un entero de 64 bits o un UUID.
    Nuestro chunk_id no cumple ese formato, así que generamos un UUID
    calculado a partir de él con uuid5: mismo chunk_id -> mismo UUID
    siempre. Esto permite que si reprocesamos el mismo chunk, Qdrant
    actualice el punto existente en lugar de duplicarlo.

    El chunk_id original se sigue guardando dentro del payload, así
    que no se pierde esa información legible.
    """
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, chunk_id))


def ensure_collection(vector_size: int) -> None:
    """
    Crea la colección configurada si todavía no existe, usando
    distancia coseno (la más habitual para embeddings de texto).
    """
    client = get_qdrant_client()
    collection_name = settings.qdrant_collection

    if not client.collection_exists(collection_name):
        client.create_collection(
            collection_name=collection_name,
            vectors_config=qmodels.VectorParams(
                size=vector_size,
                distance=qmodels.Distance.COSINE,
            ),
        )


def upsert_chunks(chunks: List[DocumentChunk]) -> int:
    """
    Sube a Qdrant los chunks que tengan embedding, usando el texto
    y los metadatos como payload.

    Los chunks sin embedding (por ejemplo texto vacío) se ignoran.

    Devuelve cuántos puntos se han subido.
    """
    valid_chunks = [chunk for chunk in chunks if chunk.embedding]

    if not valid_chunks:
        return 0

    vector_size = len(valid_chunks[0].embedding)
    ensure_collection(vector_size)

    client = get_qdrant_client()

    points = [
        qmodels.PointStruct(
            id=chunk_id_to_point_id(chunk.metadata.chunk_id),
            vector=chunk.embedding,
            payload={
                "chunk_id": chunk.metadata.chunk_id,
                "text": chunk.text,
                "document_id": chunk.metadata.document_id,
                "session_id": chunk.metadata.session_id,
                "filename": chunk.metadata.filename,
                "chunk_index": chunk.metadata.chunk_index,
                "length": chunk.metadata.length,
            },
        )
        for chunk in valid_chunks
    ]

    client.upsert(collection_name=settings.qdrant_collection, points=points)
    return len(points)


def search(
    query_vector: List[float],
    top_k: int = 5,
    session_id: Optional[str] = None,
    document_id: Optional[str] = None,
) -> List[qmodels.ScoredPoint]:
    """
    Busca los chunks más similares a la query, con filtros opcionales
    por sesión o por documento.

    Devuelve una lista de ScoredPoint, cada uno con su score de
    similitud y su payload (texto + metadatos).
    """
    client = get_qdrant_client()

    must_conditions = []
    if session_id:
        must_conditions.append(
            qmodels.FieldCondition(
                key="session_id",
                match=qmodels.MatchValue(value=session_id),
            )
        )
    if document_id:
        must_conditions.append(
            qmodels.FieldCondition(
                key="document_id",
                match=qmodels.MatchValue(value=document_id),
            )
        )

    query_filter = qmodels.Filter(must=must_conditions) if must_conditions else None

    return client.search(
        collection_name=settings.qdrant_collection,
        query_vector=query_vector,
        limit=top_k,
        query_filter=query_filter,
    )


def delete_document(document_id: str) -> None:
    """
    Elimina de Qdrant todos los puntos asociados a un documento.
    Si la colección todavía no existe, no hay nada que borrar.
    """
    client = get_qdrant_client()
    collection_name = settings.qdrant_collection

    if not client.collection_exists(collection_name):
        return

    client.delete(
        collection_name=collection_name,
        points_selector=qmodels.FilterSelector(
            filter=qmodels.Filter(
                must=[
                    qmodels.FieldCondition(
                        key="document_id",
                        match=qmodels.MatchValue(value=document_id),
                    )
                ]
            )
        ),
    )