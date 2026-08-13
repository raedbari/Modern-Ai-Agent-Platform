"""Tests for environment-backed application settings."""

import pytest
from pydantic import ValidationError

from backend.app.core.config import Settings, get_settings

RUNTIME_ENVIRONMENT_VARIABLES = (
    "MAAP_ENVIRONMENT",
    "MAAP_ADMIN_API_KEY",
    "MAAP_DEEPSEEK_API_KEY",
    "MAAP_DEEPSEEK_BASE_URL",
    "MAAP_DEEPSEEK_MODEL",
    "MAAP_DEEPSEEK_TIMEOUT_SECONDS",
    "MAAP_DEEPSEEK_MAX_RETRIES",
    "MAAP_OLLAMA_BASE_URL",
    "MAAP_OLLAMA_EMBEDDING_MODEL",
    "MAAP_EMBEDDING_DIMENSION",
    "MAAP_OLLAMA_TIMEOUT_SECONDS",
    "MAAP_OLLAMA_EMBEDDING_NUM_CTX",
    "MAAP_OLLAMA_EMBEDDING_NUM_BATCH",
    "MAAP_OLLAMA_EMBEDDING_KEEP_ALIVE",
    "MAAP_OLLAMA_EMBEDDING_MAX_RETRIES",
    "MAAP_OLLAMA_EMBEDDING_RETRY_BASE_SECONDS",
    "MAAP_MAX_UPLOAD_SIZE_BYTES",
    "MAAP_MAX_PDF_PAGES",
    "MAAP_UPLOAD_STORAGE_ROOT",
    "MAAP_INGESTION_WORKER_POLL_SECONDS",
    "MAAP_INGESTION_JOB_LOCK_TIMEOUT_SECONDS",
    "MAAP_INGESTION_JOB_MAX_ATTEMPTS",
    "MAAP_CHUNK_SIZE",
    "MAAP_CHUNK_OVERLAP",
    "MAAP_EMBEDDING_BATCH_SIZE",
    "MAAP_RETRIEVAL_TOP_K",
    "MAAP_RETRIEVAL_MIN_SIMILARITY",
    "MAAP_RAG_MAX_CONTEXT_CHARS",
    "MAAP_JWT_SECRET_KEY",
    "MAAP_JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
    "MAAP_JWT_REFRESH_TOKEN_EXPIRE_DAYS",
    "MAAP_ADMIN_LEGACY_KEY_ENABLED",
    "MAAP_TRUSTED_PROXY_CIDRS",
    "MAAP_REDIS_URL",
    "MAAP_ADMIN_LOGIN_RATE_LIMIT_PER_ACCOUNT",
    "MAAP_ADMIN_LOGIN_RATE_LIMIT_PER_IP",
    "MAAP_ADMIN_LOGIN_RATE_LIMIT_WINDOW_SECONDS",
    "MAAP_WIDGET_JWT_SECRET_KEY",
    "MAAP_WIDGET_JWT_ISSUER",
    "MAAP_WIDGET_JWT_AUDIENCE",
    "MAAP_WIDGET_TOKEN_LIFETIME_SECONDS",
    "MAAP_WIDGET_BOOTSTRAP_RATE_LIMIT_PER_WIDGET",
    "MAAP_WIDGET_BOOTSTRAP_RATE_LIMIT_PER_IP",
    "MAAP_WIDGET_BOOTSTRAP_RATE_LIMIT_WINDOW_SECONDS",
    "MAAP_WIDGET_CHAT_RATE_LIMIT_PER_SESSION",
    "MAAP_WIDGET_CHAT_RATE_LIMIT_WINDOW_SECONDS",
)


