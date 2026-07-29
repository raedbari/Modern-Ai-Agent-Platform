"""Tests for the Core AI Runtime."""

from unittest.mock import AsyncMock

import pytest

from backend.app.ai.contracts import (
    ChatMessage,
    EmbeddingRequest,
    EmbeddingResult,
    GenerationRequest,
    GenerationResult,
    RuntimeContext,
)
from backend.app.ai.runtime import CoreAIRuntime


@pytest.mark.asyncio
async def test_runtime_generates_through_langgraph():
    generation_provider = AsyncMock()
    embedding_provider = AsyncMock()

    expected = GenerationResult(
        content="Runtime response",
        model="test-model",
        finish_reason="stop",
        prompt_tokens=5,
        completion_tokens=3,
    )
    generation_provider.generate.return_value = expected

    runtime = CoreAIRuntime(
        generation_provider=generation_provider,
        embedding_provider=embedding_provider,
    )

    request = GenerationRequest(
        context=RuntimeContext(
            tenant_id="tenant-1",
            agent_id="agent-1",
        ),
        messages=[ChatMessage(role="user", content="Hello")],
    )

    result = await runtime.generate(request)

    assert result == expected
    generation_provider.generate.assert_awaited_once_with(request)


@pytest.mark.asyncio
async def test_runtime_delegates_embeddings():
    generation_provider = AsyncMock()
    embedding_provider = AsyncMock()

    expected = EmbeddingResult(
        embeddings=[[0.1] * 1024],
        model="qwen3-embedding:0.6b",
        dimension=1024,
    )
    embedding_provider.embed.return_value = expected

    runtime = CoreAIRuntime(
        generation_provider=generation_provider,
        embedding_provider=embedding_provider,
    )

    request = EmbeddingRequest(
        context=RuntimeContext(
            tenant_id="tenant-1",
            agent_id="agent-1",
        ),
        texts=["Test text"],
    )

    result = await runtime.embed(request)

    assert result == expected
    embedding_provider.embed.assert_awaited_once_with(request)