from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ClipIQ API"
    app_env: str = "development"
    api_prefix: str = "/api"
    backend_cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:5174,http://127.0.0.1:5174,"
        "http://localhost:5175,http://127.0.0.1:5175"
    )

    # No localhost default. App must read this from .env.
    mongodb_uri: str
    mongodb_db: str = "clipiq"

    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str | None = None
    qdrant_collection: str = "video_transcript_chunks"
    embedding_dimension: int = 1536
    openai_api_key: str | None = None
    openai_embedding_model: str = "text-embedding-3-small"
    embedding_provider: str = "sentence_transformers"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    openai_chat_model: str = "gpt-4o-mini"
    groq_api_key: str | None = None
    groq_chat_model: str = "llama-3.3-70b-versatile"
    ytdlp_timeout_seconds: int = 45
    ytdlp_cookies_file: str | None = None
    youtube_cookies_file: str | None = None
    instagram_cookies_file: str | None = None
    enable_whisper_fallback: bool = False
    whisper_model: str = "base"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    return settings
