from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "Esports API"
    DATABASE_URL: str
    PANDASCORE_API_KEY: str
    PANDASCORE_KEYS: str = ""
    API_ACCESS_KEY: str
    ENVIRONMENT: str = "development"
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    class Config:
        env_file = ".env"

settings = Settings()