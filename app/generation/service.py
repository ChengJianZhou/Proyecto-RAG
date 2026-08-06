import httpx

from app.core.config import settings

TIMEOUT = 120.0


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