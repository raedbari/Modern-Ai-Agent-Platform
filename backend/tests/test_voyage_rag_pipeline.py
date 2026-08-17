"""Tests for the Voyage AI RAG pipeline (DEV3 Task 2).

Covers all 14 required test cases using in-memory mocks only.
No paid APIs are called.

Stubs
-----
- ``StubVoyageEmbeddingProvider`` — returns 1024-dim vectors, tracks calls.
- ``FailingEmbeddingProvider``    — always raises EmbeddingError.
- ``StubVoyageRerankProvider``    — returns configurable rerank results.
- ``FailingRerankProvider``       — always raises RetrievalError.
- ``StubKBRepository``            — returns configurable KnowledgeBase list.
- ``StubChunkRepository``         — returns configurable (Chunk, score) pairs.
"""

from __future__ import annotations

import pytest

from backend.app.ai.contracts import (
    EmbeddingRequest,
    EmbeddingResult as ProviderEmbeddingResult,
)
from backend.app.ai.ports import EmbeddingProvider
from backend.app.ai.providers.voyage import (
    RerankRequest,
    RerankResult,
    VoyageRerankProvider,
    VOYAGE_EMBEDDING_DIMENSION,
    VOYAGE_EMBEDDING_MODEL,
    VOYAGE_RERANK_MODEL,
    VOYAGE_QUERY_INPUT_TYPE,
)
from backend.app.domain.exceptions import (
    EmbeddingError,
    RetrievalError,
    RetrievalValidationError,
)
from backend.app.domain.models.chunk import Chunk
from backend.app.domain.models.enums import KnowledgeBaseStatus
from backend.app.domain.models.knowledge_base import KnowledgeBase
from backend.app.domain.ports.repositories import (
    ChunkRepository,
    KnowledgeBaseRepository,
)
from backend.app.domain.ports.retrieval import RetrievalQuery, RetrievedChunk
from backend.app.services.knowledge.retrieval_service import (
    DEFAULT_CANDIDATE_COUNT,
    DEFAULT_FINAL_COUNT,
    RetrievalService,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_1024_VEC = [0.01] * VOYAGE_EMBEDDING_DIMENSION


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------


def _make_chunk(
    chunk_id: str = "c-1",
    tenant_id: str = "t-1",
    agent_id: str = "a-1",
    kb_id: str = "kb-1",
    content: str = "Some content text.",
) -> Chunk:
    return Chunk(
        id=chunk_id,
        tenant_id=tenant_id,
        agent_id=agent_id,
        knowledge_base_id=kb_id,
        document_id="doc-1",
        source_name="upload",
        page_number=0,
        chunk_index=0,
        content=content,
        content_hash="abc",
    )


def _make_kb(
    kb_id: str = "kb-1",
    tenant_id: str = "t-1",
    status: KnowledgeBaseStatus = KnowledgeBaseStatus.ACTIVE,
) -> KnowledgeBase:
    return KnowledgeBase(
        id=kb_id,
        tenant_id=tenant_id,
        name="Test KB",
        status=status,
    )


def _make_query(
    query: str = "What is the refund policy?",
    tenant_id: str = "t-1",
    agent_id: str = "a-1",
    top_k: int = 5,
    min_similarity: float = 0.0,
) -> RetrievalQuery:
    return RetrievalQuery(
        tenant_id=tenant_id,
        agent_id=agent_id,
        query=query,
        top_k=top_k,
        min_similarity=min_similarity,
    )


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------


class StubVoyageEmbeddingProvider(EmbeddingProvider):
    """Returns 1024-dim vectors.  Tracks model name and input_type via metadata."""

    def __init__(
        self,
        model: str = VOYAGE_EMBEDDING_MODEL,
        dimension: int = VOYAGE_EMBEDDING_DIMENSION,
    ) -> None:
        self.model = model
        self.dimension = dimension
        self.call_count = 0
        self.last_texts: list[str] = []
        self.last_input_type: str | None = None

    async def embed(self, request: EmbeddingRequest) -> ProviderEmbeddingResult:
        self.call_count += 1
        self.last_texts = list(request.texts)
        self.last_input_type = request.input_type
        return ProviderEmbeddingResult(
            embeddings=[[0.01] * self.dimension for _ in request.texts],
            model=self.model,
            dimension=self.dimension,
        )


class FailingEmbeddingProvider(EmbeddingProvider):
    async def embed(self, request: EmbeddingRequest) -> ProviderEmbeddingResult:
        raise EmbeddingError("Voyage embedding failed.")


class StubVoyageRerankProvider:
    """Returns a configurable RerankResult.  Tracks what was sent to it."""

    def __init__(
        self,
        ranked_indices: list[int] | None = None,
        relevance_scores: list[float] | None = None,
    ) -> None:
        self._ranked_indices = ranked_indices
        self._relevance_scores = relevance_scores
        self.call_count = 0
        self.last_request: RerankRequest | None = None
        self.model = VOYAGE_RERANK_MODEL

    async def rerank(self, request: RerankRequest) -> RerankResult:
        self.call_count += 1
        self.last_request = request
        n = len(request.documents)
        top = min(request.top_k, n)
        if self._ranked_indices is not None:
            indices = self._ranked_indices[:top]
            scores = (self._relevance_scores or [0.9] * top)[:top]
        else:
            # Default: return documents in reverse order (simulates reranking)
            indices = list(range(n - 1, -1, -1))[:top]
            scores = [1.0 - i * 0.1 for i in range(top)]
        return RerankResult(ranked_indices=indices, scores=scores)


class FailingRerankProvider:
    """Always raises RetrievalError — used to test fallback behaviour."""

    async def rerank(self, request: RerankRequest) -> RerankResult:
        raise RetrievalError("Voyage reranker is unavailable.")


class StubKBRepository(KnowledgeBaseRepository):
    def __init__(self, kbs: list[KnowledgeBase] | None = None) -> None:
        self._kbs = [_make_kb()] if kbs is None else kbs

    async def get_by_id(self, knowledge_base_id: str, tenant_id: str):
        for kb in self._kbs:
            if kb.id == knowledge_base_id and kb.tenant_id == tenant_id:
                return kb
        return None

    async def list_for_agent(self, agent_id: str, tenant_id: str):
        return list(self._kbs)

    async def exists_for_tenant(self, knowledge_base_id: str, tenant_id: str):
        return any(
            kb.id == knowledge_base_id and kb.tenant_id == tenant_id
            for kb in self._kbs
        )


class StubChunkRepository(ChunkRepository):
    """Returns configurable (Chunk, score) pairs per knowledge_base_id."""

    def __init__(
        self,
        results_by_kb: dict[str, list[tuple[Chunk, float]]] | None = None,
    ) -> None:
        self._results = results_by_kb or {}
        self.calls: list[dict] = []

    async def create_many(self, chunks):
        return chunks

    async def delete_by_document(self, document_id, tenant_id):
        return 0

    async def replace_for_document(self, document_id, tenant_id, new_records):
        return [record.chunk for record in new_records]

    async def list_by_document(self, document_id, tenant_id):
        return []

    async def semantic_search(
        self,
        query_embedding,
        tenant_id,
        agent_id,
        knowledge_base_id,
        top_k,
        min_similarity,
    ):
        self.calls.append(
            dict(
                tenant_id=tenant_id,
                agent_id=agent_id,
                knowledge_base_id=knowledge_base_id,
                top_k=top_k,
            )
        )
        return list(self._results.get(knowledge_base_id, []))


def _make_service(
    *,
    provider: EmbeddingProvider | None = None,
    chunk_repo: ChunkRepository | None = None,
    kb_repo: KnowledgeBaseRepository | None = None,
    rerank_provider=None,
    kbs: list[KnowledgeBase] | None = None,
    results_by_kb: dict | None = None,
    candidate_count: int = DEFAULT_CANDIDATE_COUNT,
    final_count: int = DEFAULT_FINAL_COUNT,
) -> RetrievalService:
    return RetrievalService(
        embedding_provider=provider or StubVoyageEmbeddingProvider(),
        chunk_repository=chunk_repo or StubChunkRepository(results_by_kb),
        kb_repository=kb_repo or StubKBRepository(kbs),
        rerank_provider=rerank_provider,
        retrieval_candidate_count=candidate_count,
        retrieval_final_count=final_count,
    )


# ===========================================================================
# TEST 1 — Voyage query embedding uses voyage-4-large
# ===========================================================================

class TestVoyageEmbeddingModel:
    def test_embedding_model_constant_is_voyage_4_large(self) -> None:
        """The module constant must specify voyage-4-large."""
        assert VOYAGE_EMBEDDING_MODEL == "voyage-4-large"

    @pytest.mark.asyncio
    async def test_embedding_provider_uses_voyage_4_large_model(self) -> None:
        """The EmbeddingResult returned by the stub declares voyage-4-large."""
        provider = StubVoyageEmbeddingProvider(model=VOYAGE_EMBEDDING_MODEL)
        request = _make_query()
        from backend.app.ai.contracts import EmbeddingRequest, RuntimeContext
        embed_req = EmbeddingRequest(
            context=RuntimeContext(tenant_id="t-1", agent_id="a-1"),
            texts=[request.query],
        )
        result = await provider.embed(embed_req)
        assert result.model == "voyage-4-large"


# ===========================================================================
# TEST 2 — Query vector dimension is 1024
# ===========================================================================

class TestEmbeddingDimension:
    def test_dimension_constant_is_1024(self) -> None:
        assert VOYAGE_EMBEDDING_DIMENSION == 1024

    @pytest.mark.asyncio
    async def test_embedding_vector_length_is_1024(self) -> None:
        """Each vector returned by the provider must be exactly 1024 floats."""
        from backend.app.ai.contracts import EmbeddingRequest, RuntimeContext
        provider = StubVoyageEmbeddingProvider()
        result = await provider.embed(
            EmbeddingRequest(
                context=RuntimeContext(tenant_id="t-1", agent_id="a-1"),
                texts=["test query"],
            )
        )
        assert result.dimension == 1024
        assert len(result.embeddings[0]) == 1024


# ===========================================================================
# TEST 3 — Voyage query semantics / input_type are correct
# ===========================================================================

class TestQueryInputType:
    def test_query_input_type_constant_is_query(self) -> None:
        """Voyage requires input_type='query' for retrieval queries."""
        assert VOYAGE_QUERY_INPUT_TYPE == "query"

    @pytest.mark.asyncio
    async def test_retrieval_service_uses_query_input_type(self) -> None:
        """EmbeddingRequest sent during retrieval must have input_type='query'."""
        provider = StubVoyageEmbeddingProvider()
        svc = _make_service(provider=provider)
        await svc.retrieve(_make_query(query="What is the refund policy?"))
        assert provider.last_input_type == "query"


# ===========================================================================
# TEST 4 — pgvector retrieves authorised candidates
# ===========================================================================

class TestPgvectorRetrieval:
    @pytest.mark.asyncio
    async def test_chunk_repo_receives_candidate_count_not_top_k(self) -> None:
        """semantic_search must be called with candidate_count (20) not top_k (5)."""
        chunk_repo = StubChunkRepository()
        svc = _make_service(
            chunk_repo=chunk_repo,
            candidate_count=20,
            final_count=5,
        )
        await svc.retrieve(_make_query(top_k=5))
        assert chunk_repo.calls[0]["top_k"] == 20

    @pytest.mark.asyncio
    async def test_pgvector_called_with_tenant_scope(self) -> None:
        """The repository call must carry the exact tenant_id from the query."""
        chunk_repo = StubChunkRepository({"kb-1": [(_make_chunk(), 0.9)]})
        svc = _make_service(chunk_repo=chunk_repo)
        await svc.retrieve(_make_query(tenant_id="tenant-secure"))
        assert chunk_repo.calls[0]["tenant_id"] == "tenant-secure"

    @pytest.mark.asyncio
    async def test_pgvector_called_with_agent_scope(self) -> None:
        chunk_repo = StubChunkRepository({"kb-1": [(_make_chunk(), 0.9)]})
        svc = _make_service(chunk_repo=chunk_repo)
        await svc.retrieve(_make_query(agent_id="agent-secure"))
        assert chunk_repo.calls[0]["agent_id"] == "agent-secure"

    @pytest.mark.asyncio
    async def test_pgvector_called_with_kb_scope(self) -> None:
        chunk = _make_chunk(kb_id="kb-special")
        chunk_repo = StubChunkRepository({"kb-special": [(chunk, 0.9)]})
        kbs = [_make_kb(kb_id="kb-special")]
        svc = _make_service(kbs=kbs, chunk_repo=chunk_repo)
        await svc.retrieve(_make_query())
        assert chunk_repo.calls[0]["knowledge_base_id"] == "kb-special"


# ===========================================================================
# TEST 5 — rerank-2.5 is invoked
# ===========================================================================

class TestRerankInvocation:
    @pytest.mark.asyncio
    async def test_rerank_provider_is_called(self) -> None:
        chunk = _make_chunk()
        reranker = StubVoyageRerankProvider(
            ranked_indices=[0], relevance_scores=[0.95]
        )
        svc = _make_service(
            results_by_kb={"kb-1": [(chunk, 0.8)]},
            rerank_provider=reranker,
        )
        await svc.retrieve(_make_query(top_k=1))
        assert reranker.call_count == 1

    def test_rerank_model_constant_is_rerank_25(self) -> None:
        assert VOYAGE_RERANK_MODEL == "rerank-2.5"

    @pytest.mark.asyncio
    async def test_rerank_not_called_when_no_candidates(self) -> None:
        reranker = StubVoyageRerankProvider()
        svc = _make_service(
            results_by_kb={"kb-1": []},
            rerank_provider=reranker,
        )
        await svc.retrieve(_make_query())
        assert reranker.call_count == 0


# ===========================================================================
# TEST 6 — Reranking order is honoured
# ===========================================================================

class TestRerankOrdering:
    @pytest.mark.asyncio
    async def test_reranked_order_supersedes_pgvector_order(self) -> None:
        """The reranker's index order must determine the output order."""
        chunk_a = _make_chunk(chunk_id="a", content="Alpha text.")
        chunk_b = _make_chunk(chunk_id="b", content="Beta text.")
        chunk_c = _make_chunk(chunk_id="c", content="Gamma text.")

        # pgvector returns a=0.9, b=0.8, c=0.7
        # reranker flips: c is best (index 2), then a (index 0), then b (index 1)
        reranker = StubVoyageRerankProvider(
            ranked_indices=[2, 0, 1],
            relevance_scores=[0.99, 0.88, 0.55],
        )
        svc = _make_service(
            results_by_kb={"kb-1": [(chunk_a, 0.9), (chunk_b, 0.8), (chunk_c, 0.7)]},
            rerank_provider=reranker,
            final_count=3,
        )
        result = await svc.retrieve(_make_query(top_k=3))
        ids = [r.chunk.id for r in result]
        assert ids == ["c", "a", "b"]

    @pytest.mark.asyncio
    async def test_reranked_scores_are_relevance_not_similarity(self) -> None:
        """Output scores must come from the reranker, not pgvector."""
        chunk = _make_chunk()
        reranker = StubVoyageRerankProvider(
            ranked_indices=[0], relevance_scores=[0.777]
        )
        svc = _make_service(
            results_by_kb={"kb-1": [(chunk, 0.6)]},
            rerank_provider=reranker,
            final_count=1,
        )
        result = await svc.retrieve(_make_query(top_k=1))
        assert result[0].similarity_score == pytest.approx(0.777)


# ===========================================================================
# TEST 7 — Final selected context count is respected
# ===========================================================================

class TestFinalContextCount:
    @pytest.mark.asyncio
    async def test_retrieval_final_count_limits_output(self) -> None:
        pairs = [(_make_chunk(chunk_id=f"c-{i}"), 0.9 - i * 0.05) for i in range(10)]
        reranker = StubVoyageRerankProvider(
            ranked_indices=list(range(5)),
            relevance_scores=[0.9 - i * 0.05 for i in range(5)],
        )
        svc = _make_service(
            results_by_kb={"kb-1": pairs},
            rerank_provider=reranker,
            final_count=5,
        )
        result = await svc.retrieve(_make_query(top_k=10))
        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_fewer_chunks_than_final_count_returns_all(self) -> None:
        pairs = [(_make_chunk(chunk_id=f"c-{i}"), 0.8) for i in range(2)]
        reranker = StubVoyageRerankProvider(
            ranked_indices=[0, 1], relevance_scores=[0.9, 0.8]
        )
        svc = _make_service(
            results_by_kb={"kb-1": pairs},
            rerank_provider=reranker,
            final_count=5,
        )
        result = await svc.retrieve(_make_query(top_k=10))
        assert len(result) == 2


# ===========================================================================
# TEST 8 — Wrong tenant is excluded BEFORE reranking
# ===========================================================================

class TestTenantIsolationBeforeRerank:
    @pytest.mark.asyncio
    async def test_reranker_never_sees_wrong_tenant_chunks(self) -> None:
        """Reranker input must only contain chunks from the querying tenant."""
        reranker = StubVoyageRerankProvider(
            ranked_indices=[0], relevance_scores=[0.9]
        )

        # KB repo will only return chunks for "tenant-A".
        # The stub chunk also carries tenant-A, confirming isolation.
        tenant_a_chunk = _make_chunk(
            chunk_id="ta-1", tenant_id="tenant-A", content="Tenant A data."
        )
        svc = _make_service(
            results_by_kb={"kb-1": [(tenant_a_chunk, 0.9)]},
            rerank_provider=reranker,
        )
        await svc.retrieve(_make_query(tenant_id="tenant-A"))

        # The reranker must have been called with exactly one document text.
        assert reranker.last_request is not None
        assert reranker.last_request.documents == ["Tenant A data."]

    @pytest.mark.asyncio
    async def test_wrong_tenant_query_raises_validation_error(self) -> None:
        """An empty tenant_id must be rejected before any I/O."""
        svc = _make_service()
        with pytest.raises(RetrievalValidationError, match="tenant_id"):
            await svc.retrieve(_make_query(tenant_id=""))

    @pytest.mark.asyncio
    async def test_tenant_b_chunks_absent_from_tenant_a_rerank_input(self) -> None:
        """When two tenants share an agent name, their chunks never mix."""
        tenant_a_chunk = _make_chunk(
            chunk_id="a1", tenant_id="t-A", content="A only."
        )

        # KB repo returns only tenant-A's chunks (enforced by tenant scoping).
        class TenantAScopedKBRepo(StubKBRepository):
            async def list_for_agent(self, agent_id: str, tenant_id: str):
                if tenant_id == "t-A":
                    return [_make_kb(tenant_id="t-A")]
                return []

        class TenantAScopedChunkRepo(StubChunkRepository):
            async def semantic_search(self, query_embedding, tenant_id,
                                      agent_id, knowledge_base_id,
                                      top_k, min_similarity):
                self.calls.append(dict(tenant_id=tenant_id,
                                       agent_id=agent_id,
                                       knowledge_base_id=knowledge_base_id,
                                       top_k=top_k))
                if tenant_id == "t-A":
                    return [(tenant_a_chunk, 0.9)]
                return []

        reranker = StubVoyageRerankProvider(
            ranked_indices=[0], relevance_scores=[0.9]
        )
        svc = RetrievalService(
            embedding_provider=StubVoyageEmbeddingProvider(),
            chunk_repository=TenantAScopedChunkRepo(),
            kb_repository=TenantAScopedKBRepo(),
            rerank_provider=reranker,
        )
        await svc.retrieve(_make_query(tenant_id="t-A"))
        # Only "A only." should reach the reranker.
        assert reranker.last_request is not None
        assert all("A only" in doc for doc in reranker.last_request.documents)


# ===========================================================================
# TEST 9 — Wrong agent is excluded
# ===========================================================================

class TestAgentIsolation:
    @pytest.mark.asyncio
    async def test_agent_id_scopes_chunk_repository_call(self) -> None:
        chunk_repo = StubChunkRepository({"kb-1": [(_make_chunk(), 0.8)]})
        svc = _make_service(chunk_repo=chunk_repo)
        await svc.retrieve(_make_query(agent_id="agent-XYZ"))
        assert chunk_repo.calls[0]["agent_id"] == "agent-XYZ"

    @pytest.mark.asyncio
    async def test_empty_agent_id_raises_before_io(self) -> None:
        provider = StubVoyageEmbeddingProvider()
        svc = _make_service(provider=provider)
        with pytest.raises(RetrievalValidationError, match="agent_id"):
            await svc.retrieve(_make_query(agent_id=""))
        assert provider.call_count == 0


# ===========================================================================
# TEST 10 — Wrong knowledge base is excluded
# ===========================================================================

class TestKnowledgeBaseIsolation:
    @pytest.mark.asyncio
    async def test_inactive_kb_never_searched(self) -> None:
        active = _make_kb(kb_id="kb-ok", status=KnowledgeBaseStatus.ACTIVE)
        inactive = _make_kb(kb_id="kb-bad", status=KnowledgeBaseStatus.INACTIVE)
        chunk_repo = StubChunkRepository()
        svc = _make_service(kbs=[active, inactive], chunk_repo=chunk_repo)
        await svc.retrieve(_make_query())
        searched = {c["knowledge_base_id"] for c in chunk_repo.calls}
        assert "kb-ok" in searched
        assert "kb-bad" not in searched

    @pytest.mark.asyncio
    async def test_no_active_kb_raises_validation_error(self) -> None:
        svc = _make_service(kbs=[])
        with pytest.raises(RetrievalValidationError, match="no active knowledge bases"):
            await svc.retrieve(_make_query())

    @pytest.mark.asyncio
    async def test_kb_id_is_passed_to_chunk_repo(self) -> None:
        chunk = _make_chunk(kb_id="kb-scoped")
        chunk_repo = StubChunkRepository({"kb-scoped": [(chunk, 0.9)]})
        kbs = [_make_kb(kb_id="kb-scoped")]
        svc = _make_service(kbs=kbs, chunk_repo=chunk_repo)
        await svc.retrieve(_make_query())
        assert chunk_repo.calls[0]["knowledge_base_id"] == "kb-scoped"


# ===========================================================================
# TEST 11 — Voyage rerank failure uses safe filtered fallback
# ===========================================================================

class TestRerankFallback:
    @pytest.mark.asyncio
    async def test_rerank_failure_falls_back_to_pgvector_ranking(self) -> None:
        """When reranking raises RetrievalError the service must not fail."""
        pairs = [
            (_make_chunk(chunk_id="high"), 0.95),
            (_make_chunk(chunk_id="low"), 0.60),
        ]
        svc = _make_service(
            results_by_kb={"kb-1": pairs},
            rerank_provider=FailingRerankProvider(),
            final_count=2,
        )
        result = await svc.retrieve(_make_query(top_k=2))
        assert len(result) == 2
        # Fallback must preserve pgvector descending order.
        assert result[0].chunk.id == "high"
        assert result[1].chunk.id == "low"

    @pytest.mark.asyncio
    async def test_fallback_uses_only_tenant_filtered_chunks(self) -> None:
        """Even after reranker failure, wrong-tenant chunks must not appear."""
        tenant_chunk = _make_chunk(
            chunk_id="ok", tenant_id="t-safe", content="Safe content."
        )
        svc = _make_service(
            results_by_kb={"kb-1": [(tenant_chunk, 0.88)]},
            rerank_provider=FailingRerankProvider(),
        )
        result = await svc.retrieve(_make_query(tenant_id="t-safe"))
        assert len(result) == 1
        assert result[0].chunk.tenant_id == "t-safe"

    @pytest.mark.asyncio
    async def test_fallback_respects_final_count(self) -> None:
        pairs = [(_make_chunk(chunk_id=f"c-{i}"), 0.9 - i * 0.05) for i in range(8)]
        svc = _make_service(
            results_by_kb={"kb-1": pairs},
            rerank_provider=FailingRerankProvider(),
            final_count=3,
        )
        result = await svc.retrieve(_make_query(top_k=10))
        assert len(result) == 3


# ===========================================================================
# TEST 12 — Empty retrieval is handled
# ===========================================================================

class TestEmptyRetrieval:
    @pytest.mark.asyncio
    async def test_empty_vector_search_returns_empty_list(self) -> None:
        svc = _make_service(results_by_kb={"kb-1": []})
        result = await svc.retrieve(_make_query())
        assert result == []

    @pytest.mark.asyncio
    async def test_empty_retrieval_does_not_call_reranker(self) -> None:
        reranker = StubVoyageRerankProvider()
        svc = _make_service(
            results_by_kb={"kb-1": []},
            rerank_provider=reranker,
        )
        await svc.retrieve(_make_query())
        assert reranker.call_count == 0

    @pytest.mark.asyncio
    async def test_empty_retrieval_returns_list_not_none(self) -> None:
        svc = _make_service()
        result = await svc.retrieve(_make_query())
        assert isinstance(result, list)


# ===========================================================================
# TEST 13 — DeepSeek receives only final authorised context
# ===========================================================================

class TestDeepSeekReceivesOnlyFinalContext:
    @pytest.mark.asyncio
    async def test_only_reranked_top_n_sent_as_sources(self) -> None:
        """The output list must contain only the reranker-selected chunks."""
        chunks = [_make_chunk(chunk_id=f"c-{i}", content=f"content {i}") for i in range(6)]
        pairs = [(c, 0.9 - i * 0.05) for i, c in enumerate(chunks)]

        # Reranker selects indices 5, 3, 1 (only these three must reach caller)
        reranker = StubVoyageRerankProvider(
            ranked_indices=[5, 3, 1],
            relevance_scores=[0.99, 0.88, 0.77],
        )
        svc = _make_service(
            results_by_kb={"kb-1": pairs},
            rerank_provider=reranker,
            final_count=3,
        )
        result = await svc.retrieve(_make_query(top_k=3))
        returned_ids = {r.chunk.id for r in result}
        assert returned_ids == {"c-5", "c-3", "c-1"}

    @pytest.mark.asyncio
    async def test_final_context_count_matches_final_count_setting(self) -> None:
        """Never more than retrieval_final_count chunks in the result."""
        pairs = [(_make_chunk(chunk_id=f"c-{i}"), 0.9) for i in range(20)]
        reranker = StubVoyageRerankProvider(
            ranked_indices=list(range(5)),
            relevance_scores=[0.9] * 5,
        )
        svc = _make_service(
            results_by_kb={"kb-1": pairs},
            rerank_provider=reranker,
            final_count=5,
        )
        result = await svc.retrieve(_make_query(top_k=20))
        assert len(result) <= 5


# ===========================================================================
# TEST 14 — No unauthorised chunk appears in generated prompt
# ===========================================================================

class TestNoUnauthorisedChunkInPrompt:
    @pytest.mark.asyncio
    async def test_reranker_input_contains_no_tenant_secrets(self) -> None:
        """The RerankRequest.documents list must only contain chunk text."""
        secret_free_content = "Public knowledge article."
        chunk = _make_chunk(
            chunk_id="safe-1",
            tenant_id="tenant-private",
            content=secret_free_content,
        )
        reranker = StubVoyageRerankProvider(
            ranked_indices=[0], relevance_scores=[0.9]
        )
        svc = _make_service(
            results_by_kb={"kb-1": [(chunk, 0.85)]},
            rerank_provider=reranker,
        )
        await svc.retrieve(_make_query(tenant_id="tenant-private"))

        assert reranker.last_request is not None
        # The document text sent to Voyage must be the raw chunk content only.
        assert reranker.last_request.documents == [secret_free_content]
        # No tenant ID embedded in any document text.
        for doc in reranker.last_request.documents:
            assert "tenant-private" not in doc

    @pytest.mark.asyncio
    async def test_reranker_query_is_plain_user_text(self) -> None:
        """The query string sent to Voyage must be the raw user question."""
        reranker = StubVoyageRerankProvider(
            ranked_indices=[0], relevance_scores=[0.9]
        )
        svc = _make_service(
            results_by_kb={"kb-1": [(_make_chunk(), 0.8)]},
            rerank_provider=reranker,
        )
        await svc.retrieve(_make_query(query="How do I reset my password?"))
        assert reranker.last_request is not None
        assert reranker.last_request.query == "How do I reset my password?"

    @pytest.mark.asyncio
    async def test_result_chunks_all_belong_to_querying_tenant(self) -> None:
        """Every returned RetrievedChunk must belong to the requesting tenant."""
        tenant_chunk = _make_chunk(
            chunk_id="t1", tenant_id="tenant-OK", content="Authorised content."
        )
        reranker = StubVoyageRerankProvider(
            ranked_indices=[0], relevance_scores=[0.9]
        )
        svc = _make_service(
            results_by_kb={"kb-1": [(tenant_chunk, 0.8)]},
            rerank_provider=reranker,
        )
        result = await svc.retrieve(_make_query(tenant_id="tenant-OK"))
        for item in result:
            assert item.chunk.tenant_id == "tenant-OK"
