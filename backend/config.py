from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    openai_base_url: str
    openai_api_key: str
    openai_model: str
    openai_embedding_base_url: str
    openai_embedding_api_key: str
    openai_embedding_model: str
    max_tokens: int
    cors_origins: str
    database_url: str = "sqlite+aiosqlite:///./policylens.db"
    jwt_secret: str = "change-this-to-a-random-64-char-string"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440


@lru_cache()
def get_settings() -> Settings:
    return Settings()
