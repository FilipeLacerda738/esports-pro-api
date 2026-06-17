from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "Esports API"
    DATABASE_URL: str
    PANDASCORE_API_KEY: str
    PANDASCORE_KEYS: str = ""
    API_ACCESS_KEY: str
    ENVIRONMENT: str = "development"
    BACKEND_CORS_ORIGINS: List[str] = ["*"]
    SECRET_KEY: str

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()