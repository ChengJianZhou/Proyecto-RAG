from typing import List

from langchain_text_splitters import RecursiveCharacterTextSplitter

# Separadores en orden de prioridad: LangChain intenta primero el más "grande"
# (párrafos) y solo baja de nivel si el chunk sigue siendo demasiado grande.
DEFAULT_SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


def build_splitter(chunk_size: int = 800, chunk_overlap: int = 120) -> RecursiveCharacterTextSplitter:
    """
    Crea un splitter recursivo que prioriza mantener párrafos y frases intactos
    antes de recurrir a un corte por longitud fija.
    """
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=DEFAULT_SEPARATORS,
        length_function=len,
    )


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 120) -> List[str]:
    """
    Divide el texto en chunks semánticamente más coherentes usando
    RecursiveCharacterTextSplitter de LangChain.
    """
    if not text or not text.strip():
        return []

    if overlap >= chunk_size:
        raise ValueError("overlap debe ser menor que chunk_size")

    splitter = build_splitter(chunk_size=chunk_size, chunk_overlap=overlap)
    raw_chunks = splitter.split_text(text)

    return [chunk.strip() for chunk in raw_chunks if chunk.strip()]