"""Knowledge retrieval service with Voyage reranking for the RAG pipeline.

Implements ``RetrievalPort`` — the single entry point through which the
LangGraph agent graph (or any other caller) requests grounded knowledge
for a given query.

Retrieval flow
--------------
1. **Validate** — reject malformed queries before any I/O.
2. **Resolve KBs** — load all KnowledgeBases assigned to the agent via
   ``KnowledgeBaseRepository.list_for_agent()``.  Filter to ACTIVE only.
3. **Guard** — raise ``RetrievalValidationError`` when no active KB exists.
4. **Embed** — convert the tenant-scoped query to a dense 1024-dimensional
   vector using ``EmbeddingProvider.embed()`` (Voyage voyage-4-large).
   Raise ``EmbeddingError`` on failure.
5. **Search per KB** — call ``ChunkRepository.semantic_search()`` once per
   active KB, using ``retrieval_candidate_count`` as top_k.  Each call is
   already scoped by ``tenant_id``, ``agent_id``, and ``knowledge_base_id``.
   Raise ``RetrievalError`` on repository failure.
6. **Merge tenant-filtered candidates** — concatenate all per-KB results.
   At this point every chunk has passed tenant/agent/KB filtering.
7. **Rerank** — pass the merged candidates (query + chunk texts only) to
   ``VoyageRerankProvider.rerank()``.  If reranking fails, fall back to the
   already-filtered pgvector ranking (safe fallback).
8. **Select final context** — keep the top ``top_k`` reranked chunks.
9. **Return** — convert ``(Chunk, score)`` pairs into ``RetrievedChunk`` DTOs.

Security / tenant isolation
---------------------------
``tenant_id`` from ``RetrievalQuery`` is passed explicitly to every
repository method.  The repository contract requires it and must filter on
it before applying any vector similarity ranking.

The reranker never receives tenant IDs, credentials, or internal metadata.
Only the query string and candidate chunk text are transmitted to Voyage.

Wrong-tenant chunks can never reach Voyage rerank because:
- ``list_for_agent`` accepts ``tenant_id`` — only the tenant's own KBs are
  returned.
- ``semantic_search`` accepts ``tenant_id`` — only the tenant's chunks are
  searched.
- Reranking runs AFTER the tenant-filtered candidate list is assembled.

Reranker failure
----------------
When Voyage rerank is unavailable the service degrades gracefully:
- Uses the already tenant-filtered pgvector similarity ranking.
- Selects the first ``top_k`` candidates (best pgvector score).
- Never bypasses tenant/agent/KB isolation.

Configuration
-------------
Two integers control the two-stage retrieval:
- ``retrieval_candidate_count`` (default 20): how many candidates are
  fetched from pgvector per KB before reranking.
- ``retrieval_final_count`` (default 5): how many chunks are returned to
  the caller after reranking (equivalent to ``top_k``).

These defaults match the task specification but are injected at
construction so callers and tests can override them without touching this
file.
"""

from __future__ import annotations

import logging

