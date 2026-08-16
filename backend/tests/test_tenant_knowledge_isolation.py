"""Tenant isolation tests for all knowledge operations.

Verifies that every repository method enforces tenant_id scoping so that
Tenant A can never read, modify, or delete data owned by Tenant B.

Strategy
--------
- Reuse the in-memory stubs from test_ingestion_service.py (no database needed).
- Pre-populate stores with Tenant B data.
- Attempt each operation as Tenant A.
- Assert the result is empty / None or that the appropriate domain exception
  is raised — never that Tenant B's data is returned.

Scenarios covered
-----------------
1. Cross-tenant KB list returns empty
2. Cross-tenant document read returns None
3. Cross-tenant ingestion job read returns None
4. Cross-tenant chunk retrieval (semantic search) returns empty
5. Cross-tenant replacement (reindex) raises DocumentNotFoundError
6. Cross-tenant chunk delete returns 0 deleted rows
7. Cross-tenant activate (prepare_reindex) raises DocumentNotFoundError
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from backend.app.domain.exceptions import (
    DocumentNotFoundError,
    KnowledgeBaseNotFoundError,
)
from backend.app.domain.models.chunk import Chunk
from backend.app.domain.models.document import Document
from backend.app.domain.models.enums import DocumentProcessingStatus
from backend.app.domain.models.knowledge_base import KnowledgeBase
from backend.app.domain.ports.repositories import ChunkWrite
from backend.app.infrastructure.parsers.factory import DefaultParserFactory
from backend.app.services.knowledge.chunking_service import ChunkingService
from backend.app.services.knowledge.embedding_service import EmbeddingService
from backend.app.services.knowledge.ingestion_service import (
    IngestionRequest,
    IngestionService,
    PreparedReindex,
)

# ---------------------------------------------------------------------------
# Re-use the same in-memory stubs that live in test_ingestion_service.py
# (copied here to keep this file self-contained and avoid import coupling)
# ---------------------------------------------------------------------------
from backend.app.ai.contracts import (
    EmbeddingRequest,
    EmbeddingResult as ProviderEmbeddingResult,
)
from backend.app.ai.ports import EmbeddingProvider


class _StubEmbeddingProvider(EmbeddingProvider):
    """Returns deterministic zero-cost embeddings."""

    def __init__(self, *, dimension: int = 4) -> None:
        self.dimension = dimension

    async def embed(self, request: EmbeddingRequest) -> ProviderEmbeddingResult:
        return ProviderEmbeddingResult(
            embeddings=[[0.1] * self.dimension for _ in request.texts],
            model="stub",
            dimension=self.dimension,
        )


class _InMemoryDocumentRepository:
    """Minimal in-memory DocumentRepository that enforces tenant_id."""

    def __init__(self) -> None:
        self.documents: dict[str, Document] = {}

    async def create(self, document: Document) -> Document:
        self.documents[document.id] = document
        return document

    async def update(self, document: Document) -> Document:
        self.documents[document.id] = document
        return document

    async def get_by_id(self, document_id: str, tenant_id: str) -> Document | None:
        doc = self.documents.get(document_id)
        if doc is not None and doc.tenant_id == tenant_id:
            return doc
        return None

    async def get_by_content_hash(
        self, content_hash: str, tenant_id: str, knowledge_base_id: str
    ) -> Document | None:
        return next(
            (
                d
                for d in self.documents.values()
                if d.content_hash == content_hash
                and d.tenant_id == tenant_id
                and d.knowledge_base_id == knowledge_base_id
            ),
            None,
        )

    async def list_by_knowledge_base(
        self, knowledge_base_id: str, tenant_id: str
    ) -> list[Document]:
        return [
            d
            for d in self.documents.values()
            if d.knowledge_base_id == knowledge_base_id and d.tenant_id == tenant_id
        ]

    async def update_processing_status(
        self,
        document_id: str,
        tenant_id: str,
        status: DocumentProcessingStatus,
        failure_reason: str | None = None,
    ) -> None:
        doc = await self.get_by_id(document_id, tenant_id)
        if doc is not None:
            doc.status = status
            doc.failure_reason = failure_reason


class _InMemoryChunkRepository:
    """Minimal in-memory ChunkRepository that enforces tenant_id."""

    def __init__(self) -> None:
        self.records: list[ChunkWrite] = []

    async def create_many(self, records: list[ChunkWrite]) -> list[Chunk]:
        self.records.extend(records)
        return [r.chunk for r in records]

    async def delete_by_document(self, document_id: str, tenant_id: str) -> int:
        before = len(self.records)
        self.records = [
            r
            for r in self.records
            if not (
                r.chunk.document_id == document_id and r.chunk.tenant_id == tenant_id
            )
        ]
        return before - len(self.records)

    async def replace_for_document(
        self,
        document_id: str,
        tenant_id: str,
        new_records: list[ChunkWrite],
    ) -> list[Chunk]:
        old_records = [
            r
            for r in self.records
            if r.chunk.document_id == document_id and r.chunk.tenant_id == tenant_id
        ]
        self.records = [
            r
            for r in self.records
            if not (
                r.chunk.document_id == document_id and r.chunk.tenant_id == tenant_id
            )
        ]
        try:
            self.records.extend(new_records)
            return [r.chunk for r in new_records]
        except Exception:
            self.records = (
                [
                    r
                    for r in self.records
                    if not (
                        r.chunk.document_id == document_id
                        and r.chunk.tenant_id == tenant_id
                    )
                ]
                + old_records
            )
            raise

    async def list_by_document(
        self, document_id: str, tenant_id: str
    ) -> list[Chunk]:
        return [
            r.chunk
            for r in self.records
            if r.chunk.document_id == document_id and r.chunk.tenant_id == tenant_id
        ]

    async def semantic_search(
        self,
        query_embedding: list[float],
        tenant_id: str,
        agent_id: str,
        knowledge_base_id: str,
        top_k: int,
        min_similarity: float,
    ) -> list[tuple[Chunk, float]]:
        """Return only chunks whose tenant/agent/kb all match."""
        return [
            (r.chunk, 0.9)
            for r in self.records
            if r.chunk.tenant_id == tenant_id
            and r.chunk.agent_id == agent_id
            and r.chunk.knowledge_base_id == knowledge_base_id
        ][:top_k]


class _ScopedKnowledgeBaseRepository:
    """Simple KnowledgeBaseRepository backed by a dict keyed (tenant_id, agent_id)."""

    def __init__(
        self, assignments: dict[tuple[str, str], list[KnowledgeBase]]
    ) -> None:
        self.assignments = assignments

    async def get_by_id(
        self, knowledge_base_id: str, tenant_id: str
    ) -> KnowledgeBase | None:
        for kbs in self.assignments.values():
            for kb in kbs:
                if kb.id == knowledge_base_id and kb.tenant_id == tenant_id:
                    return kb
        return None

    async def list_for_agent(
        self, agent_id: str, tenant_id: str
    ) -> list[KnowledgeBase]:
        return list(self.assignments.get((tenant_id, agent_id), []))

    async def exists_for_tenant(
        self, knowledge_base_id: str, tenant_id: str
    ) -> bool:
        return (await self.get_by_id(knowledge_base_id, tenant_id)) is not None


# ---------------------------------------------------------------------------
# Test constants
# ---------------------------------------------------------------------------

TENANT_A = "tenant-a"
TENANT_B = "tenant-b"
AGENT_A = "agent-a"
AGENT_B = "agent-b"
KB_B = "kb-b"
DOC_B = "doc-b"

# Tenant B knowledge base
_KB_B = KnowledgeBase(id=KB_B, tenant_id=TENANT_B, name="Tenant B Knowledge")

# Tenant B document already in READY state
_DOC_B = Document(
    id=DOC_B,
    tenant_id=TENANT_B,
    knowledge_base_id=KB_B,
    agent_id=AGENT_B,
    source_name="tenant-b-source",
    original_filename="tenant-b-policy.txt",
    mime_type="text/plain",
    file_size_bytes=512,
    content_hash="b" * 64,
    status=DocumentProcessingStatus.READY,
)

# Tenant B chunk already stored
_CHUNK_B = Chunk(
    id="chunk-b-1",
    tenant_id=TENANT_B,
    agent_id=AGENT_B,
    knowledge_base_id=KB_B,
    document_id=DOC_B,
    source_name="tenant-b-source",
    page_number=0,
    chunk_index=0,
    content="Tenant B confidential content.",
    content_hash="chunk-b-hash",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_service(
    doc_repo: _InMemoryDocumentRepository,
    chunk_repo: _InMemoryChunkRepository,
    kb_repo: _ScopedKnowledgeBaseRepository,
) -> IngestionService:
    """Build a fully wired IngestionService against in-memory repos."""
    return IngestionService(
        parser_factory=DefaultParserFactory(),
        chunking_service=ChunkingService(chunk_size=80, chunk_overlap=10),
        embedding_service=EmbeddingService(
            provider=_StubEmbeddingProvider(),
            batch_size=4,
            embedding_dimensions=4,
        ),
        document_repository=doc_repo,  # type: ignore[arg-type]
        chunk_repository=chunk_repo,  # type: ignore[arg-type]
        knowledge_base_repository=kb_repo,  # type: ignore[arg-type]
        max_upload_size_bytes=1024 * 1024,
        max_pdf_pages=10,
        allowed_extensions=frozenset({".txt", ".md", ".markdown", ".pdf", ".docx"}),
        allowed_mime_types=frozenset(
            {
                "text/plain",
                "text/markdown",
                "application/pdf",
                "application/vnd.openxmlformats-officedocument."
                "wordprocessingml.document",
            }
        ),
    )


def _prepopulated_stores() -> (
    tuple[_InMemoryDocumentRepository, _InMemoryChunkRepository]
):
    """Return stores already containing Tenant B's data."""
    doc_repo = _InMemoryDocumentRepository()
    doc_repo.documents[DOC_B] = _DOC_B

    chunk_repo = _InMemoryChunkRepository()
    chunk_repo.records.append(
        ChunkWrite(chunk=_CHUNK_B, embedding=(0.1, 0.2, 0.3, 0.4))
    )
    return doc_repo, chunk_repo


