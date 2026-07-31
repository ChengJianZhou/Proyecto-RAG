from fastapi import HTTPException, status

class InvalidFileTypeException(HTTPException):
    def __init__(self):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se aceptan archivos PDF"
        )

class FileTooLargeException(HTTPException):
    def __init__(self, max_mb: int):
        super().__init__(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"El archivo supera el límite de {max_mb}MB"
        )