from fastapi import FastAPI
from slowapi.errors import RateLimitExceeded
from slowapi import _rate_limit_exceeded_handler
from app.core.limiter import limiter
from app.health.router import router as health_router
from app.documents.router import router as documents_router

app = FastAPI(title="RAG API")

# Registra el limiter en el estado global de la app, requerido por slowapi
app.state.limiter = limiter

# Define qué responder cuando se supera el límite de rate limiting (429 Too Many Requests)
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Cada router se "engancha" a la app principal, como registrar un @Bean controller en Spring
app.include_router(health_router)
app.include_router(documents_router)