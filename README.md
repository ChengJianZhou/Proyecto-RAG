# RAG Project

Backend en FastAPI para un pipeline de **Retrieval-Augmented Generation (RAG)**. Permite subir documentos PDF, extraer y normalizar su texto, dividirlo en chunks semánticamente coherentes, generar embeddings vectoriales por chunk, indexarlos en una base de datos vectorial y responder preguntas en lenguaje natural usando retrieval semántico combinado con un modelo generativo local.

## Estado del proyecto

| Fase | Estado |
|---|---|
| Ingestión de PDFs (validación, extracción, chunking) | ✅ Completado |
| Generación de embeddings por chunk | ✅ Completado |
| Seguridad (API key, rate limiting, sesiones temporales) | ✅ Completado |
| Indexación en base de datos vectorial (Qdrant) | ✅ Completado |
| Borrado automático configurable (`ENABLE_CLEANUP`) | ✅ Completado |
| Endpoint de consulta `/query` (retrieval semántico) | ✅ Completado |
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
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
QDRANT_URL=http://qdrant:6333
QDRANT_COLLECTION=documents
ENABLE_CLEANUP=false
OLLAMA_BASE_URL=http://192.168.1.137:11434
OLLAMA_MODEL=llama3.2:3b
```

> **Nota:** `ENABLE_CLEANUP=false` desactiva por completo el borrado automático de PDFs, JSON procesados y vectores en Qdrant. Esto se usa cuando el proyecto se orienta a un caso de uso de base de conocimiento persistente (por ejemplo, un chatbot de portafolio que responde preguntas sobre el autor), donde los documentos no deben expirar. Para el caso de uso original de subida temporal de documentos por sesión, se puede reactivar con `ENABLE_CLEANUP=true` y ajustar `SESSION_TTL_MINUTES` a un valor de producción razonable.

> **Nota sobre Ollama:** `OLLAMA_BASE_URL` apunta a un servidor Ollama corriendo con GPU en una máquina de la red local, accesible directamente por IP o mediante un dominio interno resuelto por DNS rewrite (no expuesto públicamente en internet). `OLLAMA_MODEL` debe ser un modelo conversacional de propósito general (ej. `llama3.2:3b`); modelos especializados en código (`qwen2.5-coder`, `deepseek-coder`) o de embeddings (`mxbai-embed-large`) no son adecuados para este endpoint.

### Variables disponibles

| Variable | Descripción |
|---|---|
| `APP_NAME` | Nombre de la aplicación. |
| `UPLOAD_DIR` | Carpeta donde se guardan los PDFs originales. |
| `PROCESSED_DIR` | Carpeta donde se guardan los JSON procesados. |
| `MAX_UPLOAD_SIZE_MB` | Tamaño máximo permitido para cada PDF. |
| `API_KEY` | Clave necesaria para usar el endpoint protegido de subida. |
| `SESSION_COOKIE_NAME` | Nombre de la cookie de sesión temporal. |
| `SESSION_TTL_MINUTES` | Duración de la sesión y de la retención temporal de archivos (solo aplica si `ENABLE_CLEANUP=true`). |
| `SECURE_COOKIES` | Usar `true` cuando la app esté detrás de HTTPS. |
| `EMBEDDING_MODEL` | Modelo de embeddings de FastEmbed usado para vectorizar los chunks. Por defecto, un modelo multilingüe. |
| `QDRANT_URL` | URL del servicio Qdrant. |
| `QDRANT_COLLECTION` | Nombre de la colección usada en Qdrant. |
| `ENABLE_CLEANUP` | Activa o desactiva el borrado automático de documentos expirados (scheduler + limpieza preventiva en upload). Por defecto `false`. |
| `OLLAMA_BASE_URL` | URL del servidor Ollama que genera las respuestas. |
| `OLLAMA_MODEL` | Modelo conversacional usado para generar respuestas en `/query`. |

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

### `POST /documents/query`

Realiza una consulta en lenguaje natural: genera el embedding de la pregunta, recupera los chunks más relevantes en Qdrant y usa un modelo generativo local (Ollama) para redactar una respuesta basada únicamente en ese contexto.

#### Requisitos

- `application/json`
- Campo `question` (string, obligatorio)
- Campo `top_k` (int, opcional, por defecto 5)
- Límite de `5 peticiones/minuto` por IP

#### Ejemplo de petición

```json
{
  "question": "¿Qué tecnologías usa Marcos?",
  "top_k": 5
}
```

#### Ejemplo de respuesta

```json
{
  "answer": "Según el contexto proporcionado, Marcos utiliza las siguientes tecnologías: ...",
  "sources": [
    "d8a71d38-2021-44c6-a9b0-3d537764a8fd-7",
    "d8a71d38-2021-44c6-a9b0-3d537764a8fd-0"
  ]
}
```

Si el servidor Ollama no está disponible (por ejemplo, la máquina con GPU está apagada o desconectada de la red), el endpoint responde con `503 Service Unavailable` en vez de un error genérico.

## Flujo actual

### Subida de documento (`/documents/upload`)

1. Limpia documentos expirados de forma preventiva, solo si `ENABLE_CLEANUP=true`.
2. Valida que el archivo sea un PDF real mediante magic number (`%PDF-`), no solo por `content-type`.
3. Comprueba el tamaño máximo permitido.
4. Genera un nombre seguro con UUID.
5. Extrae el texto con `pypdf` y lo normaliza (espacios y saltos de línea redundantes).
6. Divide el texto en chunks con `RecursiveCharacterTextSplitter` (LangChain).
7. Genera un embedding vectorial local por cada chunk con FastEmbed.
8. Indexa los chunks con embedding en Qdrant para retrieval semántico.
9. Guarda el PDF original y un JSON procesado con texto, metadatos y embeddings.
10. Asocia el documento a una sesión temporal identificada por cookie.

### Consulta (`/documents/query`)

1. Genera el embedding de la pregunta del usuario.
2. Busca en Qdrant los `top_k` chunks más similares por distancia coseno.
3. Construye un prompt con un system prompt restrictivo ("usa solo el contexto proporcionado") y el texto de los chunks recuperados.
4. Envía el prompt al servidor Ollama vía HTTP y obtiene la respuesta generada.
5. Devuelve la respuesta junto con los `chunk_id` usados como fuente.

## Persistencia de datos

- `data/uploads`: PDF original subido por el usuario.
- `data/processed`: JSON procesado con metadatos, chunks y embeddings.
- Vectores en Qdrant, asociados a cada documento y sesión.

Cada documento procesado incluye `document_id`, `session_id`, `filename`, `original_path`, `created_at`, `expires_at`, `extracted_characters`, `chunks_count` y `chunks`. Cada chunk contiene `chunk_id`, `document_id`, `session_id`, `filename`, `chunk_index`, `length`, `text` y `embedding`.

## Sesiones temporales

La API usa una cookie temporal para asociar documentos a una sesión anónima. Si no existe cookie, se crea una nueva sesión; si ya existe, se reutiliza. Este mecanismo tiene sentido para el caso de uso original de subidas anónimas, pero es candidato a simplificarse en el caso de uso de chatbot de portafolio, donde no hay usuarios subiendo documentos ajenos.

## Borrado automático

Controlado por `ENABLE_CLEANUP`:

- `true`: scheduler periódico cada minuto + limpieza preventiva en cada upload, eliminando PDFs, JSON y vectores en Qdrant al expirar `expires_at`.
- `false` (por defecto): los documentos se conservan indefinidamente, pensado para una base de conocimiento persistente.

## Generación con LLM local (Ollama)

- El servidor Ollama corre en una máquina con GPU en la red local, accesible mediante `OLLAMA_BASE_URL`.
- Se usa el endpoint `/api/generate` de Ollama con `stream=False`.
- El cliente (`app/generation/service.py`) captura errores de red y los traduce a un `RuntimeError` que el router convierte en `503`, evitando errores 500 poco informativos si el servidor de generación no está disponible.
- El modelo debe ser conversacional (`llama3.2:3b` recomendado); los modelos de la familia "Coder" están especializados en generación de código y no son adecuados para responder preguntas generales sobre el autor o sus proyectos.

## Seguridad implementada

- Autenticación por API key mediante `X-API-Key` en `/documents/upload`.
- Comparación segura de API key con `secrets.compare_digest`.
- Validación real de PDF por firma binaria.
- Límite de tamaño configurable por entorno.
- Nombres de archivo aleatorios con UUID.
- Rate limiting por IP con `slowapi` (`10/minute` en `/documents/upload`, `5/minute` en `/documents/query`).
- Cookie de sesión `HttpOnly`, con soporte para `SECURE_COOKIES=true` en HTTPS.
- El servidor Ollama no se expone públicamente en internet; el acceso está limitado a la red local o mediante DNS interno.

## Chunking

`RecursiveCharacterTextSplitter` de LangChain, priorizando párrafos, luego líneas, luego frases, y por último caracteres sueltos. `chunk_size=800` y `chunk_overlap=120` por defecto, configurables en `chunking.py`.

## Embeddings

Generados localmente con [FastEmbed](https://github.com/qdrant/fastembed), sin depender de una API externa. Modelo por defecto multilingüe, configurable vía `EMBEDDING_MODEL`. `embed_texts()` para chunks e `embed_query()` para consultas de usuario.

## Vectorstore (Qdrant)

- Colección configurable vía `QDRANT_COLLECTION`, con distancia coseno.
- Cada punto guarda como payload el texto del chunk y sus metadatos.
- IDs deterministas con `uuid5` a partir del `chunk_id`, evitando duplicados.
- `search()` permite filtrar por `session_id`/`document_id`.
- `delete_document()` elimina todos los puntos asociados a un documento (usado solo si `ENABLE_CLEANUP=true`).
- El cliente se inicializa con un `timeout` explícito para evitar fallos en la creación inicial de la colección, que puede tardar más que el timeout por defecto.

## Rate limiting

`slowapi` limita peticiones por IP. `/documents/upload` a `10/minute`, `/documents/query` a `5/minute` (más restrictivo por el coste de cómputo de la generación).

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
  processed/
```

## Docker

Docker Compose monta volúmenes para persistir datos:

- `./data/uploads:/app/data/uploads`
- `./data/processed:/app/data/processed`
- `./app:/app/app`

API expuesta en `http://127.0.0.1:8001`.

## Siguientes pasos

1. Ajustar parámetros de generación en Ollama (`temperature`, `keep_alive`) para reducir variabilidad y mejorar tiempos de respuesta en peticiones consecutivas.
2. Añadir `CORSMiddleware` restringido al dominio del frontend del portafolio.
3. Endurecer el rate limiting de `/query` pensando en tráfico público real.
4. Manejar de forma explícita el caso de portátil/GPU desconectado con un mensaje claro para el usuario final.
5. Simplificar el modelo de sesión para el caso de uso de chatbot de portafolio.
6. Mejorar chunking y embedding (detección de secciones/headings, modelo de embeddings más preciso).

## Documentación interactiva

Disponible en [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs). Usa el botón **Authorize** en Swagger UI para introducir `X-API-Key`.
</content>