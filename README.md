# RAG Project

Backend en FastAPI para un pipeline de **Retrieval-Augmented Generation (RAG)**. Permite subir documentos PDF, extraer y normalizar su texto, dividirlo en chunks semánticamente coherentes, generar embeddings vectoriales por chunk, indexarlos en Qdrant y responder preguntas en lenguaje natural combinando retrieval semántico con un modelo generativo local servido con Ollama.

## Estado del proyecto

| Fase | Estado |
|---|---|
| Ingestión de PDFs (validación, extracción, chunking) | ✅ Completado |
| Generación de embeddings por chunk | ✅ Completado |
| Seguridad (API key, rate limiting, sesiones temporales) | ✅ Completado |
| Indexación en base de datos vectorial (Qdrant) | ✅ Completado |
| Borrado automático configurable (`ENABLE_CLEANUP`) | ✅ Completado |
| Endpoint de consulta `/documents/query` (retrieval semántico) | ✅ Completado |
| Generación de respuesta con LLM local (Ollama) | ✅ Completado |
| Mejora de chunking/embedding | ⏳ Pendiente (pospuesto intencionalmente) |
| CORS y rate limiting para exposición pública (frontend portafolio) | ⏳ Pendiente |
| Simplificación del modelo de sesión para caso de uso de portafolio | ⏳ Pendiente |

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
7. Hacer una consulta:
   ```bash
   curl.exe -H "Content-Type: application/json" -d "{\"question\": \"tu pregunta\"}" http://127.0.0.1:8001/documents/query
   ```

## Configuración

Ejemplo de `.env` (basado en `.env.example`):

```env
APP_NAME=RAG API
UPLOAD_DIR=data/uploads
PROCESSED_DIR=data/processed
MAX_UPLOAD_SIZE_MB=20
API_KEY=your-secret-api-key-here
SESSION_COOKIE_NAME=rag_session_id
SESSION_TTL_MINUTES=120
SECURE_COOKIES=false
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
QDRANT_URL=http://qdrant:6333
QDRANT_COLLECTION=documents
ENABLE_CLEANUP=false
OLLAMA_BASE_URL=http://192.168.1.137:11434
OLLAMA_MODEL=llama3.2:3b
```

> **Nota sobre `ENABLE_CLEANUP`:** controla tanto el scheduler periódico (`app/core/scheduler.py`) como la limpieza preventiva en cada subida (`app/documents/service.py`). Con `false` (valor por defecto en `Settings`), los documentos, sus JSON procesados y sus vectores en Qdrant se conservan indefinidamente — pensado para el caso de uso de base de conocimiento persistente de un chatbot de portafolio. Con `true`, se recupera el comportamiento original de retención temporal por sesión (`SESSION_TTL_MINUTES`).

> **Nota sobre Ollama:** `OLLAMA_BASE_URL` apunta a un servidor Ollama con GPU accesible en red local (directo por IP o vía DNS interno, sin exposición pública real a internet). `OLLAMA_MODEL` debe ser un modelo conversacional de propósito general. Modelos especializados en código (familia `qwen2.5-coder`, `deepseek-coder`) o de embeddings (`mxbai-embed-large`) no son adecuados para `/documents/query`, ya que no están entrenados para diálogo general.

### Variables disponibles

| Variable | Descripción | Valor por defecto en código |
|---|---|---|
| `APP_NAME` | Nombre de la aplicación. | `RAG API` |
| `UPLOAD_DIR` | Carpeta donde se guardan los PDFs originales. | `data/uploads` |
| `PROCESSED_DIR` | Carpeta donde se guardan los JSON procesados. | `data/processed` |
| `MAX_UPLOAD_SIZE_MB` | Tamaño máximo permitido para cada PDF. | `20` |
| `API_KEY` | Clave necesaria para usar el endpoint protegido de subida. | (obligatoria, sin default) |
| `SESSION_COOKIE_NAME` | Nombre de la cookie de sesión temporal. | `rag_session_id` |
| `SESSION_TTL_MINUTES` | Duración de la sesión y de la retención temporal de archivos (solo aplica con `ENABLE_CLEANUP=true`). | `1` |
| `SECURE_COOKIES` | Usar `true` cuando la app esté detrás de HTTPS. | `false` |
| `EMBEDDING_MODEL` | Modelo de embeddings de FastEmbed usado para vectorizar los chunks. | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` |
| `QDRANT_URL` | URL del servicio Qdrant. | `http://qdrant:6333` |
| `QDRANT_COLLECTION` | Nombre de la colección usada en Qdrant. | `documents` |
| `ENABLE_CLEANUP` | Activa o desactiva el borrado automático de documentos expirados. | `false` |
| `OLLAMA_BASE_URL` | URL del servidor Ollama que genera las respuestas. | `http://192.168.1.137:11434` |
| `OLLAMA_MODEL` | Modelo conversacional usado para generar respuestas en `/documents/query`. | `llama3.2:3b` |

