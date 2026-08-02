from functools import lru_cache
from typing import List

from fastembed import TextEmbedding

from app.core.config import settings


# Modelo por defecto recomendado para este proyecto:
# - multilingüe, útil si tus PDFs pueden estar en español e inglés
# - más apropiado que usar uno solo-en-inglés
#
# Si luego quieres cambiarlo, solo tendrás que tocar el .env
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

@lru_cache
def get_embedding_model() -> TextEmbedding:
    """
    Devuelve una única instancia cacheada del modelo de embeddings.

    ¿Por qué usamos cache?
    - Cargar el modelo cada vez sería lento e ineficiente.
    - FastEmbed descarga e inicializa el modelo la primera vez.
    - Después reutilizamos la misma instancia durante la vida del proceso.

    El nombre del modelo se toma desde settings si existe la variable
    embedding_model; si no, usamos un valor por defecto razonable.
    """
    model_name = getattr(settings, "embedding_model", DEFAULT_EMBEDDING_MODEL)
    return TextEmbedding(model_name=model_name)


def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Genera embeddings para una lista de textos.

    Parámetros:
    - texts: lista de strings, normalmente tus chunks del documento.

    Devuelve:
    - Lista de embeddings, donde cada embedding es una lista de floats.
      La posición de cada embedding corresponde a la posición del texto
      original en la lista de entrada.

    Comportamiento:
    - Si la lista está vacía, devolvemos [].
    - Filtramos textos vacíos o solo con espacios para evitar trabajo inútil.
    - Mantenemos el orden para que luego puedas emparejar chunk[i] con embedding[i].
    """
    if not texts:
        return []

    # Normalizamos entradas:
    # - convertimos None o falsy a string vacío
    # - eliminamos espacios sobrantes
    normalized_texts = [(text or "").strip() for text in texts]

    # Si todos los textos están vacíos, devolvemos embeddings vacíos por consistencia.
    if not any(normalized_texts):
        return [[] for _ in normalized_texts]

    model = get_embedding_model()

    # Necesitamos mantener la correspondencia entre índice de chunk e índice de embedding.
    # Por eso:
    # 1. separamos los textos válidos,
    # 2. generamos embeddings solo para esos,
    # 3. reconstruimos la lista final respetando posiciones.
    valid_items = [
        (index, text)
        for index, text in enumerate(normalized_texts)
        if text
    ]

    valid_texts = [text for _, text in valid_items]

    # FastEmbed devuelve un iterable/generador de vectores.
    # Lo materializamos en lista para poder recorrerlo y convertir cada vector a list[float].
    generated_embeddings = list(model.embed(valid_texts))

    # Preparamos salida con la misma longitud que texts.
    # En posiciones vacías dejamos [] para no romper la alineación.
    result: List[List[float]] = [[] for _ in normalized_texts]

    for (original_index, _), embedding in zip(valid_items, generated_embeddings):
        result[original_index] = embedding.tolist()

    return result


def embed_query(query: str) -> List[float]:
    """
    Genera el embedding de una consulta individual.

    Aunque hoy todavía no vayas a implementar retrieval ni /query,
    esta función te la dejo preparada porque será útil en la siguiente fase.

    Devuelve:
    - embedding de la query como lista de floats.
    - si la query está vacía, devuelve [].
    """
    cleaned_query = (query or "").strip()
    if not cleaned_query:
        return []

    model = get_embedding_model()

    # FastEmbed soporta embedding de consultas.
    # Algunas familias de modelos diferencian entre documentos y queries.
    query_vector = next(model.query_embed(cleaned_query))

    return query_vector.tolist()