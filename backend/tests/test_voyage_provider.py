"""Unit tests for VoyageEmbeddingProvider with mocked HTTP transport."""

import json
from typing import Any

import httpx
import pytest
from unittest.mock import AsyncMock

from backend.app.ai.contracts import EmbeddingRequest, RuntimeContext
from backend.app.ai.providers.voyage import (
    VoyageEmbeddingProvider,
    VOYAGE_EMBEDDING_DIMENSION,
)
from backend.app.core.config import Settings
from backend.app.domain.exceptions import EmbeddingError


def _mock_voyage_response(embeddings: list[list[float]]) -> bytes:
    """Create a mock Voyage API response."""
    return json.dumps({
        "data": [{"embedding": emb} for emb in embeddings],
        "model": "voyage-4-large",
        "usage": {"total_tokens": len(embeddings) * 10}
    }).encode()


def _mock_transport(
    status_code: int = 200,
    response_body: bytes | None = None,
) -> httpx.AsyncBaseTransport:
    """Create a mocked HTTP transport."""
    transport = AsyncMock(spec=httpx.AsyncBaseTransport)

    if response_body is None:
        # Default: 2 embeddings of 1024 dimensions
        response_body = _mock_voyage_response([
            [0.1] * VOYAGE_EMBEDDING_DIMENSION,
            [0.2] * VOYAGE_EMBEDDING_DIMENSION,
        ])

    mock_response = httpx.Response(
        status_code=status_code,
        content=response_body,
        headers={"content-type": "application/json"},
    )

    async def mock_handle_async_request(*args: Any, **kwargs: Any) -> httpx.Response:
        return mock_response

    transport.handle_async_request = mock_handle_async_request
    return transport


@pytest.fixture
def settings_with_voyage_key() -> Settings:
    """Settings with a valid Voyage API key."""
    return Settings(
        voyage_api_key="test_voyage_key",
        voyage_base_url="https://api.voyageai.com/v1",
        voyage_model="voyage-4-large",
        embedding_dimension=1024,
    )


@pytest.mark.asyncio
async def test_voyage_provider_embed_success(
    settings_with_voyage_key: Settings,
) -> None:
    """Test successful embedding generation."""
    transport = _mock_transport()
    provider = VoyageEmbeddingProvider(
        settings_with_voyage_key,
        transport=transport,
    )

    request = EmbeddingRequest(
        context=RuntimeContext(tenant_id="t1", agent_id="a1"),
        texts=["text1", "text2"],
    )

    result = await provider.embed(request)

    assert len(result.embeddings) == 2
    assert result.model == "voyage-4-large"
    assert result.dimension == VOYAGE_EMBEDDING_DIMENSION


@pytest.mark.asyncio
async def test_voyage_provider_returns_1024_dimensions(
    settings_with_voyage_key: Settings,
) -> None:
    """Test that embeddings have exactly 1024 dimensions."""
    # Mock response with 1 embedding for 1 text
    response_body = _mock_voyage_response([[0.1] * VOYAGE_EMBEDDING_DIMENSION])
    transport = _mock_transport(response_body=response_body)
    provider = VoyageEmbeddingProvider(
        settings_with_voyage_key,
        transport=transport,
    )

    request = EmbeddingRequest(
        context=RuntimeContext(tenant_id="t1", agent_id="a1"),
        texts=["test"],
    )

    result = await provider.embed(request)

    assert len(result.embeddings[0]) == VOYAGE_EMBEDDING_DIMENSION
    assert result.dimension == VOYAGE_EMBEDDING_DIMENSION


@pytest.mark.asyncio
async def test_voyage_provider_validates_dimension_mismatch(
    settings_with_voyage_key: Settings,
) -> None:
    """Test that dimension mismatch raises EmbeddingError."""
    # Mock response with wrong dimension (512 instead of 1024)
    wrong_dim_response = _mock_voyage_response([[0.1] * 512])
    transport = _mock_transport(response_body=wrong_dim_response)

    provider = VoyageEmbeddingProvider(
        settings_with_voyage_key,
        transport=transport,
    )

    request = EmbeddingRequest(
        context=RuntimeContext(tenant_id="t1", agent_id="a1"),
        texts=["test"],
    )

    with pytest.raises(EmbeddingError, match="incorrect dimension"):
        await provider.embed(request)


@pytest.mark.asyncio
async def test_voyage_provider_validates_count_mismatch(
    settings_with_voyage_key: Settings,
) -> None:
    """Test that count mismatch raises EmbeddingError."""
    # Mock response with 1 embedding for 2 texts
    wrong_count_response = _mock_voyage_response([[0.1] * VOYAGE_EMBEDDING_DIMENSION])
    transport = _mock_transport(response_body=wrong_count_response)

    provider = VoyageEmbeddingProvider(
        settings_with_voyage_key,
        transport=transport,
    )

    request = EmbeddingRequest(
        context=RuntimeContext(tenant_id="t1", agent_id="a1"),
        texts=["text1", "text2"],
    )

    with pytest.raises(EmbeddingError, match="unexpected number of embeddings"):
        await provider.embed(request)