## Endpoints

### `GET /health`

Devuelve el estado básico del servicio.

```json
{
  "status": "ok"
}
```

### `POST /documents/upload`

Sube un PDF, lo valida, extrae y normaliza su texto, lo divide en chunks, genera un embedding por chunk, lo indexa en Qdrant y guarda un JSON procesado asociado a una sesión temporal.

#### Requisitos

- Header `X-API-Key`
- `multipart/form-data` con campo `file`
- Límite de `10 peticiones/minuto` por IP (`@limiter.limit("10/minute")`)

#### Ejemplo de petición

```bash
curl.exe -H "X-API-Key: TU_API_KEY" -F "file=@ejemplo.pdf" http://127.0.0.1:8001/documents/upload
```

#### Forma de la respuesta (`UploadResponse`)

```json
{
  "document_id": "string",
  "session_id": "string",
  "filename": "string",
  "size_kb": 0.0,
  "path": "string",
  "created_at": "ISO 8601",
  "expires_at": "ISO 8601",
  "extracted_characters": 0,
  "chunks": 0,
  "processed_file": "string"
}
```

Si no existe cookie de sesión previa (`rag_session_id` por defecto), la respuesta incluye un header `Set-Cookie` con una nueva sesión, con `HttpOnly`, `SameSite=Lax` y expiración según `SESSION_TTL_MINUTES`.

### `POST /documents/query`

Genera el embedding de la pregunta, recupera los chunks más relevantes en Qdrant y usa Ollama para redactar una respuesta basada únicamente en ese contexto (`app/generation/service.py`).

#### Requisitos

- `Content-Type: application/json`
- Campo `question` (string, obligatorio)
- Campo `top_k` (int, opcional, por defecto `5` según `QueryRequest`)
- Límite de `5 peticiones/minuto` por IP (`@limiter.limit("5/minute")`)

#### Ejemplo de petición

```bash
curl.exe -H "Content-Type: application/json" -d "{\"question\": \"¿Qué tecnologías usa Marcos?\"}" http://127.0.0.1:8001/documents/query
```

#### Ejemplo real de respuesta

```json
{
  "answer": "Según el contexto proporcionado, Marcos utiliza las siguientes tecnologías:\n\n* Lenguajes de programación:\n + Java\n + Python\n + Node.js\n* Framework y bibliotecas:\n + Spring Boot (backend)\n + React (frontend)\n + Vue (frontend)\n + Django (backend)\n* Sistemas operativos:\n + Linux\n + Android (en tablet)\n* Gestión de proyectos y metodologías:\n + Docker\n + Docker Compose\n + Nginx\n + Git\n + Cloudflare\n + Vaultwarden\n + Agile (metodología)\n + Scrum (metodología)\n* Bases de datos:\n + PostgreSQL\n* Infraestructura y despliegue:\n + Docker\n + Docker Compose\n + SSH",
  "sources": [
    "d8a71d38-2021-44c6-a9b0-3d537764a8fd-7",
    "d8a71d38-2021-44c6-a9b0-3d537764a8fd-0",
    "d8a71d38-2021-44c6-a9b0-3d537764a8fd-2",
    "d8a71d38-2021-44c6-a9b0-3d537764a8fd-6",
    "d8a71d38-2021-44c6-a9b0-3d537764a8fd-3"
  ]
}
```

`sources` contiene los `chunk_id` (formato `{document_id}-{chunk_index}`) usados como contexto, permitiendo trazar de qué parte del documento original viene cada fragmento citado.

Si Ollama no responde (máquina con GPU apagada o inaccesible en red), `generate_answer()` lanza un `RuntimeError` que el router traduce a `503 Service Unavailable` en vez de un error genérico.

## Flujo actual

### Subida de documento (`/documents/upload`, en `app/documents/service.py`)

