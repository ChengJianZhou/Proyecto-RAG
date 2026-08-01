from contextlib import asynccontextmanager

from fastapi import FastAPI
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler

from app.core.config import settings
from app.core.limiter import limiter
from app.core.scheduler import start_scheduler, stop_scheduler
from app.health.router import router as health_router
from app.documents.router import router as documents_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestiona tareas de arranque y apagado de la aplicación.
    """
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
)

# Registra el limiter en el estado global de la app, requerido por slowapi
app.state.limiter = limiter

# Respuesta estándar cuando se supera el rate limit
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Routers de la aplicación
app.include_router(health_router)
app.include_router(documents_router)