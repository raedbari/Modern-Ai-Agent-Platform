"""Knowledge retrieval service for the RAG Pipeline.

Implements ``RetrievalPort`` — the single entry point through which the
LangGraph agent graph (or any other caller) requests grounded knowledge
for a given query.

Retrieval flow
--------------
1. **Validate** — reject malformed queries before any I/O.
2. **Resolve KBs** — load all KnowledgeBases assigned to the agent via
   ``KnowledgeBaseRepository.list_for_agent()``.  Filter to ACTIVE only.
3. **Guard** — raise ``RetrievalValidationError`` when no active KB exists.
4. **Embed** — convert the query string to a dense vector using
   ``EmbeddingProvider.embed_text()``.  Raise ``EmbeddingError`` on failure.
5. **Search per KB** — call ``ChunkRepository.semantic_search()`` once per
   active KB.  Each call is already scoped by ``tenant_id``, ``agent_id``,
   and ``knowledge_base_id``.  Raise ``RetrievalError`` on repository failure.
6. **Merge & rank** — concatenate all per-KB results, sort globally by
   descending similarity score.
7. **Truncate** — keep at most ``top_k`` results.
8. **Return** — convert ``(Chunk, score)`` pairs into ``RetrievedChunk`` DTOs.

Tenant isolation
----------------
``tenant_id`` from ``RetrievalQuery`` is passed explicitly to every
repository method.  The repository contract requires it and must filter on
it before applying any vector similarity ranking.  A chunk belonging to a
different tenant can never appear because:
- ``list_for_agent`` accepts ``tenant_id`` — only the tenant's own KBs are
  returned.
- ``semantic_search`` accepts ``tenant_id`` — only the tenant's chunks are
  searched.

KB filtering
------------
Only KnowledgeBases with ``status == ACTIVE`` are searched.  An INACTIVE KB
might contain stale data or be under maintenance; its chunks are silently
excluded rather than raising an error.

Design constraints
------------------
- No SQLAlchemy, no FastAPI, no LangGraph.
- No direct HTTP calls — all external calls go through port interfaces.
- No mutation of input objects.
- The class is fully async to match the port contract.
"""

from __future__ import annotations

from backend.app.domain.exceptions import (
    EmbeddingError,
    RetrievalError,
    RetrievalValidationError,
)
from backend.app.domain.models.enums import KnowledgeBaseStatus
from backend.app.domain.ports.embedding_provider import EmbeddingProvider
from backend.app.domain.ports.repositories import (
    ChunkRepository,
    KnowledgeBaseRepository,
)
from backend.app.domain.ports.retrieval import (
    RetrievalPort,
    RetrievalQuery,
    RetrievedChunk,
)


