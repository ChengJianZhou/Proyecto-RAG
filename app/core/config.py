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

    embedding_model: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

settings = Settings()