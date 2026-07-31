from fastapi import FastAPI
from app.health.router import router as health_router
from app.documents.router import router as documents_router

app = FastAPI(title="RAG API")

app.include_router(health_router)
app.include_router(documents_router)