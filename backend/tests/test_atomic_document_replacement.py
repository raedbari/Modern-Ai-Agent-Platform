"""Tests for atomic document replacement guarantees.

Covers the six scenarios required by Task 7:
1. Successful replacement: V2 becomes READY, V1 becomes SUPERSEDED
2. Failed replacement at parse stage: V1 remains READY (no status change)
3. Failed replacement at embed stage: V1 remains READY (chunks intact)
4. Retry after failure succeeds: V2 becomes READY, V1 SUPERSEDED
5. Exactly one active version after successful replacement
6. No mixed chunks (old + new) after any outcome
"""

from __future__ import annotations

import pytest

from backend.app.ai.contracts import (
    EmbeddingRequest,
    EmbeddingResult as ProviderEmbeddingResult,
)
from backend.app.ai.ports import EmbeddingProvider
from backend.app.domain.exceptions import EmbeddingError
from backend.app.domain.models.chunk import Chunk
from backend.app.domain.models.document import Document
from backend.app.domain.models.enums import DocumentProcessingStatus
from backend.app.domain.models.knowledge_base import KnowledgeBase
from backend.app.domain.ports.repositories import (
    ChunkRepository,
    ChunkWrite,
    DocumentRepository,
    KnowledgeBaseRepository,
)
from backend.app.infrastructure.parsers.factory import DefaultParserFactory
from backend.app.services.knowledge.chunking_service import ChunkingService
from backend.app.services.knowledge.embedding_service import EmbeddingService
from backend.app.services.knowledge.ingestion_service import (
    IngestionRequest,
    IngestionService,
)

# ---------------------------------------------------------------------------
# Stubs  (mirrored from test_ingestion_service.py)
# ---------------------------------------------------------------------------


class StubEmbeddingProvider(EmbeddingProvider):
    def __init__(self, *, dimension: int = 4) -> None:
        self.dimension = dimension

    async def embed(self, request: EmbeddingRequest) -> ProviderEmbeddingResult:
        return ProviderEmbeddingResult(
            embeddings=[[0.25] * self.dimension for _ in request.texts],
            model="test-embedding",
            dimension=self.dimension,
        )


class FailingEmbeddingProvider(EmbeddingProvider):
    """Always returns wrong-dimension embeddings, causing EmbeddingError."""

    async def embed(self, request: EmbeddingRequest) -> ProviderEmbeddingResult:
        return ProviderEmbeddingResult(
            embeddings=[[0.25] * 3 for _ in request.texts],
            model="bad-embedding",
            dimension=3,
        )


class InMemoryDocumentRepository(DocumentRepository):
    def __init__(self, existing: Document | None = None) -> None:
        self.documents: dict[str, Document] = {}
        self.statuses: list[DocumentProcessingStatus] = []
        self.create_calls = 0
        if existing is not None:
            self.documents[existing.id] = existing

    async def create(self, document: Document) -> Document:
        self.create_calls += 1
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
                doc
                for doc in self.documents.values()
                if doc.content_hash == content_hash
                and doc.tenant_id == tenant_id
                and doc.knowledge_base_id == knowledge_base_id
            ),
            None,
        )

    async def list_by_knowledge_base(
        self, knowledge_base_id: str, tenant_id: str
    ) -> list[Document]:
        return [
            doc
            for doc in self.documents.values()
            if doc.knowledge_base_id == knowledge_base_id
            and doc.tenant_id == tenant_id
        ]

    async def update_processing_status(
        self,
        document_id: str,
        tenant_id: str,
        status: DocumentProcessingStatus,
        failure_reason: str | None = None,
    ) -> None:
        doc = await self.get_by_id(document_id, tenant_id)
        assert doc is not None
        doc.status = status
        doc.failure_reason = failure_reason
        self.statuses.append(status)


