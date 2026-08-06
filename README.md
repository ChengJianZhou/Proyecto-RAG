# RAG Project

Backend en FastAPI para un pipeline de **Retrieval-Augmented Generation (RAG)**. Permite subir documentos PDF, extraer y normalizar su texto, dividirlo en chunks semánticamente coherentes, generar embeddings vectoriales por chunk y persistir el resultado, como base para las siguientes fases de indexación vectorial, retrieval semántico y generación de respuestas con un LLM.

## Estado del proyecto

| Fase | Estado |
|---|---|
| Ingestión de PDFs (validación, extracción, chunking) | ✅ Completado |
| Generación de embeddings por chunk | ✅ Completado |
| Seguridad (API key, rate limiting, sesiones temporales) | ✅ Completado |
| Indexación en base de datos vectorial (Qdrant) | ✅ Completado |
| Borrado automático configurable (`ENABLE_CLEANUP`) | ✅ Completado |
| Endpoint de consulta `/query` (retrieval semántico) | ⏳ Pendiente |
| Generación de respuesta con LLM local (Ollama) | ⏳ Pendiente |

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
EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
QDRANT_URL=http://qdrant:6333
QDRANT_COLLECTION=documents
ENABLE_CLEANUP=false
```

> **Nota:** `ENABLE_CLEANUP=false` desactiva por completo el borrado automático de PDFs, JSON procesados y vectores en Qdrant. Esto se usa cuando el proyecto se orienta a un caso de uso de base de conocimiento persistente (por ejemplo, un chatbot de portafolio que responde preguntas sobre el autor), donde los documentos no deben expirar. Para el caso de uso original de subida temporal de documentos por sesión, se puede reactivar con `ENABLE_CLEANUP=true` y ajustar `SESSION_TTL_MINUTES` a un valor de producción razonable.

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

## Flujo actual

Al subir un PDF, la API:

1. Limpia documentos expirados de forma preventiva, solo si `ENABLE_CLEANUP=true`.
2. Valida que el archivo sea un PDF real mediante magic number (`%PDF-`), no solo por `content-type`.
3. Comprueba el tamaño máximo permitido.
4. Genera un nombre seguro con UUID.
5. Extrae el texto con `pypdf` y lo normaliza (espacios y saltos de línea redundantes).
6. Divide el texto en chunks con `RecursiveCharacterTextSplitter` (LangChain), priorizando mantener párrafos y frases intactos antes de cortar por longitud fija.
7. Genera un embedding vectorial local por cada chunk con FastEmbed.
8. Indexa los chunks con embedding en Qdrant para retrieval semántico.
9. Guarda el PDF original en `data/uploads`.
10. Crea un JSON procesado en `data/processed` con texto, metadatos y embeddings.
11. Asocia el documento a una sesión temporal identificada por cookie.

## Persistencia de datos

Actualmente el proyecto guarda dos tipos de datos:

- `data/uploads`: PDF original subido por el usuario.
- `data/processed`: JSON procesado con metadatos, chunks y embeddings.
- Vectores en Qdrant, asociados a cada documento y sesión.

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

El borrado automático es **opcional** y se controla con la variable `ENABLE_CLEANUP`.

- Con `ENABLE_CLEANUP=true`:
  - Cada documento tiene un `expires_at`.
  - Un scheduler en background ejecuta limpieza periódica cada minuto.
  - También se ejecuta una limpieza preventiva al recibir cada subida.
  - Cuando un documento expira, se eliminan el PDF original, el JSON procesado asociado (incluyendo sus embeddings) y los vectores correspondientes en Qdrant.
- Con `ENABLE_CLEANUP=false` (valor por defecto):
  - El scheduler no se arranca.
  - No se ejecuta limpieza preventiva en el upload.
  - Los documentos y sus vectores se conservan indefinidamente.

Este flag permite alternar entre dos casos de uso distintos: una demo temporal orientada a subidas anónimas con retención limitada (`ENABLE_CLEANUP=true`), o una base de conocimiento persistente pensada para un chatbot que responde preguntas sobre un perfil o portafolio concreto (`ENABLE_CLEANUP=false`).

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

## Vectorstore (Qdrant)

Los chunks con embedding se indexan en Qdrant para permitir retrieval semántico:

- Colección configurable vía `QDRANT_COLLECTION`, con distancia coseno.
- Cada punto guarda como payload el texto del chunk y sus metadatos (`document_id`, `session_id`, `filename`, `chunk_index`, `length`).
- El ID de cada punto se calcula de forma determinista con `uuid5` a partir del `chunk_id`, evitando duplicados si se reprocesa el mismo documento.
- `search()` permite filtrar por `session_id` y/o `document_id` al recuperar los chunks más similares a una query.
- `delete_document()` elimina todos los puntos asociados a un documento, usado por el borrado automático cuando está activado.

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
  vectorstore/
    qdrant.py
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

1. Crear un endpoint `/query` que realice retrieval semántico filtrando por sesión/documento.
2. Conectar el retrieval a un modelo generativo (LLM) local vía Ollama para producir respuestas con contexto.
3. Evaluar y, si procede, mejorar aún más el chunking (detección de secciones/headings).
4. Simplificar el modelo de sesión para el caso de uso de chatbot de portafolio, donde no hay usuarios anónimos subiendo documentos ajenos.

## Documentación interactiva

Disponible en:

- [http://127.0.0.1:8001/docs](http://127.0.0.1:8001/docs)

Si el endpoint requiere API key, usa el botón **Authorize** en Swagger UI para introducir `X-API-Key`.
</content>