import json
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
from langchain_core.messages import AIMessage

from backend.app.ai.contracts import (
    ChatMessage,
    GenerationRequest,
    RuntimeContext,
    EmbeddingRequest,
)
from backend.app.ai.providers.deepseek import DeepSeekGenerationProvider
from backend.app.ai.providers.ollama import OllamaEmbeddingProvider
from backend.app.core.config import Settings
from backend.app.domain.exceptions import EmbeddingError


def test_deepseek_provider_can_be_created():
    settings = Settings(
        deepseek_api_key="test-key",
        _env_file=None,
    )

    provider = DeepSeekGenerationProvider(settings)

    assert provider._model_name == settings.deepseek_model


def test_ollama_provider_can_be_created():
    settings = Settings(_env_file=None)

    provider = OllamaEmbeddingProvider(settings)

    assert provider._model_name == settings.ollama_embedding_model
    assert provider._dimension == settings.embedding_dimension

@pytest.mark.asyncio
async def test_ollama_provider_sends_bounded_options_and_normalizes_embeddings():
    settings = Settings(_env_file=None)
    captured_payload = None

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_payload
        captured_payload = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "embeddings": [
                    [0.1] * settings.embedding_dimension,
                    [0.2] * settings.embedding_dimension,
                ]
            },
        )

    provider = OllamaEmbeddingProvider(
        settings,
        transport=httpx.MockTransport(handler),
    )

    request = EmbeddingRequest(
        context=RuntimeContext(
            tenant_id="tenant-1",
            agent_id="agent-1",
        ),
        texts=["First text", "Second text"],
    )

    result = await provider.embed(request)

    assert len(result.embeddings) == 2
    assert result.dimension == settings.embedding_dimension
    assert result.model == settings.ollama_embedding_model
    assert captured_payload == {
        "model": settings.ollama_embedding_model,
        "input": request.texts,
        "dimensions": settings.embedding_dimension,
        "truncate": True,
        "keep_alive": settings.ollama_embedding_keep_alive,
        "options": {
            "num_ctx": settings.ollama_embedding_num_ctx,
            "num_batch": settings.ollama_embedding_num_batch,
        },
    }


@pytest.mark.asyncio
async def test_ollama_provider_retries_transient_server_failure():
    settings = Settings(
        ollama_embedding_max_retries=2,
        ollama_embedding_retry_base_seconds=0,
        _env_file=None,
    )
    attempts = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            return httpx.Response(500, json={"error": "temporary"})
        return httpx.Response(
            200,
            json={
                "embeddings": [[0.1] * settings.embedding_dimension]
            },
        )

    provider = OllamaEmbeddingProvider(
        settings,
        transport=httpx.MockTransport(handler),
    )
    request = EmbeddingRequest(
        context=RuntimeContext(tenant_id="tenant-1", agent_id="agent-1"),
        texts=["Retry this text"],
    )

    result = await provider.embed(request)

    assert attempts == 2
    assert len(result.embeddings) == 1


@pytest.mark.asyncio
async def test_ollama_provider_raises_safe_error_after_retry_exhaustion():
    settings = Settings(
        ollama_embedding_max_retries=2,
        ollama_embedding_retry_base_seconds=0,
        _env_file=None,
    )
    attempts = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        return httpx.Response(
            500,
            json={"error": "C:/private/internal/model/path"},
        )

    provider = OllamaEmbeddingProvider(
        settings,
        transport=httpx.MockTransport(handler),
    )
    request = EmbeddingRequest(
        context=RuntimeContext(tenant_id="tenant-1", agent_id="agent-1"),
        texts=["This request will fail safely"],
    )

    with pytest.raises(
        EmbeddingError,
        match="temporarily unavailable",
    ) as exc_info:
        await provider.embed(request)

    assert attempts == 3
    assert "private" not in str(exc_info.value)

@pytest.mark.asyncio
async def test_deepseek_provider_normalizes_generation_result():
    settings = Settings(
        deepseek_api_key="test-key",
        _env_file=None,
    )
    provider = DeepSeekGenerationProvider(settings)

    bound_model = Mock()
    bound_model.ainvoke = AsyncMock(
        return_value=AIMessage(
            content="Test response",
            usage_metadata={
                "input_tokens": 10,
                "output_tokens": 4,
                "total_tokens": 14,
            },
            response_metadata={
                "model_name": settings.deepseek_model,
                "finish_reason": "stop",
            },
        )
    )

    provider._model = Mock()
    provider._model.bind.return_value = bound_model

    request = GenerationRequest(
        context=RuntimeContext(
            tenant_id="tenant-1",
            agent_id="agent-1",
        ),
        messages=[
            ChatMessage(role="user", content="Hello"),
        ],
    )

    result = await provider.generate(request)

    assert result.content == "Test response"
    assert result.model == settings.deepseek_model
    assert result.finish_reason == "stop"
    assert result.prompt_tokens == 10
    assert result.completion_tokens == 4