1. Ejecuta limpieza preventiva de documentos expirados solo si `settings.enable_cleanup` es `true`.
2. Lee el contenido del archivo y valida la firma binaria `%PDF-` (no confía solo en `content-type`).
3. Valida el tamaño máximo según `MAX_UPLOAD_SIZE_MB`.
4. Extrae el texto con `pypdf` (`text_extractor.py`) y lo normaliza (espacios y saltos de línea redundantes).
5. Divide el texto en chunks con `RecursiveCharacterTextSplitter` de LangChain (`chunking.py`).
6. Genera un embedding por chunk con FastEmbed (`embeddings/service.py`).
7. Indexa los chunks con embedding en Qdrant (`upsert_chunks()` en `vectorstore/qdrant.py`).
8. Guarda el PDF original en `UPLOAD_DIR` con nombre aleatorio (`{document_id}.pdf`).
9. Guarda un JSON procesado en `PROCESSED_DIR` con texto, metadatos y embeddings.
10. Asocia el documento a una sesión temporal identificada por cookie.

### Consulta (`/documents/query`, en `app/generation/service.py`)

1. `embed_query()` genera el embedding de la pregunta del usuario.
2. `search()` busca en Qdrant los `top_k` chunks más similares por distancia coseno.
3. `build_prompt()` construye el prompt final combinando un system prompt restrictivo con el texto de los chunks recuperados.
4. `generate_answer()` envía el prompt al servidor Ollama vía `POST /api/generate` con `stream=False` y `temperature=0.2`.
5. Se devuelve la respuesta generada junto con los `chunk_id` usados como fuente.

El system prompt actual es:

```
Eres el asistente personal de Marcos. Respondes preguntas sobre su perfil,
experiencia y proyectos usando SOLO el contexto proporcionado a continuación.
Si la respuesta no está en el contexto, dilo claramente en vez de inventar.
```

## Persistencia de datos

- `data/uploads`: PDF original subido por el usuario.
- `data/processed`: JSON procesado con metadatos, chunks y embeddings.
- Vectores en Qdrant, asociados a cada documento y sesión.

Cada `ProcessedDocument` incluye `document_id`, `session_id`, `filename`, `original_path`, `created_at`, `expires_at`, `extracted_characters`, `chunks_count` y `chunks`. Cada `DocumentChunk` contiene sus `metadata` (`chunk_id`, `document_id`, `session_id`, `filename`, `chunk_index`, `length`), su `text` y su `embedding`.

## Sesiones temporales

La API usa una cookie temporal (`SESSION_COOKIE_NAME`) para asociar documentos a una sesión anónima:

- Si no existe cookie, `router.py` genera una nueva con `generate_session_id()` y la envía en la respuesta.
- Si ya existe, se reutiliza la misma sesión sin volver a fijar la cookie.
- La cookie es `HttpOnly`, con `SameSite=Lax` y `Secure` según `SECURE_COOKIES`.

Este mecanismo tiene sentido para el caso de uso original de subidas anónimas por sesión, pero es candidato a simplificarse en el caso de uso de chatbot de portafolio, donde no hay usuarios subiendo documentos ajenos entre sí.

## Borrado automático

Controlado por `ENABLE_CLEANUP` (`app/core/config.py`), que afecta a dos puntos del código:

- `app/core/scheduler.py`: `start_scheduler()` no registra ni arranca el job periódico si `enable_cleanup` es `false`.
- `app/documents/service.py`: `save_pdf()` solo llama a `cleanup_expired_documents()` si `enable_cleanup` es `true`.

Cuando está activo, `cleanup_expired_documents()` (`app/documents/cleanup.py`) recorre los JSON en `PROCESSED_DIR`, y para cada uno cuyo `expires_at` ya haya pasado, elimina el PDF original, los vectores en Qdrant (`delete_document()`) y el propio JSON.

## Generación con LLM local (Ollama)

- El cliente vive en `app/generation/service.py` y usa `httpx` para llamar a `POST {OLLAMA_BASE_URL}/api/generate`.
- Se usa `stream=False` para obtener la respuesta completa en una sola llamada, y `temperature=0.2` para reducir variabilidad y ceñirse más al contexto proporcionado.
- Timeout configurado en `120.0` segundos (`TIMEOUT` en el módulo), suficiente para cubrir el tiempo de carga inicial del modelo en VRAM tras inactividad.
- Errores de red (`httpx.RequestError`) y errores HTTP de Ollama (`httpx.HTTPStatusError`) se capturan y re-lanzan como `RuntimeError`, que el router traduce a `503`.
- El modelo recomendado (`llama3.2:3b`) es conversacional de propósito general; los modelos "Coder" disponibles en el mismo servidor Ollama no son adecuados para este endpoint porque están entrenados específicamente para generación de código.

