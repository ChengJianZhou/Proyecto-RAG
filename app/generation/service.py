import httpx

from typing import List

from app.core.config import settings
from app.embeddings.service import embed_query
from app.vectorstore.qdrant import search

TIMEOUT = 120.0

SYSTEM_PROMPT = (
    "Eres el asistente personal de Marcos. Respondes preguntas sobre su perfil, "
    "experiencia y proyectos usando SOLO el contexto proporcionado a continuación. "
    "Si la respuesta no está en el contexto, dilo claramente en vez de inventar."
)


def build_prompt(question: str, context_chunks: List[str]) -> str:
    context = "\n\n".join(context_chunks) if context_chunks else "(sin contexto disponible)"
    return f"{SYSTEM_PROMPT}\n\nContexto:\n{context}\n\nPregunta: {question}\nRespuesta:"


def answer_question(question: str, top_k: int = 5) -> tuple[str, List[str]]:
    query_vector = embed_query(question)

    if not query_vector:
        return "No se pudo procesar la pregunta.", []

    results = search(query_vector, top_k=top_k)

    context_chunks = [r.payload["text"] for r in results]
    sources = [r.payload["chunk_id"] for r in results]

    prompt = build_prompt(question, context_chunks)
    answer = generate_answer(prompt)

    return answer, sources

def generate_answer(prompt: str, model: str | None = None) -> str:
    """
    Envía un prompt al servidor Ollama y devuelve el texto generado.

    Si Ollama no responde (portátil apagado, red caída, etc.),
    lanza RuntimeError con un mensaje claro para que el endpoint
    pueda devolver un error controlado en vez de un 500 genérico.
    """
    payload = {
        "model": model or settings.ollama_model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2
        },
    }

    try:
        response = httpx.post(
            f"{settings.ollama_base_url}/api/generate",
            json=payload,
            timeout=TIMEOUT,
        )
        response.raise_for_status()
    except httpx.RequestError as exc:
        raise RuntimeError("El servicio de generación no está disponible") from exc
    except httpx.HTTPStatusError as exc:
        raise RuntimeError(f"Ollama devolvió un error: {exc.response.text}") from exc

    return response.json()["response"]