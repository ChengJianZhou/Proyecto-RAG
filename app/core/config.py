from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "RAG API"
    upload_dir: str = "data/uploads"
    processed_dir: str = "data/processed"
    max_upload_size_mb: int = 20
    api_key: str

    session_cookie_name: str = "rag_session_id"
    session_ttl_minutes: int = 1
    secure_cookies: bool = False

    enable_cleanup: bool = False

    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

    qdrant_url: str = "http://qdrant:6333"
    qdrant_collection: str = "documents"

    ollama_base_url: str = "http://192.168.1.137:11434"
    ollama_model: str = "llama3.2:3b"

settings = Settings()