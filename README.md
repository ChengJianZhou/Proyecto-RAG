# RAG Project

## Cómo arrancar

1. Clonar el repo.
2. Crear el archivo `.env` a partir de `.env.example` y generar una API key:
   python -c "import secrets; print(secrets.token_urlsafe(32))"
3. Ejecutar:
   docker compose up --build
4. Verificar salud:
   curl.exe http://localhost:8000/health
5. Subir un PDF (requiere API key):
   curl.exe -H "X-API-Key: TU_API_KEY" -F "file=@ejemplo.pdf" http://localhost:8000/documents/upload
6. Los archivos quedan en ./data/uploads con nombre aleatorio (UUID)

## Seguridad implementada

- Autenticación por API key (header `X-API-Key`) en el endpoint de subida.
- Validación real de PDF mediante magic number (`%PDF-`), no solo por content-type declarado por el cliente.
- Límite de tamaño de archivo configurable (`MAX_UPLOAD_SIZE_MB` en `.env`).
- Nombres de archivo aleatorios (UUID) para evitar path traversal y colisiones.
- Rate limiting: máximo 20 subidas por hora por IP.

## Procesamiento actual

Al subir un PDF, la API:

- valida que sea un PDF real,
- guarda el archivo original en `data/uploads`,
- extrae el texto con `pypdf`,
- divide el texto en chunks,
- guarda un JSON procesado en `data/processed`.

Cada archivo JSON contiene:
- `document_id`,
- metadatos de cada chunk,
- texto de cada chunk,
- número total de caracteres extraídos,
- número total de chunks.

Esto deja preparado el siguiente paso del pipeline RAG: generación de embeddings e indexación en una base vectorial.

## Documentación interactiva

Disponible en http://localhost:8000/docs
Nota: en /docs, usa el botón "Authorize" para introducir tu X-API-Key antes de probar /documents/upload.