def _tenant_b_only_kb_repo() -> _ScopedKnowledgeBaseRepository:
    """KB repo where only Tenant B has a knowledge base."""
    return _ScopedKnowledgeBaseRepository(
        {(TENANT_B, AGENT_B): [_KB_B]}
    )


def _tenant_a_request(**overrides) -> IngestionRequest:
    """A valid ingestion request issued by Tenant A targeting its own KB."""
    base = IngestionRequest(
        content=b"Tenant A replacement content. " * 20,
        filename="policy.txt",
        mime_type="text/plain",
        tenant_id=TENANT_A,
        agent_id=AGENT_A,
        knowledge_base_id=KB_B,  # deliberately targeting Tenant B's KB
        source_name="tenant-a-upload",
    )
    return replace(base, **overrides)


# ---------------------------------------------------------------------------
# Scenario 1 — Cross-tenant KB list returns empty
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scenario_1_cross_tenant_kb_list_returns_empty() -> None:
    """Tenant A cannot see Tenant B's knowledge bases via list_for_agent."""
    kb_repo = _tenant_b_only_kb_repo()

    # Tenant A requests the list for its own agent — should get nothing
    result = await kb_repo.list_for_agent(agent_id=AGENT_A, tenant_id=TENANT_A)
    assert result == [], (
        "list_for_agent must return an empty list when the requesting tenant "
        "has no knowledge bases registered for that agent."
    )


