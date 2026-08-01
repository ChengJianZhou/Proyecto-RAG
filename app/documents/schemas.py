from pydantic import BaseModel
from typing import List


class ChunkMetadata(BaseModel):
    chunk_id: str
    document_id: str
    filename: str
    chunk_index: int
    length: int


class DocumentChunk(BaseModel):
    metadata: ChunkMetadata
    text: str


class ProcessedDocument(BaseModel):
    document_id: str
    filename: str
    original_path: str
    extracted_characters: int
    chunks_count: int
    chunks: List[DocumentChunk]


class UploadResponse(BaseModel):
    document_id: str
    filename: str
    size_kb: float
    path: str
    extracted_characters: int
    chunks: int
    processed_file: str