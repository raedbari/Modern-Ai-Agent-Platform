"""Tests for EmbeddingService.

All tests are pure in-memory.  A lightweight stub implements the
``EmbeddingProvider`` interface so no real HTTP calls are made.

Stub variants:
- ``SuccessProvider``       — returns correct-dimension vectors always.
- ``FailingProvider``       — always raises ``EmbeddingError``.
- ``WrongCountProvider``    — returns fewer vectors than requested.
- ``WrongDimProvider``      — returns vectors of the wrong dimension.
- ``PartialFailProvider``   — succeeds on even batches, fails on odd ones.
"""

from __future__ import annotations

import pytest

from backend.app.domain.exceptions import EmbeddingError
from backend.app.domain.models.chunk import Chunk
from backend.app.domain.ports.embedding_provider import EmbeddingProvider
from backend.app.services.knowledge.embedding_service import (
    EmbeddedChunk,
    EmbeddingResult,
    EmbeddingService,
    FailedChunk,
)


# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

_DIMS = 4          # small dimension for fast tests
_BATCH = 3         # small batch for multi-batch tests


# ---------------------------------------------------------------------------
# Stub helpers
# ---------------------------------------------------------------------------

def _make_chunk(index: int = 0) -> Chunk:
    return Chunk(
        id=f"chunk-{index}",
        tenant_id="tenant-1",
        agent_id="agent-1",
        knowledge_base_id="kb-1",
        document_id="doc-1",
        source_name="upload",
        page_number=0,
        chunk_index=index,
        content=f"Content for chunk {index}",
        content_hash=f"hash{index}",
    )


def _make_chunks(n: int) -> list[Chunk]:
    return [_make_chunk(i) for i in range(n)]


def _make_vector(dims: int = _DIMS) -> list[float]:
    return [0.1] * dims


# ---------------------------------------------------------------------------
# EmbeddingProvider stubs
# ---------------------------------------------------------------------------

class SuccessProvider(EmbeddingProvider):
    """Returns one correct-dimension vector per input text."""

    def __init__(self, dims: int = _DIMS) -> None:
        self._dims = dims
        self.call_count = 0
        self.last_texts: list[list[str]] = []

    async def embed_text(self, text: str) -> list[float]:
        return _make_vector(self._dims)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        self.call_count += 1
        self.last_texts.append(list(texts))
        return [_make_vector(self._dims) for _ in texts]


class FailingProvider(EmbeddingProvider):
    """Always raises EmbeddingError."""

    async def embed_text(self, text: str) -> list[float]:
        raise EmbeddingError("Provider unavailable.")

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        raise EmbeddingError("Provider unavailable.")


class WrongCountProvider(EmbeddingProvider):
    """Returns one fewer vector than requested."""

    async def embed_text(self, text: str) -> list[float]:
        return _make_vector()

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        # Return one fewer than requested
        return [_make_vector() for _ in texts[:-1]]


class WrongDimProvider(EmbeddingProvider):
    """Returns vectors with the wrong dimension."""

    def __init__(self, bad_dims: int = 999) -> None:
        self._bad_dims = bad_dims

    async def embed_text(self, text: str) -> list[float]:
        return _make_vector(self._bad_dims)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [_make_vector(self._bad_dims) for _ in texts]


class PartialFailProvider(EmbeddingProvider):
    """Succeeds on even-numbered batch calls, fails on odd ones."""

    def __init__(self, dims: int = _DIMS) -> None:
        self._dims = dims
        self._call = 0

    async def embed_text(self, text: str) -> list[float]:
        return _make_vector(self._dims)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        self._call += 1
        if self._call % 2 == 0:
            raise EmbeddingError("Intermittent failure.")
        return [_make_vector(self._dims) for _ in texts]


class MixedDimProvider(EmbeddingProvider):
    """Returns correct dims for even indexes, wrong dims for odd indexes."""

    def __init__(self, good_dims: int = _DIMS, bad_dims: int = 999) -> None:
        self._good = good_dims
        self._bad = bad_dims

    async def embed_text(self, text: str) -> list[float]:
        return _make_vector(self._good)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        result = []
        for i, _ in enumerate(texts):
            dims = self._good if i % 2 == 0 else self._bad
            result.append(_make_vector(dims))
        return result