@pytest.fixture(autouse=True)
def isolate_settings(monkeypatch: pytest.MonkeyPatch):
    """Prevent machine environment variables and cache from leaking into tests."""
    for variable_name in RUNTIME_ENVIRONMENT_VARIABLES:
        monkeypatch.delenv(variable_name, raising=False)

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_runtime_settings_have_expected_defaults():
    settings = Settings(_env_file=None)

    assert settings.deepseek_model == "deepseek-v4-flash"
    assert settings.deepseek_max_retries == 2
    assert settings.ollama_embedding_model == "qwen3-embedding:0.6b"
    assert settings.embedding_dimension == 1024
    assert settings.ollama_embedding_num_ctx == 1024
    assert settings.ollama_embedding_num_batch == 64
    assert settings.ollama_embedding_max_retries == 2
    assert settings.embedding_batch_size == 8
    assert settings.rag_max_context_chars == 12000
    assert settings.ingestion_job_max_attempts == 3
    assert ".md" in settings.allowed_extensions
    assert ".html" not in settings.allowed_extensions


def test_runtime_settings_can_be_overridden_from_environment(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("MAAP_DEEPSEEK_MODEL", "deepseek-v4-pro")
    monkeypatch.setenv("MAAP_EMBEDDING_DIMENSION", "2048")

    settings = get_settings()

    assert settings.deepseek_model == "deepseek-v4-pro"
    assert settings.embedding_dimension == 2048


def test_production_requires_deepseek_api_key():
    with pytest.raises(
        ValidationError,
        match="MAAP_DEEPSEEK_API_KEY",
    ):
        Settings(
            environment="production",
            deepseek_api_key=None,
            _env_file=None,
        )


def test_production_requires_admin_api_key():
    with pytest.raises(
        ValidationError,
        match="MAAP_ADMIN_API_KEY",
    ):
        Settings(
            environment="production",
            deepseek_api_key="test-deepseek-key",
            voyage_api_key="test-voyage-key",
            admin_api_key=None,
            _env_file=None,
        )


def test_admin_api_key_is_masked():
    settings = Settings(
        admin_api_key="test-admin-secret",
        _env_file=None,
    )

    assert "test-admin-secret" not in repr(settings)
    assert settings.admin_api_key is not None
    assert (
        settings.admin_api_key.get_secret_value()
        == "test-admin-secret"
    )


def test_deepseek_api_key_is_masked():
    settings = Settings(
        deepseek_api_key="test-secret-value",
        _env_file=None,
    )

    assert "test-secret-value" not in repr(settings)
    assert settings.deepseek_api_key is not None
    assert settings.deepseek_api_key.get_secret_value() == "test-secret-value"


def test_chunk_overlap_must_be_smaller_than_chunk_size():
    with pytest.raises(ValidationError, match="chunk_overlap"):
        Settings(
            chunk_size=100,
            chunk_overlap=100,
            _env_file=None,
        )


def test_short_admin_jwt_secret_is_rejected():
    with pytest.raises(ValidationError, match="at least 32 bytes"):
        Settings(jwt_secret_key="x", _env_file=None)


def test_production_requires_admin_jwt_secret():
    with pytest.raises(ValidationError, match="MAAP_JWT_SECRET_KEY"):
        Settings(
            environment="production",
            deepseek_api_key="test-deepseek-key",
            voyage_api_key="test-voyage-key",
            admin_api_key="test-admin-key",
            jwt_secret_key=None,
            _env_file=None,
        )


def test_production_requires_shared_redis():
    with pytest.raises(ValidationError, match="MAAP_REDIS_URL"):
        Settings(
            environment="production",
            deepseek_api_key="test-deepseek-key",
            voyage_api_key="test-voyage-key",
            admin_api_key="test-admin-key",
            jwt_secret_key="x" * 32,
            redis_url=None,
            _env_file=None,
        )


def test_short_widget_jwt_secret_is_rejected():
    with pytest.raises(ValidationError, match="at least 32 bytes"):
        Settings(widget_jwt_secret_key="x", _env_file=None)


def test_production_requires_widget_jwt_secret():
    with pytest.raises(
        ValidationError,
        match="MAAP_WIDGET_JWT_SECRET_KEY",
    ):
        Settings(
            environment="production",
            deepseek_api_key="test-deepseek-key",
            voyage_api_key="test-voyage-key",
            admin_api_key="test-admin-key",
            jwt_secret_key="x" * 32,
            redis_url="redis://redis:6379/0",
            widget_jwt_secret_key=None,
            _env_file=None,
        )
