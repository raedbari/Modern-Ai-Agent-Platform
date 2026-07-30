"""Tests for RetrievalService.

All tests are pure in-memory.  Lightweight stubs implement the three
injected interfaces so no real I/O occurs.

Stub variants
-------------
- ``StubEmbeddingProvider``      — returns a fixed vector; tracks call count.
- ``FailingEmbeddingProvider``   — always raises ``EmbeddingError``.
- ``StubKBRepository``           — returns a configurable list of KBs.
- ``StubChunkRepository``        — returns configurable ``(Chunk, score)`` pairs.
- ``FailingChunkRepository``     — always raises ``RetrievalError``.
- ``RaisingChunkRepository``     — raises a generic ``RuntimeError``.
"""

from __future__ import annotations

import pytest

from backend.app.ai.contracts import (
    EmbeddingRequest,
    EmbeddingResult as ProviderEmbeddingResult,
)
from backend.app.ai.ports import EmbeddingProvider
from backend.app.domain.exceptions import (
    EmbeddingError,
    RetrievalError,
    RetrievalValidationError,
)
from backend.app.domain.models.chunk import Chunk
from backend.app.domain.models.enums import KnowledgeBaseStatus
from backend.app.domain.models.knowledge_base import KnowledgeBase
from backend.app.domain.ports.repositories import ChunkRepository, KnowledgeBaseRepository
from backend.app.domain.ports.retrieval import RetrievalQuery, RetrievedChunk
from backend.app.services.knowledge.retrieval_service import RetrievalService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DIMS = 4


def _vec(val: float = 0.1) -> list[float]:
    return [val] * _DIMS


def _make_chunk(
    chunk_id: str = "c-1",
    tenant_id: str = "t-1",
    agent_id: str = "a-1",
    kb_id: str = "kb-1",
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
        content="Some content text.",
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
    min_similarity: float = 0.5,
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


class StubEmbeddingProvider(EmbeddingProvider):
    def __init__(self, vector: list[float] | None = None) -> None:
        self._vector = vector or _vec()
        self.call_count = 0
        self.last_text: str | None = None

    async def embed(
        self,
        request: EmbeddingRequest,
    ) -> ProviderEmbeddingResult:
        self.call_count += 1
        self.last_text = request.texts[0]
        return ProviderEmbeddingResult(
            embeddings=[list(self._vector) for _ in request.texts],
            model="test-embedding",
            dimension=len(self._vector),
        )


class FailingEmbeddingProvider(EmbeddingProvider):
    async def embed(
        self,
        request: EmbeddingRequest,
    ) -> ProviderEmbeddingResult:
        raise EmbeddingError("Provider is down.")


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
    """Returns configurable results per knowledge_base_id."""

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
                min_similarity=min_similarity,
            )
        )
        return list(self._results.get(knowledge_base_id, []))


class FailingChunkRepository(ChunkRepository):
    async def create_many(self, chunks):
        return chunks

    async def delete_by_document(self, document_id, tenant_id):
        return 0

    async def list_by_document(self, document_id, tenant_id):
        return []

    async def semantic_search(self, **kwargs):
        raise RetrievalError("Vector search failed.")


class RaisingChunkRepository(ChunkRepository):
    """Raises a generic RuntimeError — must be wrapped as RetrievalError."""

    async def create_many(self, chunks):
        return chunks

    async def delete_by_document(self, document_id, tenant_id):
        return 0

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
        raise RuntimeError("Unexpected DB error.")


def _make_service(
    *,
    provider: EmbeddingProvider | None = None,
    chunk_repo: ChunkRepository | None = None,
    kb_repo: KnowledgeBaseRepository | None = None,
    kbs: list[KnowledgeBase] | None = None,
    results_by_kb: dict | None = None,
) -> RetrievalService:
    return RetrievalService(
        embedding_provider=provider or StubEmbeddingProvider(),
        chunk_repository=chunk_repo or StubChunkRepository(results_by_kb),
        kb_repository=kb_repo or StubKBRepository(kbs),
    )


# ---------------------------------------------------------------------------
# Query validation
# ---------------------------------------------------------------------------


