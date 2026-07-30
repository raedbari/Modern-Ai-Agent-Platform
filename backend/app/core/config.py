"""Environment-backed application settings."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AnyHttpUrl, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    """Validated settings loaded from environment variables or backend/.env."""

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

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        env_prefix="MAAP_",
        extra="ignore",
    )

    @model_validator(mode="after")
    def require_production_secrets(self) -> "Settings":
        """Reject staging and production startup without required secrets."""
        requires_api_key = self.environment in {"staging", "production"}
        api_key_missing = (
            self.deepseek_api_key is None
            or not self.deepseek_api_key.get_secret_value().strip()
        )

        if requires_api_key and api_key_missing:
            raise ValueError(
                "MAAP_DEEPSEEK_API_KEY is required in staging and production"
            )

        return self


@lru_cache
def get_settings() -> Settings:
    """Return one cached settings instance per application process."""
    return Settings()
