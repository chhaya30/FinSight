from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    APP_NAME: str = "globalrisk-ai"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"

    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_WORKERS: int = 1

    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/globalrisk",
        description="PostgreSQL async connection URL",
    )
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL for caching",
    )

    LLM_PROVIDER: str = Field(
        default="groq",
        description="LLM provider: groq, ollama, claude",
    )
    GROQ_API_KEY: str | None = None
    GROQ_MODEL: str = "llama-3.1-70b-versatile"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1:70b"
    CLAUDE_API_KEY: str | None = None
    CLAUDE_MODEL: str = "claude-3-5-sonnet-20241022"

    EMBEDDING_PROVIDER: str = Field(
        default="sentence-transformers",
        description="Embedding provider: sentence-transformers, openai",
    )
    EMBEDDING_MODEL: str = "BAAI/bge-large-en-v1.5"
    EMBEDDING_DIMENSION: int = 1024
    OPENAI_API_KEY: str | None = None

    VECTOR_STORE_PROVIDER: str = Field(
        default="pgvector",
        description="Vector store: pgvector, pinecone",
    )
    PINECONE_API_KEY: str | None = None
    PINECONE_INDEX: str = "globalrisk"
    PINECONE_ENVIRONMENT: str = "us-east-1"

    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    MAX_CHUNKS_PER_DOC: int = 500

    OCR_ENABLED: bool = True
    OCR_LANGUAGE: str = "eng"
    TESSERACT_CMD: str | None = None

    UPLOAD_DIR: str = "./data/raw/annual_reports"
    EXTRACTED_DIR: str = "./data/extracted"
    PROCESSED_DIR: str = "./data/processed"
    MAX_UPLOAD_SIZE_MB: int = 100
    ALLOWED_EXTENSIONS: list[str] = [".pdf"]

    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    SECRET_KEY: str = Field(
        default="dev-secret-key-change-in-production",
        description="Secret key for JWT signing",
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    RISK_TAXONOMY_PATH: str = "./app/taxonomy/data/risk_taxonomy_v1.json"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
