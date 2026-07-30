"""Tests for environment-backed application settings."""

import pytest
from pydantic import ValidationError

from backend.app.core.config import Settings, get_settings

RUNTIME_ENVIRONMENT_VARIABLES = (
    "MAAP_ENVIRONMENT",
    "MAAP_DEEPSEEK_API_KEY",
    "MAAP_DEEPSEEK_BASE_URL",
    "MAAP_DEEPSEEK_MODEL",
    "MAAP_DEEPSEEK_TIMEOUT_SECONDS",
    "MAAP_DEEPSEEK_MAX_RETRIES",
    "MAAP_OLLAMA_BASE_URL",
    "MAAP_OLLAMA_EMBEDDING_MODEL",
    "MAAP_EMBEDDING_DIMENSION",
    "MAAP_OLLAMA_TIMEOUT_SECONDS",
    "MAAP_MAX_UPLOAD_SIZE_BYTES",
    "MAAP_MAX_PDF_PAGES",
    "MAAP_CHUNK_SIZE",
    "MAAP_CHUNK_OVERLAP",
    "MAAP_EMBEDDING_BATCH_SIZE",
    "MAAP_RETRIEVAL_TOP_K",
    "MAAP_RETRIEVAL_MIN_SIMILARITY",
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
    assert settings.embedding_batch_size == 32
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
