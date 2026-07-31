import secrets
from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from app.core.config import settings

# Declara que esperamos la API key en un header llamado "X-API-Key"
api_key_header = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Security(api_key_header)):
    # compare_digest compara en tiempo constante, evitando "timing attacks"
    # (comparar strings con == normal puede filtrar info por cuánto tarda la comparación)
    if not secrets.compare_digest(api_key, settings.api_key):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API key inválida"
        )
    return api_key