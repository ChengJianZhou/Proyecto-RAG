# RAG Project

Backend en FastAPI para un pipeline RAG. Actualmente permite subir documentos PDF, validar su formato, extraer texto, dividirlo en chunks, generar embeddings por chunk y persistir una representación procesada en JSON, como preparación para las siguientes fases de indexación vectorial y retrieval.

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
SESSION_TTL_MINUTES=1
SECURE_COOKIES=false
```

> **Nota:** `SESSION_TTL_MINUTES=1` está fijado así temporalmente para pruebas de desarrollo (permite validar rápido el ciclo de expiración y limpieza automática). Antes de cualquier demo o entorno real, debe subirse a un valor razonable (p. ej. `120`).

### Variables disponibles

- `APP_NAME`: nombre de la aplicación.
- `UPLOAD_DIR`: carpeta donde se guardan los PDFs originales.
- `PROCESSED_DIR`: carpeta donde se guardan los JSON procesados.
- `MAX_UPLOAD_SIZE_MB`: tamaño máximo permitido para cada PDF.
- `API_KEY`: clave necesaria para usar el endpoint protegido de subida.
- `SESSION_COOKIE_NAME`: nombre de la cookie de sesión temporal.
- `SESSION_TTL_MINUTES`: duración de la sesión y de la retención temporal de archivos (actualmente en `1` para pruebas).
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

Sube un PDF, lo valida, extrae su texto, lo divide en chunks, genera un embedding por chunk y guarda un JSON procesado asociado a una sesión temporal.

#### Requisitos

- Header `X-API-Key`
- `multipart/form-data`
- campo `file` de tipo archivo

#### Ejemplo de respuesta

```json
{
  "document_id": "9a85b5dd-ac81-48a3-add5-e1d61d0589b5",
  "session_id": "86b983af-3c14-4f92-86c1-4596916e2fc6",
  "filename": "9a85b5dd-ac81-48a3-add5-e1d61d0589b5.pdf",
  "size_kb": 46.98,
  "path": "data/uploads/9a85b5dd-ac81-48a3-add5-e1d61d0589b5.pdf",
  "created_at": "2026-08-02T16:29:17.171548+00:00",
  "expires_at": "2026-08-02T16:30:17.171553+00:00",
  "extracted_characters": 4289,
  "chunks": 6,
  "processed_file": "data/processed/9a85b5dd-ac81-48a3-add5-e1d61d0589b5.json"
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
- **genera un embedding vectorial por cada chunk**;
- crea un JSON procesado en `data/processed` con texto, metadatos y embeddings;
- asocia el documento a una sesión temporal identificada por cookie.

## Persistencia de datos

Actualmente el proyecto guarda dos tipos de datos:

- `data/uploads`: PDF original subido por el usuario.
- `data/processed`: JSON procesado con metadatos, chunks y embeddings.

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
- **`embedding`** (vector generado a partir del texto del chunk)

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
  - y el JSON procesado asociado (incluyendo sus embeddings).

Este comportamiento está orientado a una demo temporal y reduce la retención innecesaria de archivos. Actualmente `SESSION_TTL_MINUTES` está fijado a `1` minuto de forma intencional para poder probar rápido el ciclo completo de expiración y limpieza durante el desarrollo; se ajustará a un valor de producción más adelante.

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
    embeddings.py
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

Actualmente el proyecto cubre la fase de ingestión documental y generación de embeddings de un sistema RAG:

- upload seguro de PDFs,
- extracción de texto,
- chunking,
- **generación de embeddings por chunk**,
- persistencia de chunks, embeddings y metadatos,
- sesiones temporales,
- retención limitada y cleanup automático.

Todavía no incluye:

- chunking semántico (por párrafos/secciones, en lugar de longitud fija),
- base de datos vectorial,
- retrieval semántico,
- endpoint de consulta tipo `/query`,
- generación de respuesta con un LLM.

## Siguientes pasos

Los siguientes bloques naturales del proyecto son:

1. mejorar el chunking para respetar mejor párrafos o secciones y limpiar el texto extraído antes de generar embeddings;
2. indexar los embeddings en una base vectorial como Qdrant o Chroma;
3. crear un endpoint `/query`;
4. conectar el retrieval a un modelo generativo (LLM);
5. subir `SESSION_TTL_MINUTES` a un valor de producción antes de cualquier demo o despliegue.

## Documentación interactiva

Disponible en:

- [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs)

Si el endpoint requiere API key, usa el botón **Authorize** en Swagger UI para introducir `X-API-Key`.