class RetrievalService(RetrievalPort):
    """Concrete implementation of ``RetrievalPort`` for the RAG pipeline.

    Depends only on domain ports and domain exceptions.  Can be constructed
    with any compliant implementations of the three injected interfaces.

    Args:
        embedding_provider:    Provides ``embed_text()`` for query vectorisation.
        chunk_repository:      Provides ``semantic_search()`` against the vector
                               store.
        kb_repository:         Provides ``list_for_agent()`` to resolve which
                               knowledge bases are in scope for the agent.
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        chunk_repository: ChunkRepository,
        kb_repository: KnowledgeBaseRepository,
    ) -> None:
        self._embedding_provider = embedding_provider
        self._chunk_repository = chunk_repository
        self._kb_repository = kb_repository

    # ------------------------------------------------------------------
    # RetrievalPort implementation
    # ------------------------------------------------------------------

    async def retrieve(self, query: RetrievalQuery) -> list[RetrievedChunk]:
        """Execute a scoped similarity search and return ranked results.

        Args:
            query: A fully constructed ``RetrievalQuery`` carrying tenant,
                   agent, search text, top_k, and similarity threshold.

        Returns:
            A list of ``RetrievedChunk`` objects ordered by descending
            ``similarity_score``, containing at most ``query.top_k`` items.
            Returns an empty list when no chunk meets ``query.min_similarity``.

        Raises:
            RetrievalValidationError: When the query is malformed or when the
                agent has no active knowledge bases.
            EmbeddingError:           When the query text cannot be embedded.
            RetrievalError:           When a repository search call fails.
        """
        self._validate_query(query)

        active_kb_ids = await self._resolve_active_kb_ids(query)

        query_embedding = await self._embed_query(query.query)

        raw_results = await self._search_all_kbs(
            query_embedding=query_embedding,
            query=query,
            kb_ids=active_kb_ids,
        )

        ranked = sorted(raw_results, key=lambda pair: pair[1], reverse=True)
        top = ranked[: query.top_k]

        return [RetrievedChunk(chunk=chunk, similarity_score=score) for chunk, score in top]

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_query(query: RetrievalQuery) -> None:
        """Raise ``RetrievalValidationError`` for any malformed field.

        Validation is intentionally strict and runs before any I/O so
        misconfigured callers fail fast without consuming provider quota.
        """
        if not query.query or not query.query.strip():
            raise RetrievalValidationError(
                "RetrievalQuery.query must not be empty."
            )
        if not query.tenant_id or not query.tenant_id.strip():
            raise RetrievalValidationError(
                "RetrievalQuery.tenant_id must not be empty."
            )
        if not query.agent_id or not query.agent_id.strip():
            raise RetrievalValidationError(
                "RetrievalQuery.agent_id must not be empty."
            )
        if query.top_k <= 0:
            raise RetrievalValidationError(
                f"RetrievalQuery.top_k must be a positive integer, "
                f"got {query.top_k}."
            )
        if not (0.0 <= query.min_similarity <= 1.0):
            raise RetrievalValidationError(
                f"RetrievalQuery.min_similarity must be in [0.0, 1.0], "
                f"got {query.min_similarity}."
            )

    async def _resolve_active_kb_ids(self, query: RetrievalQuery) -> list[str]:
        """Return IDs of ACTIVE KnowledgeBases for the agent in this tenant.

        Raises:
            RetrievalValidationError: When no active KBs exist for the agent.
        """
        all_kbs = await self._kb_repository.list_for_agent(
            agent_id=query.agent_id,
            tenant_id=query.tenant_id,
        )
        active_ids = [
            kb.id
            for kb in all_kbs
            if kb.status == KnowledgeBaseStatus.ACTIVE
        ]
        if not active_ids:
            raise RetrievalValidationError(
                f"Agent '{query.agent_id}' has no active knowledge bases "
                "available for retrieval."
            )
        return active_ids

    async def _embed_query(self, text: str) -> list[float]:
        """Embed the query string.  Propagates ``EmbeddingError`` unchanged."""
        # EmbeddingError is a domain exception and must reach the caller
        # per the RetrievalPort contract.
        return await self._embedding_provider.embed_text(text)

    async def _search_all_kbs(
        self,
        query_embedding: list[float],
        query: RetrievalQuery,
        kb_ids: list[str],
    ) -> list[tuple]:
        """Fan out ``semantic_search`` across every active KB and collect results.

        Each KB is searched independently.  Results from all KBs are combined
        into a single flat list so the caller can rank them globally.

        Raises:
            RetrievalError: When any repository call fails.
        """
        combined: list[tuple] = []
        for kb_id in kb_ids:
            try:
                pairs = await self._chunk_repository.semantic_search(
                    query_embedding=query_embedding,
                    tenant_id=query.tenant_id,
                    agent_id=query.agent_id,
                    knowledge_base_id=kb_id,
                    top_k=query.top_k,
                    min_similarity=query.min_similarity,
                )
            except RetrievalError:
                raise
            except Exception as exc:
                raise RetrievalError(
                    "An error occurred while searching the knowledge base."
                ) from exc
            combined.extend(pairs)
        return combined