class TestQueryValidation:
    @pytest.mark.asyncio
    async def test_empty_query_text_raises(self) -> None:
        svc = _make_service()
        with pytest.raises(RetrievalValidationError, match="query"):
            await svc.retrieve(_make_query(query=""))

    @pytest.mark.asyncio
    async def test_whitespace_query_raises(self) -> None:
        svc = _make_service()
        with pytest.raises(RetrievalValidationError, match="query"):
            await svc.retrieve(_make_query(query="   "))

    @pytest.mark.asyncio
    async def test_empty_tenant_id_raises(self) -> None:
        svc = _make_service()
        with pytest.raises(RetrievalValidationError, match="tenant_id"):
            await svc.retrieve(_make_query(tenant_id=""))

    @pytest.mark.asyncio
    async def test_empty_agent_id_raises(self) -> None:
        svc = _make_service()
        with pytest.raises(RetrievalValidationError, match="agent_id"):
            await svc.retrieve(_make_query(agent_id=""))

    @pytest.mark.asyncio
    async def test_zero_top_k_raises(self) -> None:
        svc = _make_service()
        with pytest.raises(RetrievalValidationError, match="top_k"):
            await svc.retrieve(_make_query(top_k=0))

    @pytest.mark.asyncio
    async def test_negative_top_k_raises(self) -> None:
        svc = _make_service()
        with pytest.raises(RetrievalValidationError, match="top_k"):
            await svc.retrieve(_make_query(top_k=-1))

    @pytest.mark.asyncio
    async def test_similarity_below_zero_raises(self) -> None:
        svc = _make_service()
        with pytest.raises(RetrievalValidationError, match="min_similarity"):
            await svc.retrieve(_make_query(min_similarity=-0.1))

    @pytest.mark.asyncio
    async def test_similarity_above_one_raises(self) -> None:
        svc = _make_service()
        with pytest.raises(RetrievalValidationError, match="min_similarity"):
            await svc.retrieve(_make_query(min_similarity=1.1))

    @pytest.mark.asyncio
    async def test_similarity_zero_is_valid(self) -> None:
        svc = _make_service()
        result = await svc.retrieve(_make_query(min_similarity=0.0))
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_similarity_one_is_valid(self) -> None:
        svc = _make_service()
        result = await svc.retrieve(_make_query(min_similarity=1.0))
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_validation_happens_before_any_io(self) -> None:
        provider = StubEmbeddingProvider()
        svc = _make_service(provider=provider)
        with pytest.raises(RetrievalValidationError):
            await svc.retrieve(_make_query(query=""))
        assert provider.call_count == 0


# ---------------------------------------------------------------------------
# Knowledge base resolution
# ---------------------------------------------------------------------------


class TestKBResolution:
    @pytest.mark.asyncio
    async def test_no_kbs_raises_validation_error(self) -> None:
        svc = _make_service(kbs=[])
        with pytest.raises(RetrievalValidationError, match="no active knowledge bases"):
            await svc.retrieve(_make_query())

    @pytest.mark.asyncio
    async def test_all_inactive_kbs_raises(self) -> None:
        inactive_kb = _make_kb(status=KnowledgeBaseStatus.INACTIVE)
        svc = _make_service(kbs=[inactive_kb])
        with pytest.raises(RetrievalValidationError, match="no active knowledge bases"):
            await svc.retrieve(_make_query())

    @pytest.mark.asyncio
    async def test_only_active_kbs_are_searched(self) -> None:
        active = _make_kb(kb_id="kb-active", status=KnowledgeBaseStatus.ACTIVE)
        inactive = _make_kb(kb_id="kb-inactive", status=KnowledgeBaseStatus.INACTIVE)
        chunk_repo = StubChunkRepository()
        svc = _make_service(kbs=[active, inactive], chunk_repo=chunk_repo)
        await svc.retrieve(_make_query())
        searched_kb_ids = {call["knowledge_base_id"] for call in chunk_repo.calls}
        assert "kb-active" in searched_kb_ids
        assert "kb-inactive" not in searched_kb_ids

    @pytest.mark.asyncio
    async def test_mixed_active_inactive_uses_active_only(self) -> None:
        kbs = [
            _make_kb(kb_id="kb-1", status=KnowledgeBaseStatus.ACTIVE),
            _make_kb(kb_id="kb-2", status=KnowledgeBaseStatus.INACTIVE),
            _make_kb(kb_id="kb-3", status=KnowledgeBaseStatus.ACTIVE),
        ]
        chunk_repo = StubChunkRepository()
        svc = _make_service(kbs=kbs, chunk_repo=chunk_repo)
        await svc.retrieve(_make_query())
        searched = {c["knowledge_base_id"] for c in chunk_repo.calls}
        assert searched == {"kb-1", "kb-3"}


# ---------------------------------------------------------------------------
# Successful retrieval
# ---------------------------------------------------------------------------


