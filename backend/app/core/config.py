"""Environment-backed application settings."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AnyHttpUrl, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Validated settings loaded from environment variables or backend/.env."""

    # ------------------------------------------------------------------ #
    # Application                                                          #
    # ------------------------------------------------------------------ #

    app_name: str = "Modern AI Agent Platform API"
    app_version: str = "0.1.0"
    environment: Literal["development", "test", "staging", "production"] = (
        "development"
    )
    debug: bool = False

    deepseek_api_key: SecretStr | None = None
    deepseek_base_url: AnyHttpUrl = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-v4-flash"
    deepseek_timeout_seconds: float = Field(default=30.0, gt=0)
    deepseek_max_retries: int = Field(default=2, ge=0, le=5)

    ollama_base_url: AnyHttpUrl = "http://127.0.0.1:11434"
    ollama_embedding_model: str = "qwen3-embedding:0.6b"
    embedding_dimension: int = Field(default=1024, gt=0)
    ollama_timeout_seconds: float = Field(default=30.0, gt=0)
    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5432/maap"
    )

    # ------------------------------------------------------------------ #
    # File processing                                                      #
    # ------------------------------------------------------------------ #

    # Maximum size of a single uploaded file, in bytes (default: 20 MB).
    max_upload_size_bytes: int = Field(default=20 * 1024 * 1024, gt=0)

    # Maximum number of pages accepted from a PDF document.
    max_pdf_pages: int = Field(default=500, gt=0)

    # File extensions accepted by the ingestion pipeline.
    allowed_extensions: frozenset[str] = frozenset(
        {".pdf", ".docx", ".txt", ".md", ".markdown"}
    )

    # MIME types accepted by the ingestion pipeline.
    allowed_mime_types: frozenset[str] = frozenset(
        {
            "application/pdf",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "text/plain",
            "text/markdown",
        }
    )

    # ------------------------------------------------------------------ #
    # Chunking                                                             #
    # ------------------------------------------------------------------ #

    # Target character count for each chunk produced during ingestion.
    chunk_size: int = Field(default=1000, gt=0)

    # Number of characters shared between consecutive chunks.
    chunk_overlap: int = Field(default=200, ge=0)

    # ------------------------------------------------------------------ #
    # Embeddings                                                           #
    # ------------------------------------------------------------------ #

    # Maximum number of chunks sent to the embedding provider per call.
    embedding_batch_size: int = Field(default=32, gt=0, le=64)

    # ------------------------------------------------------------------ #
    # Retrieval                                                            #
    # ------------------------------------------------------------------ #

    # Default number of chunks returned by a similarity search.
    retrieval_top_k: int = Field(default=5, gt=0)

    # Minimum cosine similarity score required for a chunk to be included
    # in retrieval results. Range: 0.0 (no filtering) – 1.0 (exact match).
    retrieval_min_similarity: float = Field(default=0.5, ge=0.0, le=1.0)

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        env_prefix="MAAP_",
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_runtime_settings(self) -> "Settings":
        """Validate production secrets and safe RAG window settings."""
        requires_api_key = self.environment in {"staging", "production"}
        api_key_missing = (
            self.deepseek_api_key is None
            or not self.deepseek_api_key.get_secret_value().strip()
        )

        if requires_api_key and api_key_missing:
            raise ValueError(
                "MAAP_DEEPSEEK_API_KEY is required in staging and production"
            )

        if self.chunk_overlap >= self.chunk_size:
            raise ValueError(
                f"chunk_overlap ({self.chunk_overlap}) must be strictly less than "
                f"chunk_size ({self.chunk_size})."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """Return one cached settings instance per application process."""
    return Settings()
