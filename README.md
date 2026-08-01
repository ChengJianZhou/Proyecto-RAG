# RAG Project

Backend en FastAPI para ingestión de PDFs orientado a un pipeline RAG. Actualmente permite subir documentos PDF, validar su formato, extraer texto, dividirlo en chunks y persistir una representación procesada en JSON para preparar las siguientes fases de embeddings y retrieval.

## Cómo arrancar

1. Clonar el repo.
2. Crear el archivo `.env` a partir de `.env.example`.
3. Generar una API key:
   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
4. Levantar el proyecto:
   ```bash
   docker compose up --build
   ```
5. Verificar salud:
   ```bash
   curl.exe http://127.0.0.1:8001/health
   ```
6. Subir un PDF:
   ```bash
   curl.exe -H "X-API-Key: TU_API_KEY" -F "file=@ejemplo.pdf" http://127.0.0.1:8001/documents/upload
   ```

## Configuración

Ejemplo de `.env`:

```env
APP_NAME=RAG API
UPLOAD_DIR=data/uploads
PROCESSED_DIR=data/processed
MAX_UPLOAD_SIZE_MB=20
API_KEY=your-secret-api-key-here
SESSION_COOKIE_NAME=rag_session_id
SESSION_TTL_MINUTES=120
SECURE_COOKIES=false
```

### Variables disponibles

- `APP_NAME`: nombre de la aplicación.
- `UPLOAD_DIR`: carpeta donde se guardan los PDFs originales.
- `PROCESSED_DIR`: carpeta donde se guardan los JSON procesados.
- `MAX_UPLOAD_SIZE_MB`: tamaño máximo permitido para cada PDF.
- `API_KEY`: clave necesaria para usar el endpoint protegido de subida.
- `SESSION_COOKIE_NAME`: nombre de la cookie de sesión temporal.
- `SESSION_TTL_MINUTES`: duración de la sesión y de la retención temporal de archivos.
- `SECURE_COOKIES`: usar `true` cuando la app esté detrás de HTTPS.

## Endpoints

### `GET /health`

Devuelve el estado básico del servicio.

Respuesta esperada:

```json
{
  "status": "ok"
}
```

### `POST /documents/upload`

Sube un PDF, lo valida, extrae su texto, lo divide en chunks y guarda un JSON procesado asociado a una sesión temporal.

#### Requisitos

- Header `X-API-Key`
- `multipart/form-data`
- campo `file` de tipo archivo

#### Ejemplo de respuesta

```json
{
  "document_id": "171691e0-9d6a-45f9-990c-30fe5ef93e45",
  "session_id": "5a6d0d26-1c28-4ef1-9a0e-2c0fa5ff1234",
  "filename": "171691e0-9d6a-45f9-990c-30fe5ef93e45.pdf",
  "size_kb": 419.44,
  "path": "data/uploads/171691e0-9d6a-45f9-990c-30fe5ef93e45.pdf",
  "created_at": "2026-08-01T01:20:00+00:00",
  "expires_at": "2026-08-01T03:20:00+00:00",
  "extracted_characters": 2702,
  "chunks": 4,
  "processed_file": "data/processed/171691e0-9d6a-45f9-990c-30fe5ef93e45.json"
}
```

## Flujo actual

Al subir un PDF, la API:

- valida que el archivo sea un PDF real mediante magic number (`%PDF-`);
- comprueba el tamaño máximo permitido;
- genera un nombre seguro con UUID;
- guarda el PDF original en `data/uploads`;
- extrae texto con `pypdf`;
- divide el texto en chunks con solapamiento;
- crea un JSON procesado en `data/processed`;
- asocia el documento a una sesión temporal identificada por cookie.

## Persistencia de datos

Actualmente el proyecto guarda dos tipos de datos:

- `data/uploads`: PDF original subido por el usuario.
- `data/processed`: JSON procesado con metadatos y chunks.

Cada documento procesado incluye, como mínimo:

- `document_id`
- `session_id`
- `filename`
- `original_path`
- `created_at`
- `expires_at`
- `extracted_characters`
- `chunks_count`
- `chunks`

Cada chunk contiene:

- `chunk_id`
- `document_id`
- `session_id`
- `filename`
- `chunk_index`
- `length`
- `text`

## Sesiones temporales

La API usa una cookie temporal para asociar documentos a una sesión anónima.

### Comportamiento

- Si no existe cookie, se crea una nueva sesión.
- Si ya existe cookie válida, se reutiliza esa sesión.
- La cookie expira según `SESSION_TTL_MINUTES`.
- La sesión está pensada como temporal, no como autenticación de usuarios.

Esto permite separar documentos subidos en diferentes navegadores o sesiones sin implementar todavía cuentas de usuario.

## Borrado automático

Los archivos no se conservan indefinidamente.

- Cada documento tiene un `expires_at`.
- Un scheduler en background ejecuta limpieza periódica.
- Cuando un documento expira, se eliminan:
  - el PDF original,
  - y el JSON procesado asociado.

Este comportamiento está orientado a una demo temporal y reduce la retención innecesaria de archivos.

## Seguridad implementada

- Autenticación por API key mediante `X-API-Key`.
- Comparación segura de API key con `secrets.compare_digest`.
- Validación real de PDF por firma binaria, no solo por `content-type`.
- Límite de tamaño configurable por entorno.
- Nombres de archivo aleatorios con UUID.
- Rate limiting por IP con `slowapi`.
- Cookie de sesión `HttpOnly`.
- Opción de endurecer cookies con `SECURE_COOKIES=true` en despliegues HTTPS.

## Rate limiting

El proyecto usa `slowapi` como base para limitar peticiones por IP. Si amplías el endpoint de subida o añades nuevos endpoints sensibles, conviene mantener límites explícitos por ruta.

## Estructura principal

```text
app/
  core/
    config.py
    limiter.py
    scheduler.py
    security.py
  documents/
    chunking.py
    cleanup.py
    exceptions.py
    router.py
    schemas.py
    service.py
    session.py
    text_extractor.py
  health/
    router.py
  main.py
data/
  uploads/
  processed/
```

## Docker

El proyecto usa Docker Compose y monta volúmenes para persistir los datos procesados:

- `./data/uploads:/app/data/uploads`
- `./data/processed:/app/data/processed`
- `./app:/app/app`

La API queda expuesta en:

- `http://127.0.0.1:8001`

## Estado actual del proyecto

Actualmente el proyecto cubre la fase de ingestión documental de un sistema RAG:

- upload seguro de PDFs,
- extracción de texto,
- chunking,
- persistencia de chunks y metadatos,
- sesiones temporales,
- retención limitada y cleanup automático.

Todavía no incluye:

- embeddings,
- base de datos vectorial,
- retrieval semántico,
- endpoint de consulta tipo `/query`,
- generación de respuesta con un LLM.

## Siguientes pasos

Los siguientes bloques naturales del proyecto son:

1. mejorar el chunking para respetar mejor párrafos o secciones;
2. generar embeddings por chunk;
3. indexar en una base vectorial como Qdrant o Chroma;
4. crear un endpoint `/query`;
5. conectar el retrieval a un modelo generativo.

## Documentación interactiva

Disponible en:

- [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs)

Si el endpoint requiere API key, usa el botón **Authorize** en Swagger UI para introducir `X-API-Key`.