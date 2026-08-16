"""Embedding service for the Knowledge RAG Pipeline.

Accepts a list of ``Chunk`` domain objects, batches their text content,
calls the platform ``EmbeddingProvider.embed()`` contract, validates the
returned vectors, and returns a structured ``EmbeddingResult`` that
separates successfully embedded chunks from failed ones.

Design
------
The service is intentionally narrow:
- Batch size and expected dimensions are injected at construction time.
- It calls only the shared ``EmbeddingProvider.embed()`` port.  It never
  touches a repository and never persists anything.
- Input ``Chunk`` objects are **never mutated**.  Embeddings are returned
  alongside their source chunk in ``EmbeddedChunk`` value objects.

Batch strategy
--------------
Chunks are grouped into consecutive batches of at most
``embedding_batch_size``.  Each batch is a single ``embed()`` call.
If a batch call raises ``EmbeddingError``, every chunk in that batch is
recorded as a failure with the safe error message.  Chunks from other
batches are not affected — the loop continues.

Validation
----------
After each successful ``embed()`` call:

1. **Count check**: ``len(vectors) == len(batch)`` — the provider must
   return exactly one vector per input text.
2. **Dimension check**: ``len(vector) == embedding_dimensions`` for every
   vector — the provider must return vectors of the expected length.

A validation failure for a batch is treated identically to a provider
exception: all chunks in that batch are moved to ``failed_chunks``.

Idempotency
-----------
The service has no side effects.  Calling ``embed_chunks()`` twice with
the same input produces the same output (assuming the provider is
deterministic).  There is no internal state between calls.

Partial failure
---------------
``EmbeddingResult.failed_chunks`` contains every chunk that could not be
embedded along with a ``reason`` string.  Successfully embedded chunks in
other batches are **always preserved** in ``EmbeddingResult.embedded``.
The caller decides whether to retry failed chunks or mark the parent
document as partially failed.

Ordering
--------
``EmbeddingResult.embedded`` preserves the input order of successfully
embedded chunks.  Ordering within a failed batch is also preserved in
``EmbeddingResult.failed_chunks``.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.app.ai.contracts import EmbeddingRequest, RuntimeContext
from backend.app.ai.ports import EmbeddingProvider
from backend.app.domain.exceptions import EmbeddingError
from backend.app.domain.models.chunk import Chunk


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EmbeddedChunk:
    """A ``Chunk`` paired with its embedding vector.

    The ``Chunk`` is the unmodified input; the embedding is the dense
    vector returned by the provider for ``chunk.content``.

    Attributes:
        chunk:     The original domain ``Chunk``.
        embedding: Dense float vector.  Length equals
                   the configured embedding dimension.
    """

    chunk: Chunk
    embedding: list[float]


@dataclass
class FailedChunk:
    """A ``Chunk`` that could not be embedded, with a safe failure reason.

    Attributes:
        chunk:  The original domain ``Chunk``.
        reason: Human-readable explanation of the failure.  Must never
                contain raw exception traces or infrastructure details.
    """

    chunk: Chunk
    reason: str


@dataclass
class EmbeddingResult:
    """Structured outcome of an ``EmbeddingService.embed_chunks()`` call.

    Attributes:
        embedded:      Successfully embedded chunks, in input order.
        failed_chunks: Chunks that could not be embedded, with reasons.
    """

    embedded: list[EmbeddedChunk] = field(default_factory=list)
    failed_chunks: list[FailedChunk] = field(default_factory=list)

    @property
    def total(self) -> int:
        """Total number of chunks processed (success + failure)."""
        return len(self.embedded) + len(self.failed_chunks)

    @property
    def success_count(self) -> int:
        """Number of successfully embedded chunks."""
        return len(self.embedded)

    @property
    def failure_count(self) -> int:
        """Number of chunks that failed to embed."""
        return len(self.failed_chunks)

    @property
    def has_failures(self) -> bool:
        """``True`` when at least one chunk could not be embedded."""
        return bool(self.failed_chunks)

    @property
    def fully_successful(self) -> bool:
        """``True`` when every chunk was embedded successfully."""
        return not self.failed_chunks


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class EmbeddingService:
    """Generates embeddings for a list of ``Chunk`` objects.

    Responsibilities:
    - Slice the input list into batches of ``embedding_batch_size``.
    - Call ``EmbeddingProvider.embed()`` for each batch.
    - Validate the provider response (count and dimension checks).
    - Accumulate results into an ``EmbeddingResult``.
    - Never mutate input ``Chunk`` objects.
    - Never propagate provider exceptions to the caller — all failures
      are captured in ``EmbeddingResult.failed_chunks``.

    This class has no I/O dependencies beyond ``EmbeddingProvider``.
    It does not call any repository, does not persist data, and has no
    FastAPI or SQLAlchemy imports.
    """

    def __init__(
        self,
        provider: EmbeddingProvider,
        batch_size: int,
        embedding_dimensions: int,
    ) -> None:
        """Initialise the service.

        Args:
            provider:             An ``EmbeddingProvider`` implementation.
            batch_size:           Maximum chunks per ``embed()`` call.
                                  Must be a positive integer.
            embedding_dimensions: Expected vector length for every embedding.
                                  Must be a positive integer.

        Raises:
            ValueError: When ``batch_size`` or ``embedding_dimensions`` is
                        not a positive integer.
        """
        if batch_size <= 0:
            raise ValueError(
                f"batch_size must be a positive integer, got {batch_size}."
            )
        if embedding_dimensions <= 0:
            raise ValueError(
                f"embedding_dimensions must be a positive integer, "
                f"got {embedding_dimensions}."
            )
        self._provider = provider
        self._batch_size = batch_size
        self._embedding_dimensions = embedding_dimensions

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def embed_chunks(self, chunks: list[Chunk]) -> EmbeddingResult:
        """Embed a list of chunks and return a structured result.

        Processing order
        ~~~~~~~~~~~~~~~~
        Chunks are processed in the exact order they are provided.  Input
        order is preserved in ``EmbeddingResult.embedded`` for all
        successfully embedded chunks.

        Batch failures
        ~~~~~~~~~~~~~~
        A provider exception or a validation failure for one batch does not
        abort processing of subsequent batches.  All successfully embedded
        chunks from other batches are preserved in the result.

        Args:
            chunks: A list of ``Chunk`` domain objects to embed.  May be
                    empty — an empty list returns an empty ``EmbeddingResult``
                    without calling the provider.

        Returns:
            An ``EmbeddingResult`` containing embedded chunks and any
            failures with their reasons.

        Raises:
            This method does **not** raise ``EmbeddingError``.  All provider
            failures are captured in ``EmbeddingResult.failed_chunks``.
        """
        result = EmbeddingResult()

        if not chunks:
            return result

        contexts = {(chunk.tenant_id, chunk.agent_id) for chunk in chunks}
        if len(contexts) != 1:
            raise ValueError(
                "All chunks in one embedding operation must belong to the "
                "same tenant and agent."
            )

        for batch_start in range(0, len(chunks), self._batch_size):
            batch = chunks[batch_start : batch_start + self._batch_size]
            await self._process_batch(batch, result)

        return result

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _process_batch(
        self,
        batch: list[Chunk],
        result: EmbeddingResult,
    ) -> None:
        """Embed one batch of chunks and update *result* in place.

        On any failure (provider exception, count mismatch, dimension
        mismatch) every chunk in the batch is added to
        ``result.failed_chunks`` with a safe message.  No exception is
        re-raised.

        Args:
            batch:  A non-empty sub-list of chunks to embed.
            result: The accumulator updated in place.
        """
        texts = [chunk.content for chunk in batch]
        first = batch[0]
        request = EmbeddingRequest(
            context=RuntimeContext(
                tenant_id=first.tenant_id,
                agent_id=first.agent_id,
            ),
            texts=texts,
            input_type="document",
        )

        try:
            provider_result = await self._provider.embed(request)
            vectors = provider_result.embeddings
        except EmbeddingError:
            reason = "Embedding provider failed to process the batch."
            for chunk in batch:
                result.failed_chunks.append(FailedChunk(chunk=chunk, reason=reason))
            return
        except Exception:  # pragma: no cover – catch-all safety net
            reason = "An unexpected error occurred during embedding."
            for chunk in batch:
                result.failed_chunks.append(FailedChunk(chunk=chunk, reason=reason))
            return

        if provider_result.dimension != self._embedding_dimensions:
            reason = (
                f"Embedding provider declared {provider_result.dimension} "
                f"dimension(s); expected {self._embedding_dimensions}."
            )
            for chunk in batch:
                result.failed_chunks.append(FailedChunk(chunk=chunk, reason=reason))
            return

        # Validate response count.
        if len(vectors) != len(batch):
            reason = (
                f"Embedding provider returned {len(vectors)} vector(s) "
                f"for {len(batch)} chunk(s). Expected equal counts."
            )
            for chunk in batch:
                result.failed_chunks.append(FailedChunk(chunk=chunk, reason=reason))
            return

        # Validate each vector's dimension and pair with its chunk.
        for chunk, vector in zip(batch, vectors):
            if len(vector) != self._embedding_dimensions:
                reason = (
                    f"Embedding vector has {len(vector)} dimension(s); "
                    f"expected {self._embedding_dimensions}."
                )
                result.failed_chunks.append(FailedChunk(chunk=chunk, reason=reason))
            else:
                result.embedded.append(EmbeddedChunk(chunk=chunk, embedding=vector))
