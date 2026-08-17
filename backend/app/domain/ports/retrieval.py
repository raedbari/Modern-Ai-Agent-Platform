"""RetrievalPort interface and associated data transfer objects.

The RetrievalPort is the single entry point through which the LangGraph agent
graph requests knowledge from the RAG pipeline.  It accepts a structured query
and returns ranked results with enough metadata for the agent to construct a
grounded response.

Design notes:
- ``RetrievalQuery`` and ``RetrievedChunk`` are plain dataclasses — no Pydantic,
  no SQLAlchemy, no framework coupling.
- The port does not expose embeddings or raw SQL; it exposes domain concepts.
- Multi-tenant isolation (tenant_id + agent_id) is part of the query contract,
  not an optional filter, so it can never be accidentally omitted.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from backend.app.domain.models.chunk import Chunk


# ---------------------------------------------------------------------------
# Data transfer objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RetrievalQuery:
    """All parameters required to execute a scoped similarity search.

    Attributes:
        tenant_id:         Identifier of the requesting tenant.
                           Results must never cross tenant boundaries.
        agent_id:          Identifier of the requesting agent.
                           Results must be limited to knowledge bases
                           associated with this agent.
        query:             The raw natural-language query string that will be
                           embedded and used for similarity search.
        top_k:             Maximum number of chunks to return.
                           Must be a positive integer.
        min_similarity:    Minimum cosine similarity score (0.0–1.0) for a
                           chunk to be included in the results.
                           Chunks below this threshold are excluded.
    """

    tenant_id: str
    agent_id: str
    query: str
    top_k: int
    min_similarity: float


@dataclass(frozen=True)
class RetrievedChunk:
    """A single retrieval result returned by the RAG pipeline.

    Attributes:
        chunk:             The domain ``Chunk`` entity containing the text
                           content and all isolation identifiers.
        similarity_score:  Cosine similarity between the query embedding and
                           this chunk's embedding.  Range: 0.0–1.0.
    """

    chunk: Chunk
    similarity_score: float


@dataclass(frozen=True)
class RetrievalExecution:
    """Chunks plus execution counts produced by the real retrieval pipeline."""

    chunks: tuple[RetrievedChunk, ...]
    candidate_count: int
    rerank_result_count: int | None
    rerank_applied: bool


# ---------------------------------------------------------------------------
# Port interface
# ---------------------------------------------------------------------------


class RetrievalPort(ABC):
    """Contract for retrieving relevant knowledge chunks for an agent query.

    The LangGraph agent graph calls this port to obtain grounded context
    before generating a response.  The implementation orchestrates:
    1. Embedding the query text via ``EmbeddingProvider``.
    2. Executing a scoped vector similarity search via ``ChunkRepository``.
    3. Returning ranked ``RetrievedChunk`` results.

    Isolation contract: implementations MUST enforce ``tenant_id`` and
    ``agent_id`` boundaries.  A result from a different tenant or an agent
    the query does not belong to must never appear in the output.
    """

    @abstractmethod
    async def retrieve(self, query: RetrievalQuery) -> list[RetrievedChunk]:
        """Execute a scoped similarity search and return ranked results.

        Args:
            query: A ``RetrievalQuery`` carrying all isolation parameters and
                   search configuration.

        Returns:
            A list of ``RetrievedChunk`` objects ordered by descending
            ``similarity_score``.  Returns an empty list when no chunks meet
            the minimum similarity threshold.

        Raises:
            EmbeddingError:  When the query cannot be embedded.
            RetrievalError:  When the vector search fails at the
                             infrastructure level.
        """

    async def retrieve_with_trace(
        self,
        query: RetrievalQuery,
    ) -> RetrievalExecution:
        """Retrieve with optional execution data for runtime observability.

        Existing implementations remain compatible. Implementations that own
        candidate/rerank orchestration should override this method.
        """

        chunks = tuple(await self.retrieve(query))
        return RetrievalExecution(
            chunks=chunks,
            candidate_count=len(chunks),
            rerank_result_count=None,
            rerank_applied=False,
        )
