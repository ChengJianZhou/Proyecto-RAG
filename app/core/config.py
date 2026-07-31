from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # SettingsConfigDict le dice a Pydantic que lea variables desde el archivo .env
    # extra="ignore" evita que falle si el .env tiene variables que no están declaradas aquí
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "RAG API"          # Valor por defecto si no está en .env
    upload_dir: str = "data/uploads"   # Carpeta donde se guardan los PDFs
    max_upload_size_mb: int = 20       # Límite de tamaño de archivo permitido

    # Sin valor por defecto: si falta en .env, la app NO arranca (fail-fast)
    # Esto evita que el servicio quede corriendo sin protección por un despiste
    api_key: str

# Instancia única que se importa en todo el proyecto (patrón singleton)
settings = Settings()