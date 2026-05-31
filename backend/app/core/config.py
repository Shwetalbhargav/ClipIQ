from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ClipIQ"
    app_env: str = "development"
    api_prefix: str = "/api"
    backend_cors_origins: str = "http://localhost:5173"

    openai_api_key: str | None = None
    groq_api_key: str | None = None

    mongodb_uri: str = "mongodb://localhost:27017"
    mongodb_db: str = "clipiq"

    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None

    model_config = SettingsConfigDict(
        env_file="../.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()