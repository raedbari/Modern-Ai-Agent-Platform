"""Environment-backed application settings."""

from functools import lru_cache
from ipaddress import ip_network
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

    admin_api_key: SecretStr | None = None

    deepseek_api_key: SecretStr | None = None
    deepseek_base_url: AnyHttpUrl = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-v4-flash"
    deepseek_timeout_seconds: float = Field(default=30.0, gt=0)
    deepseek_max_retries: int = Field(default=2, ge=0, le=5)

    ollama_base_url: AnyHttpUrl = "http://127.0.0.1:11434"
    ollama_embedding_model: str = "qwen3-embedding:0.6b"
    embedding_dimension: int = Field(default=1024, gt=0)
    ollama_timeout_seconds: float = Field(default=30.0, gt=0)
    # Bound the runner allocations for embedding-sized inputs.  The Ollama
    # defaults (4K context / a very large execution batch) can reserve more
    # than 1 GiB of one contiguous GPU buffer even for a single short text.
    ollama_embedding_num_ctx: int = Field(default=1024, ge=256, le=8192)
    ollama_embedding_num_batch: int = Field(default=64, ge=32, le=512)
    ollama_embedding_keep_alive: str = Field(
        default="10m",
        min_length=1,
        max_length=32,
    )
    ollama_embedding_max_retries: int = Field(default=2, ge=0, le=5)
    ollama_embedding_retry_base_seconds: float = Field(
        default=0.5,
        ge=0,
        le=10,
    )
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

    # Durable local object storage shared by API and ingestion workers.
    upload_storage_root: Path = BACKEND_DIR / ".data" / "uploads"

    # PostgreSQL-backed ingestion worker controls.
    ingestion_worker_poll_seconds: float = Field(default=2.0, gt=0, le=60)
    ingestion_job_lock_timeout_seconds: int = Field(
        default=600,
        ge=30,
        le=86400,
    )
    ingestion_job_max_attempts: int = Field(default=3, ge=1, le=10)

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
    embedding_batch_size: int = Field(default=8, gt=0, le=64)

    # ------------------------------------------------------------------ #
    # Retrieval                                                            #
    # ------------------------------------------------------------------ #

    # Default number of chunks returned by a similarity search.
    retrieval_top_k: int = Field(default=5, gt=0)

    # Minimum cosine similarity score required for a chunk to be included
    # in retrieval results. Range: 0.0 (no filtering) – 1.0 (exact match).
    retrieval_min_similarity: float = Field(default=0.5, ge=0.0, le=1.0)

    # Hard ceiling for retrieved text injected into one generation request.
    rag_max_context_chars: int = Field(default=12000, ge=500, le=100000)

    # ------------------------------------------------------------------ #
    # Admin authentication                                                 #
    # ------------------------------------------------------------------ #

    # HS256 signing key for admin JWT access tokens.
    # Must be at least 32 characters in staging and production.
    # Leave unset in development to disable JWT-based admin auth.
    jwt_secret_key: SecretStr | None = None

    # Lifetime of a short-lived admin access token, in minutes.
    jwt_access_token_expire_minutes: int = Field(default=15, gt=0, le=1440)

    # Lifetime of a long-lived admin refresh token, in days.
    jwt_refresh_token_expire_days: int = Field(default=7, gt=0, le=90)

    # When True the legacy X-Admin-Key header is accepted alongside JWT
    # Bearer tokens.  Set to False once all callers have migrated.
    admin_legacy_key_enabled: bool = True

    # Only direct peers in these networks may supply X-Forwarded-For.
    trusted_proxy_cidrs: tuple[str, ...] = ()

    # Shared Redis is mandatory outside development/test so rate limits work
    # consistently across all API containers.
    redis_url: SecretStr | None = None
    admin_login_rate_limit_per_account: int = Field(
        default=5,
        ge=1,
        le=1000,
    )
    admin_login_rate_limit_per_ip: int = Field(
        default=20,
        ge=1,
        le=10000,
    )
    admin_login_rate_limit_window_seconds: int = Field(
        default=60,
        ge=1,
        le=86400,
    )

    # ------------------------------------------------------------------ #
    # Argon2id password hashing                                           #
    # ------------------------------------------------------------------ #

    # Number of iterations (time cost).  OWASP minimum: 2.
    argon2_time_cost: int = Field(default=2, ge=1, le=16)

    # Memory usage in KiB.  OWASP minimum: 19456 (19 MiB).
    argon2_memory_cost: int = Field(default=19456, ge=8192)

    # Degree of parallelism (number of threads).
    argon2_parallelism: int = Field(default=1, ge=1, le=8)

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

        admin_key_missing = (
            self.admin_api_key is None
            or not self.admin_api_key.get_secret_value().strip()
        )
        if (
            requires_api_key
            and self.admin_legacy_key_enabled
            and admin_key_missing
        ):
            raise ValueError(
                "MAAP_ADMIN_API_KEY is required in staging and production"
            )

        jwt_secret_missing = (
            self.jwt_secret_key is None
            or not self.jwt_secret_key.get_secret_value().strip()
        )
        if requires_api_key and jwt_secret_missing:
            raise ValueError(
                "MAAP_JWT_SECRET_KEY is required in staging and production"
            )
        if not jwt_secret_missing:
            jwt_secret = self.jwt_secret_key.get_secret_value().strip()
            if len(jwt_secret.encode("utf-8")) < 32:
                raise ValueError(
                    "MAAP_JWT_SECRET_KEY must contain at least 32 bytes"
                )

        redis_missing = (
            self.redis_url is None
            or not self.redis_url.get_secret_value().strip()
        )
        if requires_api_key and redis_missing:
            raise ValueError(
                "MAAP_REDIS_URL is required in staging and production"
            )

        for cidr in self.trusted_proxy_cidrs:
            try:
                ip_network(cidr, strict=False)
            except ValueError as exc:
                raise ValueError(
                    f"Invalid trusted proxy CIDR: {cidr}"
                ) from exc

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