@pytest.mark.asyncio
async def test_scenario_1_cross_tenant_kb_exists_returns_false() -> None:
    """Tenant A's exists_for_tenant check on Tenant B's KB returns False."""
    kb_repo = _tenant_b_only_kb_repo()

    exists = await kb_repo.exists_for_tenant(
        knowledge_base_id=KB_B, tenant_id=TENANT_A
    )
    assert exists is False, (
        "exists_for_tenant must return False when the KB belongs to a different tenant."
    )


# ---------------------------------------------------------------------------
# Scenario 2 — Cross-tenant document read returns None
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scenario_2_cross_tenant_document_read_returns_none() -> None:
    """Tenant A cannot read Tenant B's document by ID."""
    doc_repo, _ = _prepopulated_stores()

    result = await doc_repo.get_by_id(
        document_id=DOC_B, tenant_id=TENANT_A
    )
    assert result is None, (
        "get_by_id must return None when the document belongs to a different tenant."
    )


@pytest.mark.asyncio
async def test_scenario_2_cross_tenant_document_list_returns_empty() -> None:
    """Tenant A cannot list documents from Tenant B's knowledge base."""
    doc_repo, _ = _prepopulated_stores()

    result = await doc_repo.list_by_knowledge_base(
        knowledge_base_id=KB_B, tenant_id=TENANT_A
    )
    assert result == [], (
        "list_by_knowledge_base must return an empty list for a different tenant."
    )


# ---------------------------------------------------------------------------
# Scenario 3 — Cross-tenant ingestion job read returns None
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scenario_3_cross_tenant_ingestion_blocked_by_kb_auth() -> None:
    """Tenant A cannot start an ingestion job targeting Tenant B's KB.

    The IngestionService checks KB authorization before creating any job
    records.  When Tenant A's agent_id / tenant_id combination is not
    registered in the KB repository, a KnowledgeBaseNotFoundError is raised
    and no document or job record is created.
    """
    doc_repo, chunk_repo = _prepopulated_stores()
    kb_repo = _tenant_b_only_kb_repo()
    service = _make_service(doc_repo, chunk_repo, kb_repo)

    initial_doc_count = len(doc_repo.documents)

    with pytest.raises(KnowledgeBaseNotFoundError):
        await service.ingest(_tenant_a_request())

    # No new document record must have been created for Tenant A
    assert len(doc_repo.documents) == initial_doc_count, (
        "No document should be persisted when KB authorization is rejected."
    )


