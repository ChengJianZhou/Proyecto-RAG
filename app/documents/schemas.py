from pydantic import BaseModel

class UploadResponse(BaseModel):
    filename: str
    size_kb: float
    path: str