class TestSuccessfulRetrieval:
    @pytest.mark.asyncio
    async def test_returns_list_of_retrieved_chunks(self) -> None:
        chunk = _make_chunk()
        svc = _make_service(results_by_kb={"kb-1": [(chunk, 0.9)]})
        result = await svc.retrieve(_make_query())
        assert isinstance(result, list)
        assert all(isinstance(r, RetrievedChunk) for r in result)

    @pytest.mark.asyncio
    async def test_empty_search_result_returns_empty_list(self) -> None:
        svc = _make_service(results_by_kb={"kb-1": []})
        result = await svc.retrieve(_make_query())
        assert result == []

    @pytest.mark.asyncio
    async def test_result_contains_correct_chunk(self) -> None:
        chunk = _make_chunk(chunk_id="the-chunk")
        svc = _make_service(results_by_kb={"kb-1": [(chunk, 0.9)]})
        result = await svc.retrieve(_make_query())
        assert result[0].chunk.id == "the-chunk"

    @pytest.mark.asyncio
    async def test_result_contains_correct_score(self) -> None:
        chunk = _make_chunk()
        svc = _make_service(results_by_kb={"kb-1": [(chunk, 0.87)]})
        result = await svc.retrieve(_make_query())
        assert result[0].similarity_score == 0.87

    @pytest.mark.asyncio
    async def test_embedding_provider_called_once(self) -> None:
        provider = StubEmbeddingProvider()
        svc = _make_service(provider=provider)
        await svc.retrieve(_make_query())
        assert provider.call_count == 1

    @pytest.mark.asyncio
    async def test_query_text_passed_to_provider(self) -> None:
        provider = StubEmbeddingProvider()
        svc = _make_service(provider=provider)
        await svc.retrieve(_make_query(query="What is the return policy?"))
        assert provider.last_text == "What is the return policy?"


# ---------------------------------------------------------------------------
# top_k enforcement
# ---------------------------------------------------------------------------


class TestTopKEnforcement:
    @pytest.mark.asyncio
    async def test_top_k_limits_results(self) -> None:
        pairs = [(_make_chunk(chunk_id=f"c-{i}"), 0.9 - i * 0.05) for i in range(8)]
        svc = _make_service(results_by_kb={"kb-1": pairs})
        result = await svc.retrieve(_make_query(top_k=3))
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_fewer_results_than_top_k_returns_all(self) -> None:
        pairs = [(_make_chunk(chunk_id=f"c-{i}"), 0.9) for i in range(2)]
        svc = _make_service(results_by_kb={"kb-1": pairs})
        result = await svc.retrieve(_make_query(top_k=10))
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_top_k_one_returns_single_result(self) -> None:
        pairs = [(_make_chunk(chunk_id=f"c-{i}"), 0.9 - i * 0.1) for i in range(5)]
        svc = _make_service(results_by_kb={"kb-1": pairs})
        result = await svc.retrieve(_make_query(top_k=1))
        assert len(result) == 1


# ---------------------------------------------------------------------------
# Ranking
# ---------------------------------------------------------------------------


class TestRanking:
    @pytest.mark.asyncio
    async def test_results_sorted_by_descending_score(self) -> None:
        pairs = [
            (_make_chunk(chunk_id="c-low"), 0.6),
            (_make_chunk(chunk_id="c-high"), 0.95),
            (_make_chunk(chunk_id="c-mid"), 0.75),
        ]
        svc = _make_service(results_by_kb={"kb-1": pairs})
        result = await svc.retrieve(_make_query(top_k=10))
        scores = [r.similarity_score for r in result]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_highest_score_is_first(self) -> None:
        pairs = [
            (_make_chunk(chunk_id="low"), 0.5),
            (_make_chunk(chunk_id="high"), 0.99),
        ]
        svc = _make_service(results_by_kb={"kb-1": pairs})
        result = await svc.retrieve(_make_query(top_k=5))
        assert result[0].chunk.id == "high"

    @pytest.mark.asyncio
    async def test_multi_kb_results_merged_and_sorted(self) -> None:
        chunk_a = _make_chunk(chunk_id="a", kb_id="kb-1")
        chunk_b = _make_chunk(chunk_id="b", kb_id="kb-2")
        chunk_c = _make_chunk(chunk_id="c", kb_id="kb-1")
        kbs = [
            _make_kb(kb_id="kb-1"),
            _make_kb(kb_id="kb-2"),
        ]
        results_by_kb = {
            "kb-1": [(chunk_a, 0.8), (chunk_c, 0.6)],
            "kb-2": [(chunk_b, 0.9)],
        }
        svc = _make_service(kbs=kbs, results_by_kb=results_by_kb)
        result = await svc.retrieve(_make_query(top_k=10))
        scores = [r.similarity_score for r in result]
        assert scores == sorted(scores, reverse=True)
        assert result[0].similarity_score == 0.9

    @pytest.mark.asyncio
    async def test_deterministic_ordering(self) -> None:
        pairs = [(_make_chunk(chunk_id=f"c-{i}"), 0.9 - i * 0.05) for i in range(5)]
        svc = _make_service(results_by_kb={"kb-1": pairs})
        r1 = await svc.retrieve(_make_query(top_k=10))
        r2 = await svc.retrieve(_make_query(top_k=10))
        assert [r.chunk.id for r in r1] == [r.chunk.id for r in r2]


