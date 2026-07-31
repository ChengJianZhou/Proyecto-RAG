from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "RAG API"
    upload_dir: str = "data/uploads"
    max_upload_size_mb: int = 20

settings = Settings()