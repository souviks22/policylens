from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    environment: str = "development"
    cors_origins: str = "http://localhost:3000"
    database_url: str = "sqlite+aiosqlite:///./policylens.db"
    chroma_path: str = "./chroma_db"

    openai_api_key: str
    openai_model: str
    openai_embedding_model: str
    chroma_api_key: str
    chroma_tenant_id: str
    chroma_database_name: str
    rag_top_k: int
    rag_score_threshold: float
    rag_max_context_chars: int
    jwt_secret: str
    jwt_algorithm: str
    jwt_expire_minutes: int

@lru_cache()
def get_settings() -> Settings:
    return Settings()
