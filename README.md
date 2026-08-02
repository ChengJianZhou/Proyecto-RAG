# RAG Project

Backend en FastAPI para un pipeline de **Retrieval-Augmented Generation (RAG)**. Permite subir documentos PDF, extraer y normalizar su texto, dividirlo en chunks semánticamente coherentes, generar embeddings vectoriales por chunk y persistir el resultado, como base para las siguientes fases de indexación vectorial, retrieval semántico y generación de respuestas con un LLM.

## Estado del proyecto

| Fase | Estado |
|---|---|
| Ingestión de PDFs (validación, extracción, chunking) | ✅ Completado |
| Generación de embeddings por chunk | ✅ Completado |
| Seguridad (API key, rate limiting, sesiones temporales) | ✅ Completado |
| Indexación en base de datos vectorial (Qdrant) | 🚧 En progreso |
| Endpoint de consulta `/query` (retrieval semántico) | ⏳ Pendiente |
| Generación de respuesta con LLM | ⏳ Pendiente |

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
EMBEDDING_MODEL=intfloat/multilingual-e5-small
```

> **Nota:** `SESSION_TTL_MINUTES=1` está fijado así temporalmente para pruebas de desarrollo (permite validar rápido el ciclo de expiración y limpieza automática). Antes de cualquier demo o entorno real, debe subirse a un valor razonable (p. ej. `120`).

### Variables disponibles

| Variable | Descripción |
|---|---|
| `APP_NAME` | Nombre de la aplicación. |
| `UPLOAD_DIR` | Carpeta donde se guardan los PDFs originales. |
| `PROCESSED_DIR` | Carpeta donde se guardan los JSON procesados. |
| `MAX_UPLOAD_SIZE_MB` | Tamaño máximo permitido para cada PDF. |
| `API_KEY` | Clave necesaria para usar el endpoint protegido de subida. |
| `SESSION_COOKIE_NAME` | Nombre de la cookie de sesión temporal. |
| `SESSION_TTL_MINUTES` | Duración de la sesión y de la retención temporal de archivos (actualmente en `1` para pruebas). |
| `SECURE_COOKIES` | Usar `true` cuando la app esté detrás de HTTPS. |
| `EMBEDDING_MODEL` | Modelo de embeddings de FastEmbed usado para vectorizar los chunks. Por defecto, un modelo multilingüe. |

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

Sube un PDF, lo valida, extrae y normaliza su texto, lo divide en chunks, genera un embedding por chunk y guarda un JSON procesado asociado a una sesión temporal.

#### Requisitos

- Header `X-API-Key`
- `multipart/form-data`
- Campo `file` de tipo archivo
- Límite de `10 peticiones/minuto` por IP

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

1. Limpia documentos expirados de forma preventiva.
2. Valida que el archivo sea un PDF real mediante magic number (`%PDF-`), no solo por `content-type`.
3. Comprueba el tamaño máximo permitido.
4. Genera un nombre seguro con UUID.
5. Extrae el texto con `pypdf` y lo normaliza (espacios y saltos de línea redundantes).
6. Divide el texto en chunks con `RecursiveCharacterTextSplitter` (LangChain), priorizando mantener párrafos y frases intactos antes de cortar por longitud fija.
7. Genera un embedding vectorial local por cada chunk con FastEmbed.
8. Guarda el PDF original en `data/uploads`.
9. Crea un JSON procesado en `data/processed` con texto, metadatos y embeddings.
10. Asocia el documento a una sesión temporal identificada por cookie.

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
- `embedding` (vector generado a partir del texto del chunk)

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
- Un scheduler en background ejecuta limpieza periódica cada minuto.
- Cuando un documento expira, se eliminan:
  - el PDF original,
  - y el JSON procesado asociado (incluyendo sus embeddings).

Este comportamiento está orientado a una demo temporal y reduce la retención innecesaria de archivos. `SESSION_TTL_MINUTES` está fijado a `1` minuto de forma intencional durante el desarrollo, para poder probar rápido el ciclo completo de expiración y limpieza; se ajustará a un valor de producción más adelante.

## Seguridad implementada

- Autenticación por API key mediante `X-API-Key`.
- Comparación segura de API key con `secrets.compare_digest` (evita timing attacks).
- Validación real de PDF por firma binaria, no solo por `content-type`.
- Límite de tamaño configurable por entorno.
- Nombres de archivo aleatorios con UUID.
- Rate limiting por IP con `slowapi` (`10/minute` en `/documents/upload`).
- Cookie de sesión `HttpOnly`.
- Opción de endurecer cookies con `SECURE_COOKIES=true` en despliegues HTTPS.

## Chunking

El texto se divide con `RecursiveCharacterTextSplitter` de LangChain, que intenta preservar la estructura semántica del documento:

- Prioriza cortar por párrafos (`\n\n`), luego por líneas (`\n`), luego por frases (`. `), y solo como último recurso por caracteres sueltos.
- `chunk_size=800` y `chunk_overlap=120` por defecto, configurables en `chunking.py`.
- El overlap asegura que no se pierda contexto en los límites entre chunks.

## Embeddings

Los embeddings se generan localmente con [FastEmbed](https://github.com/qdrant/fastembed), sin depender de una API externa:

- Modelo por defecto multilingüe (español/inglés), configurable vía `EMBEDDING_MODEL`.
- El modelo se carga una única vez por proceso (`lru_cache`) para evitar reinicializaciones costosas.
- `embed_texts()` genera embeddings para una lista de chunks manteniendo el orden y alineación con el índice original.
- `embed_query()` está preparado para la fase de retrieval, generando el embedding de una consulta de usuario.

## Rate limiting

El proyecto usa `slowapi` para limitar peticiones por IP. Si amplías el endpoint de subida o añades nuevos endpoints sensibles, conviene mantener límites explícitos por ruta.

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
  embeddings/
    service.py
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

## Siguientes pasos

Los siguientes bloques naturales del proyecto son:

1. Indexar los embeddings en una base de datos vectorial (Qdrant).
2. Crear un endpoint `/query` que realice retrieval semántico filtrando por sesión/documento.
3. Conectar el retrieval a un modelo generativo (LLM) para producir respuestas con contexto.
4. Evaluar y, si procede, mejorar aún más el chunking (detección de secciones/headings).
5. Subir `SESSION_TTL_MINUTES` a un valor de producción antes de cualquier demo o despliegue.

## Documentación interactiva

Disponible en:

- [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs)

Si el endpoint requiere API key, usa el botón **Authorize** en Swagger UI para introducir `X-API-Key`.