@pytest.mark.asyncio
async def test_voyage_provider_retry_on_429(
    settings_with_voyage_key: Settings,
) -> None:
    """Test retry logic on HTTP 429 (rate limit)."""
    transport = AsyncMock(spec=httpx.AsyncBaseTransport)

    # First call: 429, second call: 200
    call_count = 0
    async def mock_handle(*args: Any, **kwargs: Any) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(status_code=429, content=b"Rate limited")
        return httpx.Response(
            status_code=200,
            content=_mock_voyage_response([[0.1] * VOYAGE_EMBEDDING_DIMENSION]),
            headers={"content-type": "application/json"},
        )

    transport.handle_async_request = mock_handle

    provider = VoyageEmbeddingProvider(
        settings_with_voyage_key,
        transport=transport,
    )

    request = EmbeddingRequest(
        context=RuntimeContext(tenant_id="t1", agent_id="a1"),
        texts=["test"],
    )

    result = await provider.embed(request)
    assert len(result.embeddings) == 1
    assert call_count == 2  # Retried once


@pytest.mark.asyncio
async def test_voyage_provider_retry_on_500(
    settings_with_voyage_key: Settings,
) -> None:
    """Test retry logic on HTTP 500 (server error)."""
    transport = AsyncMock(spec=httpx.AsyncBaseTransport)

    call_count = 0
    async def mock_handle(*args: Any, **kwargs: Any) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return httpx.Response(status_code=500, content=b"Server error")
        return httpx.Response(
            status_code=200,
            content=_mock_voyage_response([[0.1] * VOYAGE_EMBEDDING_DIMENSION]),
            headers={"content-type": "application/json"},
        )

    transport.handle_async_request = mock_handle

    provider = VoyageEmbeddingProvider(
        settings_with_voyage_key,
        transport=transport,
    )

    request = EmbeddingRequest(
        context=RuntimeContext(tenant_id="t1", agent_id="a1"),
        texts=["test"],
    )

    result = await provider.embed(request)
    assert call_count == 2  # Retried once


@pytest.mark.asyncio
async def test_voyage_provider_fail_on_400(
    settings_with_voyage_key: Settings,
) -> None:
    """Test that HTTP 400 (bad request) fails immediately without retry."""
    transport = _mock_transport(status_code=400, response_body=b"Bad request")

    provider = VoyageEmbeddingProvider(
        settings_with_voyage_key,
        transport=transport,
    )

    request = EmbeddingRequest(
        context=RuntimeContext(tenant_id="t1", agent_id="a1"),
        texts=["test"],
    )

    with pytest.raises(EmbeddingError, match="temporarily unavailable"):
        await provider.embed(request)


@pytest.mark.asyncio
async def test_voyage_provider_uses_document_input_type(
    settings_with_voyage_key: Settings,
) -> None:
    """Test that requests include input_type='document'."""
    transport = AsyncMock(spec=httpx.AsyncBaseTransport)

    captured_payload = None

    async def mock_handle(request: httpx.Request) -> httpx.Response:
        nonlocal captured_payload
        captured_payload = json.loads(request.content)
        return httpx.Response(
            status_code=200,
            content=_mock_voyage_response([[0.1] * VOYAGE_EMBEDDING_DIMENSION]),
            headers={"content-type": "application/json"},
        )

    transport.handle_async_request = mock_handle

    provider = VoyageEmbeddingProvider(
        settings_with_voyage_key,
        transport=transport,
    )

    request = EmbeddingRequest(
        context=RuntimeContext(tenant_id="t1", agent_id="a1"),
        texts=["test"],
    )

    await provider.embed(request)

    assert captured_payload is not None
    assert captured_payload["input_type"] == "document"
    assert captured_payload["model"] == "voyage-4-large"
    assert captured_payload["output_dimension"] == VOYAGE_EMBEDDING_DIMENSION


@pytest.mark.asyncio
async def test_voyage_provider_requires_api_key() -> None:
    """Test that provider raises error when API key is missing."""
    settings = Settings(voyage_api_key=None)

    with pytest.raises(ValueError, match="VOYAGE_API_KEY is required"):
        VoyageEmbeddingProvider(settings)


@pytest.mark.asyncio
async def test_voyage_provider_exhausts_retries(
    settings_with_voyage_key: Settings,
) -> None:
    """Test that provider fails after exhausting retries."""
    transport = _mock_transport(status_code=500, response_body=b"Server error")

    provider = VoyageEmbeddingProvider(
        settings_with_voyage_key,
        transport=transport,
    )

    request = EmbeddingRequest(
        context=RuntimeContext(tenant_id="t1", agent_id="a1"),
        texts=["test"],
    )

    with pytest.raises(EmbeddingError, match="temporarily unavailable"):
        await provider.embed(request)
