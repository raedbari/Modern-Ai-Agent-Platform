from unittest.mock import AsyncMock, Mock

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
async def test_ollama_provider_normalizes_embeddings():
    settings = Settings(_env_file=None)
    provider = OllamaEmbeddingProvider(settings)

    provider._model = Mock()
    provider._model.aembed_documents = AsyncMock(
        return_value=[
            [0.1] * settings.embedding_dimension,
            [0.2] * settings.embedding_dimension,
        ]
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
    provider._model.aembed_documents.assert_awaited_once_with(request.texts)

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