# ---------------------------------------------------------------------------
# EmbeddingService construction
# ---------------------------------------------------------------------------


class TestEmbeddingServiceConstruction:
    def test_valid_construction(self) -> None:
        svc = EmbeddingService(
            provider=SuccessProvider(),
            batch_size=10,
            embedding_dimensions=_DIMS,
        )
        assert svc._batch_size == 10
        assert svc._embedding_dimensions == _DIMS

    def test_zero_batch_size_raises(self) -> None:
        with pytest.raises(ValueError, match="batch_size"):
            EmbeddingService(
                provider=SuccessProvider(),
                batch_size=0,
                embedding_dimensions=_DIMS,
            )

    def test_negative_batch_size_raises(self) -> None:
        with pytest.raises(ValueError, match="batch_size"):
            EmbeddingService(
                provider=SuccessProvider(),
                batch_size=-1,
                embedding_dimensions=_DIMS,
            )

    def test_zero_embedding_dimensions_raises(self) -> None:
        with pytest.raises(ValueError, match="embedding_dimensions"):
            EmbeddingService(
                provider=SuccessProvider(),
                batch_size=10,
                embedding_dimensions=0,
            )

    def test_negative_embedding_dimensions_raises(self) -> None:
        with pytest.raises(ValueError, match="embedding_dimensions"):
            EmbeddingService(
                provider=SuccessProvider(),
                batch_size=10,
                embedding_dimensions=-1,
            )


# ---------------------------------------------------------------------------
# EmbeddingResult properties
# ---------------------------------------------------------------------------


class TestEmbeddingResult:
    def _chunk(self) -> Chunk:
        return _make_chunk(0)

    def test_total_counts_both(self) -> None:
        r = EmbeddingResult()
        chunk = self._chunk()
        r.embedded.append(EmbeddedChunk(chunk=chunk, embedding=[0.1]))
        r.failed_chunks.append(FailedChunk(chunk=chunk, reason="fail"))
        assert r.total == 2

    def test_success_count(self) -> None:
        r = EmbeddingResult()
        r.embedded.append(EmbeddedChunk(chunk=self._chunk(), embedding=[0.1]))
        assert r.success_count == 1

    def test_failure_count(self) -> None:
        r = EmbeddingResult()
        r.failed_chunks.append(FailedChunk(chunk=self._chunk(), reason="x"))
        assert r.failure_count == 1

    def test_has_failures_false_when_empty(self) -> None:
        assert not EmbeddingResult().has_failures

    def test_has_failures_true_with_failures(self) -> None:
        r = EmbeddingResult()
        r.failed_chunks.append(FailedChunk(chunk=self._chunk(), reason="x"))
        assert r.has_failures

    def test_fully_successful_with_no_failures(self) -> None:
        r = EmbeddingResult()
        r.embedded.append(EmbeddedChunk(chunk=self._chunk(), embedding=[0.1]))
        assert r.fully_successful

    def test_not_fully_successful_with_failures(self) -> None:
        r = EmbeddingResult()
        r.embedded.append(EmbeddedChunk(chunk=self._chunk(), embedding=[0.1]))
        r.failed_chunks.append(FailedChunk(chunk=self._chunk(), reason="x"))
        assert not r.fully_successful


# ---------------------------------------------------------------------------
# embed_chunks — successful cases
# ---------------------------------------------------------------------------