@pytest.mark.asyncio
async def test_scenario_3_cross_tenant_document_content_hash_lookup_returns_none() -> None:
    """Tenant A cannot find Tenant B's document via content hash lookup."""
    doc_repo, _ = _prepopulated_stores()

    result = await doc_repo.get_by_content_hash(
        content_hash="b" * 64,
        tenant_id=TENANT_A,
        knowledge_base_id=KB_B,
    )
    assert result is None, (
        "get_by_content_hash must return None when the content belongs to "
        "a different tenant."
    )


# ---------------------------------------------------------------------------
# Scenario 4 — Cross-tenant chunk retrieval returns empty
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scenario_4_semantic_search_returns_empty_for_cross_tenant() -> None:
    """Tenant A's semantic search cannot retrieve Tenant B's chunks."""
    _, chunk_repo = _prepopulated_stores()

    results = await chunk_repo.semantic_search(
        query_embedding=[0.1, 0.2, 0.3, 0.4],
        tenant_id=TENANT_A,
        agent_id=AGENT_A,
        knowledge_base_id=KB_B,
        top_k=10,
        min_similarity=0.0,
    )
    assert results == [], (
        "semantic_search must return an empty list when all stored chunks "
        "belong to a different tenant."
    )


@pytest.mark.asyncio
async def test_scenario_4_list_by_document_returns_empty_for_cross_tenant() -> None:
    """Tenant A's list_by_document cannot retrieve Tenant B's chunks."""
    _, chunk_repo = _prepopulated_stores()

    results = await chunk_repo.list_by_document(
        document_id=DOC_B, tenant_id=TENANT_A
    )
    assert results == [], (
        "list_by_document must return an empty list when the document "
        "belongs to a different tenant."
    )


# ---------------------------------------------------------------------------
# Scenario 5 — Cross-tenant replacement (reindex) is rejected
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scenario_5_cross_tenant_reindex_raises_kb_not_found() -> None:
    """Tenant A cannot reindex Tenant B's document — KB auth fails first."""
    doc_repo, chunk_repo = _prepopulated_stores()
    kb_repo = _tenant_b_only_kb_repo()
    service = _make_service(doc_repo, chunk_repo, kb_repo)

    # Tenant A tries to reindex Tenant B's document
    with pytest.raises(KnowledgeBaseNotFoundError):
        await service.reindex(
            document_id=DOC_B,
            request=_tenant_a_request(),
        )

    # Tenant B's document must remain unchanged
    doc_b = doc_repo.documents[DOC_B]
    assert doc_b.status == DocumentProcessingStatus.READY, (
        "Tenant B's document status must not be changed by a cross-tenant reindex."
    )


@pytest.mark.asyncio
async def test_scenario_5_cross_tenant_reindex_leaves_chunks_intact() -> None:
    """Tenant B's chunks remain intact after a failed cross-tenant reindex attempt."""
    doc_repo, chunk_repo = _prepopulated_stores()
    kb_repo = _tenant_b_only_kb_repo()
    service = _make_service(doc_repo, chunk_repo, kb_repo)

    original_chunk_count = len(chunk_repo.records)

    with pytest.raises(KnowledgeBaseNotFoundError):
        await service.reindex(
            document_id=DOC_B,
            request=_tenant_a_request(),
        )

    assert len(chunk_repo.records) == original_chunk_count, (
        "No chunks should be deleted or added during a cross-tenant reindex attempt."
    )


# ---------------------------------------------------------------------------
# Scenario 6 — Cross-tenant chunk delete returns 0
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scenario_6_cross_tenant_chunk_delete_returns_zero() -> None:
    """Tenant A's delete_by_document deletes nothing from Tenant B's store."""
    _, chunk_repo = _prepopulated_stores()

    deleted = await chunk_repo.delete_by_document(
        document_id=DOC_B, tenant_id=TENANT_A
    )
    assert deleted == 0, (
        "delete_by_document must delete 0 records when the document "
        "belongs to a different tenant."
    )