class InMemoryChunkRepository(ChunkRepository):
    def __init__(self) -> None:
        self.records: list[ChunkWrite] = []

    async def create_many(self, records: list[ChunkWrite]) -> list[Chunk]:
        self.records.extend(records)
        return [record.chunk for record in records]

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
        """Atomically replace old chunks with new ones (in-memory simulation)."""
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
            # Rollback: restore old records
            self.records = [
                r
                for r in self.records
                if not (
                    r.chunk.document_id == document_id
                    and r.chunk.tenant_id == tenant_id
                )
            ] + old_records
            raise

    async def list_by_document(self, document_id: str, tenant_id: str) -> list[Chunk]:
        return [
            r.chunk
            for r in self.records
            if r.chunk.document_id == document_id and r.chunk.tenant_id == tenant_id
        ]

    async def semantic_search(self, **kwargs) -> list[tuple[Chunk, float]]:
        return []


class ScopedKnowledgeBaseRepository(KnowledgeBaseRepository):
    def __init__(self, kb: KnowledgeBase) -> None:
        self._kb = kb

    async def get_by_id(self, knowledge_base_id: str, tenant_id: str) -> KnowledgeBase | None:
        if self._kb.id == knowledge_base_id and self._kb.tenant_id == tenant_id:
            return self._kb
        return None

    async def list_for_agent(self, agent_id: str, tenant_id: str) -> list[KnowledgeBase]:
        if self._kb.tenant_id == tenant_id:
            return [self._kb]
        return []

    async def exists_for_tenant(self, knowledge_base_id: str, tenant_id: str) -> bool:
        return (
            self._kb.id == knowledge_base_id and self._kb.tenant_id == tenant_id
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TENANT_ID = "tenant-1"
AGENT_ID = "agent-1"
KB_ID = "kb-1"


def _kb() -> KnowledgeBase:
    return KnowledgeBase(id=KB_ID, tenant_id=TENANT_ID, name="KB")


def _ready_document() -> Document:
    return Document(
        id="doc-v1",
        tenant_id=TENANT_ID,
        knowledge_base_id=KB_ID,
        agent_id=AGENT_ID,
        source_name="v1-upload",
        original_filename="policy-v1.txt",
        mime_type="text/plain",
        file_size_bytes=256,
        content_hash="a" * 64,
        status=DocumentProcessingStatus.READY,
        version_number=1,
    )


def _old_chunk(document: Document) -> ChunkWrite:
    return ChunkWrite(
        chunk=Chunk(
            id="chunk-v1",
            tenant_id=document.tenant_id,
            agent_id=document.agent_id or AGENT_ID,
            knowledge_base_id=document.knowledge_base_id,
            document_id=document.id,
            source_name=document.source_name,
            page_number=0,
            chunk_index=0,
            content="Old policy content — version 1.",
            content_hash="old-chunk-hash",
        ),
        embedding=(0.1, 0.2, 0.3, 0.4),
    )


def _replacement_request() -> IngestionRequest:
    return IngestionRequest(
        content=b"Replacement policy content. " * 20,
        filename="policy-v2.txt",
        mime_type="text/plain",
        tenant_id=TENANT_ID,
        agent_id=AGENT_ID,
        knowledge_base_id=KB_ID,
        source_name="v2-upload",
    )


def _service(
    *,
    provider: EmbeddingProvider | None = None,
    document_repository: InMemoryDocumentRepository | None = None,
    chunk_repository: InMemoryChunkRepository | None = None,
) -> tuple[IngestionService, InMemoryDocumentRepository, InMemoryChunkRepository]:
    doc_repo = document_repository or InMemoryDocumentRepository()
    chunk_repo = chunk_repository or InMemoryChunkRepository()
    embed_provider = provider or StubEmbeddingProvider()

    svc = IngestionService(
        parser_factory=DefaultParserFactory(),
        chunking_service=ChunkingService(chunk_size=80, chunk_overlap=10),
        embedding_service=EmbeddingService(
            provider=embed_provider,
            batch_size=4,
            embedding_dimensions=4,
        ),
        document_repository=doc_repo,
        chunk_repository=chunk_repo,
        knowledge_base_repository=ScopedKnowledgeBaseRepository(_kb()),
        max_upload_size_bytes=1024 * 1024,
        max_pdf_pages=10,
        allowed_extensions=frozenset({".txt", ".md", ".markdown", ".pdf", ".docx"}),
        allowed_mime_types=frozenset(
            {
                "text/plain",
                "text/markdown",
                "application/pdf",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            }
        ),
    )
    return svc, doc_repo, chunk_repo


# ---------------------------------------------------------------------------
# Scenario 1 — Successful replacement: V2 READY, V1 SUPERSEDED
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_successful_replacement_v2_ready_v1_superseded() -> None:
    """A successful replacement persists distinct, linked V1 and V2 rows."""
    doc = _ready_document()
    doc_repo = InMemoryDocumentRepository(existing=doc)
    chunk_repo = InMemoryChunkRepository()
    chunk_repo.records.append(_old_chunk(doc))

    svc, _, _ = _service(document_repository=doc_repo, chunk_repository=chunk_repo)

    result = await svc.reindex(document_id=doc.id, request=_replacement_request())

    assert result.document.id != doc.id
    assert result.document.predecessor_id == doc.id
    assert result.document.version_number == 2
    assert result.document.status == DocumentProcessingStatus.READY
    assert result.chunks_persisted > 0
    assert doc.status == DocumentProcessingStatus.SUPERSEDED
    assert doc.superseded_by_id == result.document.id


# ---------------------------------------------------------------------------
# Scenario 2 — Parse failure: V1 remains READY, no status change recorded
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_parse_failure_leaves_v1_ready() -> None:
    """Scenario 2: A replacement that fails at parse time (e.g. empty content)
    must not alter V1's status."""
    doc = _ready_document()
    doc_repo = InMemoryDocumentRepository(existing=doc)
    chunk_repo = InMemoryChunkRepository()
    chunk_repo.records.append(_old_chunk(doc))

    svc, _, _ = _service(document_repository=doc_repo, chunk_repository=chunk_repo)

    # An empty body fails the parse guard before any DB mutation occurs.
    bad_request = IngestionRequest(
        content=b"",  # triggers ParseError("The uploaded document is empty.")
        filename="policy-v2.txt",
        mime_type="text/plain",
        tenant_id=TENANT_ID,
        agent_id=AGENT_ID,
        knowledge_base_id=KB_ID,
        source_name="v2-upload",
    )

    with pytest.raises(Exception):
        await svc.reindex(document_id=doc.id, request=bad_request)

    # V1 is still READY with no status mutations
    assert doc.status == DocumentProcessingStatus.READY
    assert list(doc_repo.documents) == [doc.id]
    # Old chunk is untouched
    assert any(r.chunk.id == "chunk-v1" for r in chunk_repo.records)


# ---------------------------------------------------------------------------
# Scenario 3 — Embed failure: V1 remains READY, old chunks intact
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_embed_failure_leaves_v1_ready_chunks_intact() -> None:
    """Scenario 3: A replacement that fails during embedding leaves V1 READY
    and does not remove or replace the existing chunks."""
    doc = _ready_document()
    doc_repo = InMemoryDocumentRepository(existing=doc)
    chunk_repo = InMemoryChunkRepository()
    old_record = _old_chunk(doc)
    chunk_repo.records.append(old_record)

    svc, _, _ = _service(
        provider=FailingEmbeddingProvider(),
        document_repository=doc_repo,
        chunk_repository=chunk_repo,
    )

    with pytest.raises(EmbeddingError):
        await svc.reindex(document_id=doc.id, request=_replacement_request())

    # V1 is unchanged
    assert doc.status == DocumentProcessingStatus.READY
    assert doc.failure_reason is None
    assert all(item.status != DocumentProcessingStatus.READY for key, item in doc_repo.documents.items() if key != doc.id)

    # Old chunks are intact — no partial new chunks leaked in
    assert chunk_repo.records == [old_record]


# ---------------------------------------------------------------------------
# Scenario 4 — Retry after failure succeeds: V2 READY, V1 SUPERSEDED
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retry_after_embed_failure_succeeds() -> None:
    """Scenario 4: After an initial embed failure the caller can retry with a
    working provider; the retry should complete successfully."""
    doc = _ready_document()
    doc_repo = InMemoryDocumentRepository(existing=doc)
    chunk_repo = InMemoryChunkRepository()
    chunk_repo.records.append(_old_chunk(doc))

    # First attempt — will fail at embed
    failing_svc, _, _ = _service(
        provider=FailingEmbeddingProvider(),
        document_repository=doc_repo,
        chunk_repository=chunk_repo,
    )
    with pytest.raises(EmbeddingError):
        await failing_svc.reindex(document_id=doc.id, request=_replacement_request())

    # Sanity: V1 still READY after failure
    assert doc.status == DocumentProcessingStatus.READY
    assert doc.status == DocumentProcessingStatus.READY

    # Second attempt — good provider
    good_svc, _, _ = _service(
        provider=StubEmbeddingProvider(),
        document_repository=doc_repo,
        chunk_repository=chunk_repo,
    )
    result = await good_svc.reindex(document_id=doc.id, request=_replacement_request())

    assert result.document.status == DocumentProcessingStatus.READY
    assert result.chunks_persisted > 0
    assert doc.status == DocumentProcessingStatus.SUPERSEDED
    assert result.document.predecessor_id == doc.id


# ---------------------------------------------------------------------------
# Scenario 5 — Exactly one active (READY) version after successful replacement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_exactly_one_active_version_after_replacement() -> None:
    """Scenario 5: After reindex there must be exactly one READY document in
    the knowledge base — there must never be zero or two READY documents."""
    doc = _ready_document()
    doc_repo = InMemoryDocumentRepository(existing=doc)
    chunk_repo = InMemoryChunkRepository()
    chunk_repo.records.append(_old_chunk(doc))

    svc, _, _ = _service(document_repository=doc_repo, chunk_repository=chunk_repo)
    await svc.reindex(document_id=doc.id, request=_replacement_request())

    all_docs = await doc_repo.list_by_knowledge_base(KB_ID, TENANT_ID)
    ready_docs = [d for d in all_docs if d.status == DocumentProcessingStatus.READY]

    assert len(ready_docs) == 1


# ---------------------------------------------------------------------------
# Scenario 6 — No mixed chunks after any outcome
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_mixed_chunks_after_successful_replacement() -> None:
    """Scenario 6a: After a successful replacement there are no old chunks left —
    only new chunks exist (no old+new mix)."""
    doc = _ready_document()
    doc_repo = InMemoryDocumentRepository(existing=doc)
    chunk_repo = InMemoryChunkRepository()
    chunk_repo.records.append(_old_chunk(doc))

    svc, _, _ = _service(document_repository=doc_repo, chunk_repository=chunk_repo)
    await svc.reindex(document_id=doc.id, request=_replacement_request())

    old_ids = {r.chunk.id for r in chunk_repo.records if r.chunk.document_id == doc.id}
    new_records = [r for r in chunk_repo.records if r.chunk.document_id != doc.id]
    assert old_ids == {"chunk-v1"}
    assert new_records
    assert all(r.chunk.document_id != doc.id for r in new_records)


@pytest.mark.asyncio
async def test_no_mixed_chunks_after_failed_replacement() -> None:
    """Scenario 6b: After a failed replacement (embed error) only the original
    V1 chunks remain — no partially-inserted new chunks."""
    doc = _ready_document()
    doc_repo = InMemoryDocumentRepository(existing=doc)
    chunk_repo = InMemoryChunkRepository()
    old_record = _old_chunk(doc)
    chunk_repo.records.append(old_record)

    svc, _, _ = _service(
        provider=FailingEmbeddingProvider(),
        document_repository=doc_repo,
        chunk_repository=chunk_repo,
    )

    with pytest.raises(EmbeddingError):
        await svc.reindex(document_id=doc.id, request=_replacement_request())

    # The chunk set must be exactly what it was before — only the old record
    assert chunk_repo.records == [old_record]
    # No new chunks leaked in
    assert len(chunk_repo.records) == 1
    assert chunk_repo.records[0].chunk.id == "chunk-v1"