## Seguridad implementada

- Autenticación por API key mediante `X-API-Key` en `/documents/upload` (`app/core/security.py`).
- Comparación segura de API key con `secrets.compare_digest` (evita timing attacks).
- Validación real de PDF por firma binaria (`%PDF-`), no solo por `content-type`.
- Límite de tamaño configurable por entorno (`MAX_UPLOAD_SIZE_MB`).
- Nombres de archivo aleatorios con UUID.
- Rate limiting por IP con `slowapi`: `10/minute` en `/documents/upload`, `5/minute` en `/documents/query`.
- Cookie de sesión `HttpOnly`, con soporte para `Secure` en despliegues HTTPS (`SECURE_COOKIES`).
- El servidor Ollama no se expone públicamente en internet; el acceso está limitado a la red local o a un dominio interno resuelto por DNS.
- `/documents/query` no requiere `X-API-Key`, ya que está pensado para consumo público desde un frontend (a diferencia de `/documents/upload`, que sí controla quién sube documentos).

## Chunking

`RecursiveCharacterTextSplitter` de LangChain (`app/documents/chunking.py`), con separadores en orden de prioridad `["\n\n", "\n", ". ", " ", ""]`: intenta preservar párrafos completos, luego líneas, luego frases, y solo como último recurso corta por caracteres sueltos. `chunk_size=800` y `chunk_overlap=120` por defecto.

## Embeddings

Generados localmente con [FastEmbed](https://github.com/qdrant/fastembed) (`app/embeddings/service.py`), sin depender de una API externa:

- Modelo cacheado con `lru_cache` para evitar reinicializaciones costosas (`get_embedding_model()`).
- `embed_texts()` genera embeddings para una lista de chunks, manteniendo el orden y alineación con el índice original, e ignorando textos vacíos sin romper la correspondencia de posiciones.
- `embed_query()` genera el embedding de una consulta individual, usado en el endpoint `/documents/query`.

## Vectorstore (Qdrant)

`app/vectorstore/qdrant.py`:

- Cliente cacheado con `lru_cache` (`get_qdrant_client()`).
- `ensure_collection()` crea la colección configurada (`QDRANT_COLLECTION`) con distancia coseno si todavía no existe.
- `upsert_chunks()` sube solo los chunks que tengan embedding, usando texto y metadatos como payload.
- IDs de punto deterministas con `uuid5` a partir del `chunk_id` (`chunk_id_to_point_id()`), evitando duplicados si se reprocesa el mismo chunk.
- `search()` permite filtrar por `session_id` y/o `document_id` al recuperar los chunks más similares.
- `delete_document()` elimina todos los puntos asociados a un documento, usado por la limpieza automática cuando `ENABLE_CLEANUP=true`.

## Rate limiting

`slowapi` (`app/core/limiter.py`) limita peticiones por IP:

- `/documents/upload`: `10/minute`.
- `/documents/query`: `5/minute` (más restrictivo, por el coste de cómputo de la generación con LLM).

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
  generation/
    service.py
  health/
    router.py
  vectorstore/
    qdrant.py
  main.py
data/
  uploads/
tests/
  documents/
  health/
```

## Docker

`docker-compose.yml` levanta dos servicios: `api` (build local, puerto `127.0.0.1:8001`) y `qdrant` (imagen oficial, puerto `127.0.0.1:6333`), con volúmenes para persistir `data/uploads`, `data/processed` y montar `./app` en caliente durante desarrollo (`Dockerfile` usa `--reload`).

## Siguientes pasos

1. Añadir `CORSMiddleware` restringido al dominio del frontend del portafolio, para permitir peticiones desde el navegador.
2. Manejar de forma explícita en el frontend el caso de servidor Ollama desconectado, mostrando un mensaje claro en vez de un error genérico.
3. Simplificar el modelo de sesión: el concepto de sesión anónima por cookie tiene menos sentido cuando el documento fuente es un único CV/perfil, no subidas de terceros.
4. Mejorar chunking y embedding (detección de secciones/headings, evaluación de modelos de embeddings alternativos).
5. Considerar `keep_alive` en las llamadas a Ollama para reducir la latencia de la primera petición tras un periodo de inactividad.

## Documentación interactiva

Disponible en [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs). Usa el botón **Authorize** en Swagger UI para introducir `X-API-Key` (necesaria solo para `/documents/upload`).
</content>