class TestEmbedChunksSuccess:
    @pytest.mark.asyncio
    async def test_empty_input_returns_empty_result(self) -> None:
        svc = EmbeddingService(
            provider=SuccessProvider(),
            batch_size=_BATCH,
            embedding_dimensions=_DIMS,
        )
        result = await svc.embed_chunks([])
        assert result.total == 0
        assert not result.has_failures

    @pytest.mark.asyncio
    async def test_empty_input_does_not_call_provider(self) -> None:
        provider = SuccessProvider()
        svc = EmbeddingService(
            provider=provider, batch_size=_BATCH, embedding_dimensions=_DIMS
        )
        await svc.embed_chunks([])
        assert provider.call_count == 0

    @pytest.mark.asyncio
    async def test_single_chunk_embedded(self) -> None:
        svc = EmbeddingService(
            provider=SuccessProvider(),
            batch_size=_BATCH,
            embedding_dimensions=_DIMS,
        )
        result = await svc.embed_chunks([_make_chunk()])
        assert result.success_count == 1
        assert result.failure_count == 0

    @pytest.mark.asyncio
    async def test_result_contains_embedded_chunk(self) -> None:
        svc = EmbeddingService(
            provider=SuccessProvider(),
            batch_size=_BATCH,
            embedding_dimensions=_DIMS,
        )
        chunk = _make_chunk(0)
        result = await svc.embed_chunks([chunk])
        assert result.embedded[0].chunk is chunk

    @pytest.mark.asyncio
    async def test_embedding_vector_attached(self) -> None:
        svc = EmbeddingService(
            provider=SuccessProvider(),
            batch_size=_BATCH,
            embedding_dimensions=_DIMS,
        )
        result = await svc.embed_chunks([_make_chunk()])
        assert len(result.embedded[0].embedding) == _DIMS

    @pytest.mark.asyncio
    async def test_multiple_chunks_single_batch(self) -> None:
        chunks = _make_chunks(3)
        svc = EmbeddingService(
            provider=SuccessProvider(),
            batch_size=10,
            embedding_dimensions=_DIMS,
        )
        result = await svc.embed_chunks(chunks)
        assert result.success_count == 3
        assert result.failure_count == 0

    @pytest.mark.asyncio
    async def test_multiple_batches(self) -> None:
        """6 chunks with batch_size=3 → 2 provider calls."""
        provider = SuccessProvider()
        svc = EmbeddingService(
            provider=provider, batch_size=3, embedding_dimensions=_DIMS
        )
        result = await svc.embed_chunks(_make_chunks(6))
        assert result.success_count == 6
        assert provider.call_count == 2

    @pytest.mark.asyncio
    async def test_batch_boundary_chunks_embedded(self) -> None:
        """7 chunks with batch_size=3 → batches of [3, 3, 1]."""
        provider = SuccessProvider()
        svc = EmbeddingService(
            provider=provider, batch_size=3, embedding_dimensions=_DIMS
        )
        result = await svc.embed_chunks(_make_chunks(7))
        assert result.success_count == 7
        assert provider.call_count == 3

    @pytest.mark.asyncio
    async def test_input_order_preserved(self) -> None:
        chunks = _make_chunks(5)
        svc = EmbeddingService(
            provider=SuccessProvider(),
            batch_size=10,
            embedding_dimensions=_DIMS,
        )
        result = await svc.embed_chunks(chunks)
        for i, embedded in enumerate(result.embedded):
            assert embedded.chunk.chunk_index == i

    @pytest.mark.asyncio
    async def test_input_chunks_not_mutated(self) -> None:
        chunk = _make_chunk(0)
        original_content = chunk.content
        svc = EmbeddingService(
            provider=SuccessProvider(),
            batch_size=_BATCH,
            embedding_dimensions=_DIMS,
        )
        await svc.embed_chunks([chunk])
        assert chunk.content == original_content

    @pytest.mark.asyncio
    async def test_idempotent_execution(self) -> None:
        """Two calls with the same input return results with same structure."""
        chunks = _make_chunks(4)
        svc = EmbeddingService(
            provider=SuccessProvider(),
            batch_size=_BATCH,
            embedding_dimensions=_DIMS,
        )
        r1 = await svc.embed_chunks(chunks)
        r2 = await svc.embed_chunks(chunks)
        assert r1.success_count == r2.success_count
        assert r1.failure_count == r2.failure_count
        for e1, e2 in zip(r1.embedded, r2.embedded):
            assert e1.chunk is e2.chunk


# ---------------------------------------------------------------------------
# embed_chunks — provider failures
# ---------------------------------------------------------------------------