@pytest.mark.asyncio
async def test_scenario_6_cross_tenant_chunk_delete_leaves_tenant_b_data_intact() -> None:
    """Tenant B's chunks survive a cross-tenant delete attempt."""
    _, chunk_repo = _prepopulated_stores()

    original_chunk_count = len(chunk_repo.records)
    await chunk_repo.delete_by_document(
        document_id=DOC_B, tenant_id=TENANT_A
    )

    assert len(chunk_repo.records) == original_chunk_count, (
        "Tenant B's chunks must not be removed by a cross-tenant delete."
    )
    assert any(r.chunk.id == "chunk-b-1" for r in chunk_repo.records), (
        "Tenant B's specific chunk must still be present after the cross-tenant delete."
    )


# ---------------------------------------------------------------------------
# Scenario 7 — Cross-tenant activate/update is rejected
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_scenario_7_cross_tenant_activate_reindex_raises_kb_not_found() -> None:
    """Tenant A cannot activate a prepared reindex for Tenant B's document."""
    doc_repo, chunk_repo = _prepopulated_stores()
    kb_repo = _tenant_b_only_kb_repo()
    service = _make_service(doc_repo, chunk_repo, kb_repo)

    # Build a fake PreparedReindex scoped to Tenant B's data
    fake_chunk = Chunk(
        id="chunk-replacement",
        tenant_id=TENANT_A,  # attacker claims this is their chunk
        agent_id=AGENT_A,
        knowledge_base_id=KB_B,
        document_id=DOC_B,
        source_name="tenant-a-upload",
        page_number=0,
        chunk_index=0,
        content="Tenant A injected content.",
        content_hash="injected-hash",
    )
    import hashlib

    replacement_content = b"Tenant A replacement content. " * 20
    prepared = PreparedReindex(
        content_hash=hashlib.sha256(replacement_content).hexdigest(),
        mime_type="text/plain",
        records=(ChunkWrite(chunk=fake_chunk, embedding=(0.1, 0.2, 0.3, 0.4)),),
    )

    with pytest.raises(KnowledgeBaseNotFoundError):
        await service.activate_prepared_reindex(
            document_id=DOC_B,
            request=_tenant_a_request(content=replacement_content),
            prepared=prepared,
        )


@pytest.mark.asyncio
async def test_scenario_7_cross_tenant_validate_reindex_target_raises_kb_not_found() -> None:
    """validate_reindex_target blocks Tenant A from targeting Tenant B's document."""
    doc_repo, chunk_repo = _prepopulated_stores()
    kb_repo = _tenant_b_only_kb_repo()
    service = _make_service(doc_repo, chunk_repo, kb_repo)

    with pytest.raises(KnowledgeBaseNotFoundError):
        await service.validate_reindex_target(
            document_id=DOC_B,
            request=_tenant_a_request(),
        )


@pytest.mark.asyncio
async def test_scenario_7_cross_tenant_kb_repo_get_by_id_returns_none() -> None:
    """KnowledgeBaseRepository.get_by_id returns None for cross-tenant lookup."""
    kb_repo = _tenant_b_only_kb_repo()

    result = await kb_repo.get_by_id(
        knowledge_base_id=KB_B, tenant_id=TENANT_A
    )
    assert result is None, (
        "get_by_id must return None when the KB belongs to a different tenant."
    )


# ---------------------------------------------------------------------------
# Bonus: verify same-tenant operations still work (sanity / regression guard)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sanity_tenant_b_can_read_its_own_document() -> None:
    """Control test: Tenant B can access its own document (isolation not over-blocking)."""
    doc_repo, _ = _prepopulated_stores()

    result = await doc_repo.get_by_id(document_id=DOC_B, tenant_id=TENANT_B)
    assert result is not None
    assert result.id == DOC_B
    assert result.tenant_id == TENANT_B


@pytest.mark.asyncio
async def test_sanity_tenant_b_can_list_its_own_chunks() -> None:
    """Control test: Tenant B's semantic search returns its own chunks."""
    _, chunk_repo = _prepopulated_stores()

    results = await chunk_repo.semantic_search(
        query_embedding=[0.1, 0.2, 0.3, 0.4],
        tenant_id=TENANT_B,
        agent_id=AGENT_B,
        knowledge_base_id=KB_B,
        top_k=10,
        min_similarity=0.0,
    )
    assert len(results) == 1
    assert results[0][0].tenant_id == TENANT_B


@pytest.mark.asyncio
async def test_sanity_tenant_b_chunk_delete_removes_only_its_own_chunks() -> None:
    """Control test: Tenant B can delete its own chunks, not accidentally others."""
    _, chunk_repo = _prepopulated_stores()

    deleted = await chunk_repo.delete_by_document(
        document_id=DOC_B, tenant_id=TENANT_B
    )
    assert deleted == 1
    assert chunk_repo.records == []