# ---------------------------------------------------------------------------
# Tenant isolation
# ---------------------------------------------------------------------------


class TestTenantIsolation:
    @pytest.mark.asyncio
    async def test_tenant_id_passed_to_kb_repository(self) -> None:
        calls = []

        class TrackingKBRepo(StubKBRepository):
            async def list_for_agent(self, agent_id: str, tenant_id: str):
                calls.append(tenant_id)
                return await super().list_for_agent(agent_id, tenant_id)

        svc = RetrievalService(
            embedding_provider=StubEmbeddingProvider(),
            chunk_repository=StubChunkRepository(),
            kb_repository=TrackingKBRepo([_make_kb()]),
        )
        await svc.retrieve(_make_query(tenant_id="tenant-xyz"))
        assert "tenant-xyz" in calls

    @pytest.mark.asyncio
    async def test_tenant_id_passed_to_chunk_repository(self) -> None:
        chunk_repo = StubChunkRepository({"kb-1": [(_make_chunk(), 0.9)]})
        svc = _make_service(chunk_repo=chunk_repo)
        await svc.retrieve(_make_query(tenant_id="tenant-xyz"))
        assert chunk_repo.calls[0]["tenant_id"] == "tenant-xyz"

    @pytest.mark.asyncio
    async def test_agent_id_passed_to_chunk_repository(self) -> None:
        chunk_repo = StubChunkRepository({"kb-1": [(_make_chunk(), 0.9)]})
        svc = _make_service(chunk_repo=chunk_repo)
        await svc.retrieve(_make_query(agent_id="agent-xyz"))
        assert chunk_repo.calls[0]["agent_id"] == "agent-xyz"

    @pytest.mark.asyncio
    async def test_kb_id_passed_to_chunk_repository(self) -> None:
        chunk_repo = StubChunkRepository({"kb-special": [(_make_chunk(kb_id="kb-special"), 0.9)]})
        kbs = [_make_kb(kb_id="kb-special")]
        svc = _make_service(kbs=kbs, chunk_repo=chunk_repo)
        await svc.retrieve(_make_query())
        assert chunk_repo.calls[0]["knowledge_base_id"] == "kb-special"


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_embedding_error_propagates(self) -> None:
        svc = _make_service(provider=FailingEmbeddingProvider())
        with pytest.raises(EmbeddingError):
            await svc.retrieve(_make_query())

    @pytest.mark.asyncio
    async def test_retrieval_error_propagates(self) -> None:
        svc = RetrievalService(
            embedding_provider=StubEmbeddingProvider(),
            chunk_repository=FailingChunkRepository(),
            kb_repository=StubKBRepository([_make_kb()]),
        )
        with pytest.raises(RetrievalError):
            await svc.retrieve(_make_query())

    @pytest.mark.asyncio
    async def test_generic_repo_exception_wrapped_as_retrieval_error(self) -> None:
        svc = RetrievalService(
            embedding_provider=StubEmbeddingProvider(),
            chunk_repository=RaisingChunkRepository(),
            kb_repository=StubKBRepository([_make_kb()]),
        )
        with pytest.raises(RetrievalError):
            await svc.retrieve(_make_query())

    @pytest.mark.asyncio
    async def test_embedding_error_does_not_call_chunk_repo(self) -> None:
        chunk_repo = StubChunkRepository()
        svc = RetrievalService(
            embedding_provider=FailingEmbeddingProvider(),
            chunk_repository=chunk_repo,
            kb_repository=StubKBRepository([_make_kb()]),
        )
        with pytest.raises(EmbeddingError):
            await svc.retrieve(_make_query())
        assert chunk_repo.calls == []
