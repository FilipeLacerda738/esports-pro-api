from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Esports API"
    DATABASE_URL: str
    PANDASCORE_API_KEY: str
    API_ACCESS_KEY: str

    class Config:
        env_file = ".env"

settings = Settings()