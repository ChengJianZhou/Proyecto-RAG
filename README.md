# RAG Project

## Cómo arrancar

1. Clonar el repo.
2. Ejecutar:
   docker compose up --build
3. Verificar salud:
   curl http://localhost:8000/health
4. Subir un PDF:
   curl -F "file=@ejemplo.pdf" http://localhost:8000/documents/upload
5. Los archivos quedan en ./data/uploads