from backend.app.ai.contracts import EmbeddingRequest, RuntimeContext
from backend.app.ai.ports import EmbeddingProvider
from backend.app.ai.rerank import RerankProvider, RerankRequest
from backend.app.domain.exceptions import (
    EmbeddingError,
    RetrievalError,
    RetrievalValidationError,
)
from backend.app.domain.models.chunk import Chunk
from backend.app.domain.models.enums import KnowledgeBaseStatus
from backend.app.domain.ports.repositories import (
    ChunkRepository,
    KnowledgeBaseRepository,
)
from backend.app.domain.ports.retrieval import (
    RetrievalPort,
    RetrievalQuery,
    RetrievedChunk,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Production defaults — must match the task specification.
# ---------------------------------------------------------------------------

DEFAULT_CANDIDATE_COUNT = 20   # pgvector first-stage retrieval count
DEFAULT_FINAL_COUNT = 5        # Voyage reranked final context count


class RetrievalService(RetrievalPort):
    """Concrete implementation of ``RetrievalPort`` using Voyage AI reranking.

    Two-stage retrieval:
    1. pgvector semantic search retrieves ``retrieval_candidate_count``
       tenant-filtered candidates per knowledge base.
    2. Voyage rerank-2.5 reorders the merged candidates and selects the
       final ``retrieval_final_count`` chunks for DeepSeek.

    If the Voyage reranker fails, the service falls back to the existing
    pgvector ranking, selecting the first ``retrieval_final_count`` chunks
    from the already tenant-filtered candidate list.

    Args:
        embedding_provider:       Provides ``embed()`` for query vectorisation
                                  (Voyage voyage-4-large).
        chunk_repository:         Provides ``semantic_search()`` against the
                                  vector store.
        kb_repository:            Provides ``list_for_agent()`` to resolve which
                                  knowledge bases are in scope for the agent.
        rerank_provider:          Provides ``rerank()`` for Voyage reranking.
                                  When ``None``, the service skips reranking
                                  and returns pgvector-ranked results.
        retrieval_candidate_count: Number of candidates fetched from pgvector
                                  per knowledge base.  Default: 20.
        retrieval_final_count:    Number of chunks returned after reranking.
                                  Default: 5.
    """

    def __init__(
        self,
        embedding_provider: EmbeddingProvider,
        chunk_repository: ChunkRepository,
        kb_repository: KnowledgeBaseRepository,
        *,
        rerank_provider: RerankProvider | None = None,
        retrieval_candidate_count: int = DEFAULT_CANDIDATE_COUNT,
        retrieval_final_count: int = DEFAULT_FINAL_COUNT,
    ) -> None:
        if retrieval_candidate_count <= 0:
            raise ValueError("retrieval_candidate_count must be positive.")
        if retrieval_final_count <= 0:
            raise ValueError("retrieval_final_count must be positive.")
        self._embedding_provider = embedding_provider
        self._chunk_repository = chunk_repository
        self._kb_repository = kb_repository
        self._rerank_provider = rerank_provider
        self._retrieval_candidate_count = retrieval_candidate_count
        self._retrieval_final_count = retrieval_final_count

    # ------------------------------------------------------------------
    # RetrievalPort implementation
    # ------------------------------------------------------------------

    async def retrieve(self, query: RetrievalQuery) -> list[RetrievedChunk]:
        """Execute a two-stage retrieval (pgvector + Voyage rerank).

        Args:
            query: A fully constructed ``RetrievalQuery`` carrying tenant,
                   agent, search text, top_k, and similarity threshold.

        Returns:
            A list of ``RetrievedChunk`` objects ordered by relevance,
            containing at most ``query.top_k`` items (or
            ``retrieval_final_count`` when reranking is active).
            Returns an empty list when no chunk meets the similarity
            threshold or all knowledge bases are empty.

        Raises:
            RetrievalValidationError: When the query is malformed or when the
                agent has no active knowledge bases.
            EmbeddingError:           When the query text cannot be embedded.
            RetrievalError:           When a repository search call fails.
        """
        self._validate_query(query)

        active_kb_ids = await self._resolve_active_kb_ids(query)

        query_embedding = await self._embed_query(query)

        # First-stage: tenant-filtered pgvector candidates.
        # The candidate_count overrides query.top_k for the vector search
        # because we need more candidates to feed into the reranker.
        candidates = await self._search_all_kbs(
            query_embedding=query_embedding,
            query=query,
            kb_ids=active_kb_ids,
            candidate_count=self._retrieval_candidate_count,
        )

        if not candidates:
            return []

        # Second-stage: Voyage reranking (optional — falls back safely).
        # Use the configured retrieval_final_count when set; otherwise
        # honour the per-query top_k as a ceiling.
        final_count = min(query.top_k, self._retrieval_final_count)
        ranked = await self._rerank_candidates(
            query=query,
            candidates=candidates,
            final_count=final_count,
        )

        return [
            RetrievedChunk(chunk=chunk, similarity_score=score)
            for chunk, score in ranked
        ]

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

    async def _embed_query(self, query: RetrievalQuery) -> list[float]:
        """Embed one tenant-scoped query through the Voyage AI provider port."""
        request = EmbeddingRequest(
            context=RuntimeContext(
                tenant_id=query.tenant_id,
                agent_id=query.agent_id,
            ),
            texts=[query.query],
            input_type="query",
        )
        try:
            result = await self._embedding_provider.embed(request)
        except EmbeddingError:
            raise
        except Exception as exc:
            raise EmbeddingError(
                "The query could not be embedded."
            ) from exc

        if len(result.embeddings) != 1:
            raise EmbeddingError(
                "The embedding provider returned an invalid query result."
            )
        vector = result.embeddings[0]
        if len(vector) != result.dimension:
            raise EmbeddingError(
                "The embedding provider returned an invalid query dimension."
            )
        return vector

    async def _search_all_kbs(
        self,
        query_embedding: list[float],
        query: RetrievalQuery,
        kb_ids: list[str],
        candidate_count: int,
    ) -> list[tuple[Chunk, float]]:
        """Fan out ``semantic_search`` across every active KB and collect results.

        Each KB is searched independently.  Results from all KBs are combined
        into a single flat list.  All results are already tenant/agent/KB
        filtered — they are safe to pass to the Voyage reranker.

        Args:
            query_embedding:  The embedded query vector.
            query:            The original ``RetrievalQuery`` for scoping.
            kb_ids:           Active knowledge base IDs to search.
            candidate_count:  Number of candidates to retrieve per KB.

        Raises:
            RetrievalError: When any repository call fails.
        """
        # With an external reranker configured, the first-stage vector
        # search is a recall stage: collect the best candidate_count chunks
        # without applying the final answerability threshold. Voyage rerank
        # then decides which chunks are most relevant. Applying the 0.5
        # threshold here can discard the correct chunk before reranking.
        candidate_min_similarity = (
            0.0
            if self._rerank_provider is not None
            else query.min_similarity
        )

        combined: list[tuple[Chunk, float]] = []
        for kb_id in kb_ids:
            try:
                pairs = await self._chunk_repository.semantic_search(
                    query_embedding=query_embedding,
                    tenant_id=query.tenant_id,
                    agent_id=query.agent_id,
                    knowledge_base_id=kb_id,
                    top_k=candidate_count,
                    min_similarity=candidate_min_similarity,
                )
            except RetrievalError:
                raise
            except Exception as exc:
                raise RetrievalError(
                    "An error occurred while searching the knowledge base."
                ) from exc
            combined.extend(pairs)
        return combined

    async def _rerank_candidates(
        self,
        query: RetrievalQuery,
        candidates: list[tuple[Chunk, float]],
        final_count: int,
    ) -> list[tuple[Chunk, float]]:
        """Rerank tenant-filtered candidates using Voyage rerank-2.5.

        Security invariant: only the query string and candidate chunk texts
        are sent to Voyage.  No tenant IDs, credentials, or internal IDs are
        transmitted.

        When reranking fails (``RetrievalError``), the service falls back to
        the pgvector similarity ranking.  The fallback still uses only the
        already-tenant-filtered candidates, so isolation is never bypassed.

        Args:
            query:       The original ``RetrievalQuery``.
            candidates:  Tenant-filtered ``(Chunk, pgvector_score)`` pairs,
                         sorted by descending pgvector similarity.
            final_count: Maximum number of chunks to return.

        Returns:
            A list of ``(Chunk, score)`` pairs, at most ``final_count`` long,
            ordered from most to least relevant.
        """
        # Sort by pgvector score before anything else (needed for safe fallback).
        sorted_candidates = sorted(
            candidates,
            key=lambda pair: pair[1],
            reverse=True,
        )

        # Global cap: Voyage never receives candidate_count
        # multiplied by the number of Knowledge Bases.
        candidate_limit = max(
            self._retrieval_candidate_count,
            final_count,
        )
        sorted_candidates = sorted_candidates[
            :candidate_limit
        ]

        if self._rerank_provider is None:
            # No reranker configured — return pgvector-ranked top-N.
            return sorted_candidates[:final_count]

        # Send ONLY query + chunk texts to Voyage (no tenant secrets).
        document_texts = [chunk.content for chunk, _ in sorted_candidates]

        try:
            rerank_result = await self._rerank_provider.rerank(
                RerankRequest(
                    query=query.query,
                    documents=document_texts,
                    top_k=final_count,
                )
            )
        except RetrievalError:
            # Reranker unavailable — fall back to pgvector ranking, but
            # restore the configured similarity threshold because the
            # reranker recall stage intentionally searched with 0.0.
            # Tenant isolation is preserved: candidates were already
            # tenant/agent/KB filtered by the repository.
            logger.warning(
                "Voyage reranker unavailable; falling back to pgvector "
                "similarity ranking for tenant=%s agent=%s.",
                query.tenant_id,
                query.agent_id,
            )
            thresholded_candidates = [
                pair
                for pair in sorted_candidates
                if pair[1] >= query.min_similarity
            ]
            return thresholded_candidates[:final_count]

        # Map reranked indices back to the original chunk objects.
        reranked: list[tuple[Chunk, float]] = []
        for position, original_index in enumerate(rerank_result.ranked_indices):
            chunk, _ = sorted_candidates[original_index]
            relevance_score = rerank_result.relevance_scores[position]
            reranked.append((chunk, relevance_score))

        return reranked
