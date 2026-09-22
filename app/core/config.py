from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Esports API"
    ENVIRONMENT: Literal["development", "test", "production"]
    DATABASE_URL: str = Field(repr=False)
    DATABASE_SSL: bool = True
    DATABASE_CA_FILE: str | None = None
    PANDASCORE_API_KEY: str = Field(min_length=1, repr=False)
    PANDASCORE_KEYS: str = Field(default="", repr=False)
    API_ACCESS_KEY: str = Field(min_length=32, max_length=256, repr=False)
    SECRET_KEY: str = Field(min_length=32, max_length=256, repr=False)
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=60 * 24 * 7, ge=1, le=60 * 24 * 30)
    JWT_ISSUER: str = "esports-api"
    JWT_AUDIENCE: str = "esports-app"
    BACKEND_CORS_ORIGINS: list[str] = Field(default_factory=list)
    RATE_LIMIT_STORAGE_URI: str = Field(default="memory://", repr=False)

    model_config = SettingsConfigDict(env_file=".env", extra="ignore", hide_input_in_errors=True)

    @model_validator(mode="after")
    def validate_security(self):
        if self.SECRET_KEY == self.API_ACCESS_KEY:
            raise ValueError("SECRET_KEY must be different from the mobile API key")
        if not self.SECRET_KEY.strip() or not self.API_ACCESS_KEY.strip():
            raise ValueError("Security keys cannot be blank")
        for origin in self.BACKEND_CORS_ORIGINS:
            parsed = urlsplit(origin)
            if ("*" in origin or parsed.scheme not in {"http", "https"}
                    or not parsed.netloc or parsed.path or parsed.query
                    or parsed.fragment or parsed.username or parsed.password):
                raise ValueError("CORS origins must be explicit HTTP(S) origins without paths")
            if self.ENVIRONMENT == "production" and parsed.scheme != "https":
                raise ValueError("Production CORS origins must use HTTPS")
        if not self.DATABASE_SSL:
            host = urlsplit(self.DATABASE_URL).hostname
            if self.ENVIRONMENT == "production" or host not in {"localhost", "127.0.0.1", "::1"}:
                raise ValueError("TLS can only be disabled for a local development/test database")
        storage = urlsplit(self.RATE_LIMIT_STORAGE_URI)
        if storage.scheme not in {"memory", "redis", "rediss"}:
            raise ValueError("Unsupported rate limit storage")
        if self.ENVIRONMENT == "production":
            if storage.scheme == "redis" and storage.hostname not in {"localhost", "127.0.0.1", "::1"}:
                raise ValueError("Remote production Redis must use rediss://")
            if storage.query:
                raise ValueError("Configure production Redis without URL query overrides")
        return self


settings = Settings()