class TestEmbedChunksFailures:
    @pytest.mark.asyncio
    async def test_provider_exception_captured(self) -> None:
        svc = EmbeddingService(
            provider=FailingProvider(),
            batch_size=_BATCH,
            embedding_dimensions=_DIMS,
        )
        chunks = _make_chunks(3)
        result = await svc.embed_chunks(chunks)
        assert result.failure_count == 3
        assert result.success_count == 0

    @pytest.mark.asyncio
    async def test_provider_exception_does_not_raise(self) -> None:
        svc = EmbeddingService(
            provider=FailingProvider(),
            batch_size=_BATCH,
            embedding_dimensions=_DIMS,
        )
        # Must not raise
        result = await svc.embed_chunks(_make_chunks(2))
        assert result is not None

    @pytest.mark.asyncio
    async def test_failed_chunk_has_reason(self) -> None:
        svc = EmbeddingService(
            provider=FailingProvider(),
            batch_size=_BATCH,
            embedding_dimensions=_DIMS,
        )
        result = await svc.embed_chunks([_make_chunk()])
        assert result.failed_chunks[0].reason
        assert len(result.failed_chunks[0].reason) > 0

    @pytest.mark.asyncio
    async def test_failed_chunk_preserves_original_chunk(self) -> None:
        chunk = _make_chunk(0)
        svc = EmbeddingService(
            provider=FailingProvider(),
            batch_size=_BATCH,
            embedding_dimensions=_DIMS,
        )
        result = await svc.embed_chunks([chunk])
        assert result.failed_chunks[0].chunk is chunk

    @pytest.mark.asyncio
    async def test_partial_failure_preserves_successful_batches(self) -> None:
        """First batch succeeds (call 1 = odd), second fails (call 2 = even)."""
        svc = EmbeddingService(
            provider=PartialFailProvider(),
            batch_size=3,
            embedding_dimensions=_DIMS,
        )
        # 6 chunks → 2 batches of 3
        result = await svc.embed_chunks(_make_chunks(6))
        assert result.success_count == 3
        assert result.failure_count == 3
        assert result.has_failures

    @pytest.mark.asyncio
    async def test_wrong_count_fails_entire_batch(self) -> None:
        svc = EmbeddingService(
            provider=WrongCountProvider(),
            batch_size=_BATCH,
            embedding_dimensions=_DIMS,
        )
        result = await svc.embed_chunks(_make_chunks(3))
        assert result.failure_count == 3
        assert result.success_count == 0

    @pytest.mark.asyncio
    async def test_wrong_count_failure_has_descriptive_reason(self) -> None:
        svc = EmbeddingService(
            provider=WrongCountProvider(),
            batch_size=_BATCH,
            embedding_dimensions=_DIMS,
        )
        result = await svc.embed_chunks([_make_chunk()])
        # WrongCountProvider returns 0 vectors for 1 input
        assert result.failed_chunks[0].reason

    @pytest.mark.asyncio
    async def test_wrong_dimension_fails_affected_chunks(self) -> None:
        svc = EmbeddingService(
            provider=WrongDimProvider(bad_dims=999),
            batch_size=_BATCH,
            embedding_dimensions=_DIMS,
        )
        result = await svc.embed_chunks(_make_chunks(3))
        assert result.failure_count == 3
        assert result.success_count == 0

    @pytest.mark.asyncio
    async def test_wrong_dimension_reason_mentions_dimensions(self) -> None:
        svc = EmbeddingService(
            provider=WrongDimProvider(bad_dims=999),
            batch_size=_BATCH,
            embedding_dimensions=_DIMS,
        )
        result = await svc.embed_chunks([_make_chunk()])
        reason = result.failed_chunks[0].reason
        assert "999" in reason or "dimension" in reason.lower()

    @pytest.mark.asyncio
    async def test_mixed_dimension_within_batch(self) -> None:
        """Even-indexed chunks in the batch get right dims, odd ones get wrong."""
        svc = EmbeddingService(
            provider=MixedDimProvider(good_dims=_DIMS, bad_dims=999),
            batch_size=6,
            embedding_dimensions=_DIMS,
        )
        result = await svc.embed_chunks(_make_chunks(6))
        # Indexes 0, 2, 4 → good; 1, 3, 5 → bad
        assert result.success_count == 3
        assert result.failure_count == 3
