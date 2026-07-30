"""Tests for the complete application-layer ingestion coordinator."""

from __future__ import annotations

import io
from dataclasses import replace

import pytest

from backend.app.ai.contracts import (
    EmbeddingRequest,
    EmbeddingResult as ProviderEmbeddingResult,
)
from backend.app.ai.ports import EmbeddingProvider
from backend.app.domain.exceptions import (
    EmbeddingError,
    KnowledgeBaseNotFoundError,
    ParseError,
    UnsupportedDocumentTypeError,
)
from backend.app.domain.models.chunk import Chunk
from backend.app.domain.models.document import Document
from backend.app.domain.models.enums import (
    DocumentProcessingStatus,
)
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


class StubEmbeddingProvider(EmbeddingProvider):
    def __init__(self, *, dimension: int = 4) -> None:
        self.dimension = dimension
        self.requests: list[EmbeddingRequest] = []

    async def embed(
        self,
        request: EmbeddingRequest,
    ) -> ProviderEmbeddingResult:
        self.requests.append(request)
        return ProviderEmbeddingResult(
            embeddings=[
                [0.25] * self.dimension for _ in request.texts
            ],
            model="test-embedding",
            dimension=self.dimension,
        )


class WrongDimensionProvider(EmbeddingProvider):
    async def embed(
        self,
        request: EmbeddingRequest,
    ) -> ProviderEmbeddingResult:
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

    async def get_by_id(
        self,
        document_id: str,
        tenant_id: str,
    ) -> Document | None:
        document = self.documents.get(document_id)
        if document is not None and document.tenant_id == tenant_id:
            return document
        return None

    async def get_by_content_hash(
        self,
        content_hash: str,
        tenant_id: str,
        knowledge_base_id: str,
    ) -> Document | None:
        return next(
            (
                document
                for document in self.documents.values()
                if document.content_hash == content_hash
                and document.tenant_id == tenant_id
                and document.knowledge_base_id == knowledge_base_id
            ),
            None,
        )

    async def list_by_knowledge_base(
        self,
        knowledge_base_id: str,
        tenant_id: str,
    ) -> list[Document]:
        return [
            document
            for document in self.documents.values()
            if document.knowledge_base_id == knowledge_base_id
            and document.tenant_id == tenant_id
        ]

    async def update_processing_status(
        self,
        document_id: str,
        tenant_id: str,
        status: DocumentProcessingStatus,
        failure_reason: str | None = None,
    ) -> None:
        document = await self.get_by_id(document_id, tenant_id)
        assert document is not None
        document.status = status
        document.failure_reason = failure_reason
        self.statuses.append(status)


class InMemoryChunkRepository(ChunkRepository):
    def __init__(self) -> None:
        self.records: list[ChunkWrite] = []

    async def create_many(
        self,
        records: list[ChunkWrite],
    ) -> list[Chunk]:
        self.records.extend(records)
        return [record.chunk for record in records]

    async def delete_by_document(
        self,
        document_id: str,
        tenant_id: str,
    ) -> int:
        before = len(self.records)
        self.records = [
            record
            for record in self.records
            if not (
                record.chunk.document_id == document_id
                and record.chunk.tenant_id == tenant_id
            )
        ]
        return before - len(self.records)

    async def list_by_document(
        self,
        document_id: str,
        tenant_id: str,
    ) -> list[Chunk]:
        return [
            record.chunk
            for record in self.records
            if record.chunk.document_id == document_id
            and record.chunk.tenant_id == tenant_id
        ]

    async def semantic_search(self, **kwargs) -> list[tuple[Chunk, float]]:
        return []


class ScopedKnowledgeBaseRepository(KnowledgeBaseRepository):
    def __init__(
        self,
        assignments: dict[tuple[str, str], list[KnowledgeBase]],
    ) -> None:
        self.assignments = assignments

    async def get_by_id(
        self,
        knowledge_base_id: str,
        tenant_id: str,
    ) -> KnowledgeBase | None:
        for knowledge_bases in self.assignments.values():
            for knowledge_base in knowledge_bases:
                if (
                    knowledge_base.id == knowledge_base_id
                    and knowledge_base.tenant_id == tenant_id
                ):
                    return knowledge_base
        return None

    async def list_for_agent(
        self,
        agent_id: str,
        tenant_id: str,
    ) -> list[KnowledgeBase]:
        return list(self.assignments.get((tenant_id, agent_id), []))

    async def exists_for_tenant(
        self,
        knowledge_base_id: str,
        tenant_id: str,
    ) -> bool:
        return (
            await self.get_by_id(knowledge_base_id, tenant_id)
        ) is not None


def _knowledge_base(
    *,
    knowledge_base_id: str = "kb-1",
    tenant_id: str = "tenant-1",
) -> KnowledgeBase:
    return KnowledgeBase(
        id=knowledge_base_id,
        tenant_id=tenant_id,
        name="Knowledge",
    )


def _request(**overrides) -> IngestionRequest:
    request = IngestionRequest(
        content=b"Return policy information. " * 20,
        filename="policy.txt",
        mime_type="text/plain",
        tenant_id="tenant-1",
        agent_id="agent-1",
        knowledge_base_id="kb-1",
    )
    return replace(request, **overrides)


def _service(
    *,
    provider: EmbeddingProvider | None = None,
    document_repository: InMemoryDocumentRepository | None = None,
    chunk_repository: InMemoryChunkRepository | None = None,
    kb_repository: ScopedKnowledgeBaseRepository | None = None,
    max_upload_size_bytes: int = 1024 * 1024,
    max_pdf_pages: int = 10,
) -> tuple[
    IngestionService,
    InMemoryDocumentRepository,
    InMemoryChunkRepository,
    EmbeddingProvider,
]:
    document_repository = (
        document_repository or InMemoryDocumentRepository()
    )
    chunk_repository = chunk_repository or InMemoryChunkRepository()
    provider = provider or StubEmbeddingProvider()
    kb_repository = kb_repository or ScopedKnowledgeBaseRepository(
        {
            ("tenant-1", "agent-1"): [_knowledge_base()],
        }
    )
    service = IngestionService(
        parser_factory=DefaultParserFactory(),
        chunking_service=ChunkingService(
            chunk_size=80,
            chunk_overlap=10,
        ),
        embedding_service=EmbeddingService(
            provider=provider,
            batch_size=4,
            embedding_dimensions=4,
        ),
        document_repository=document_repository,
        chunk_repository=chunk_repository,
        knowledge_base_repository=kb_repository,
        max_upload_size_bytes=max_upload_size_bytes,
        max_pdf_pages=max_pdf_pages,
        allowed_extensions=frozenset(
            {".txt", ".md", ".markdown", ".pdf", ".docx"}
        ),
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
    return service, document_repository, chunk_repository, provider


@pytest.mark.asyncio
async def test_success_persists_chunks_with_embeddings() -> None:
    service, documents, chunks, provider = _service()

    result = await service.ingest(_request())

    assert result.document.status == DocumentProcessingStatus.READY
    assert result.chunks_persisted == len(chunks.records) > 0
    assert all(len(record.embedding) == 4 for record in chunks.records)
    assert documents.statuses == [
        DocumentProcessingStatus.PROCESSING,
        DocumentProcessingStatus.READY,
    ]
    assert isinstance(provider, StubEmbeddingProvider)
    assert provider.requests
    assert all(
        request.context.tenant_id == "tenant-1"
        and request.context.agent_id == "agent-1"
        for request in provider.requests
    )


@pytest.mark.asyncio
async def test_duplicate_upload_is_idempotent() -> None:
    service, documents, chunks, provider = _service()
    first = await service.ingest(_request())
    initial_create_calls = documents.create_calls
    initial_provider_calls = len(provider.requests)  # type: ignore[attr-defined]

    duplicate = await service.ingest(_request())

    assert duplicate.duplicate
    assert duplicate.document.id == first.document.id
    assert duplicate.chunks_persisted == 0
    assert documents.create_calls == initial_create_calls
    assert len(provider.requests) == initial_provider_calls  # type: ignore[attr-defined]
    assert len(chunks.records) == first.chunks_persisted


@pytest.mark.asyncio
async def test_unauthorized_agent_cannot_ingest_to_knowledge_base() -> None:
    kb_repository = ScopedKnowledgeBaseRepository(
        {
            ("tenant-1", "agent-1"): [_knowledge_base()],
            ("tenant-1", "agent-2"): [],
        }
    )
    service, documents, chunks, _ = _service(
        kb_repository=kb_repository
    )

    with pytest.raises(KnowledgeBaseNotFoundError):
        await service.ingest(_request(agent_id="agent-2"))

    assert documents.create_calls == 0
    assert chunks.records == []


@pytest.mark.asyncio
async def test_cross_tenant_knowledge_base_is_rejected() -> None:
    kb_repository = ScopedKnowledgeBaseRepository(
        {
            ("tenant-2", "agent-1"): [
                _knowledge_base(tenant_id="tenant-2")
            ],
        }
    )
    service, documents, _, _ = _service(
        kb_repository=kb_repository
    )

    with pytest.raises(KnowledgeBaseNotFoundError):
        await service.ingest(_request())

    assert documents.create_calls == 0


@pytest.mark.asyncio
async def test_mime_extension_mismatch_is_rejected() -> None:
    service, documents, _, _ = _service()

    with pytest.raises(UnsupportedDocumentTypeError):
        await service.ingest(
            _request(filename="renamed.txt", mime_type="application/pdf")
        )

    assert documents.create_calls == 0


@pytest.mark.asyncio
async def test_upload_size_limit_is_enforced_before_persistence() -> None:
    service, documents, _, _ = _service(max_upload_size_bytes=10)

    with pytest.raises(ParseError, match="size limit"):
        await service.ingest(_request(content=b"x" * 11))

    assert documents.create_calls == 0


@pytest.mark.asyncio
async def test_pdf_page_limit_marks_document_failed() -> None:
    from pypdf import PdfWriter

    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    writer.add_blank_page(width=612, height=792)
    buffer = io.BytesIO()
    writer.write(buffer)

    service, documents, _, _ = _service(max_pdf_pages=1)

    with pytest.raises(ParseError, match="page limit"):
        await service.ingest(
            _request(
                content=buffer.getvalue(),
                filename="two-pages.pdf",
                mime_type="application/pdf",
            )
        )

    assert documents.statuses == [
        DocumentProcessingStatus.PROCESSING,
        DocumentProcessingStatus.FAILED,
    ]


@pytest.mark.asyncio
async def test_embedding_failure_marks_document_failed() -> None:
    service, documents, chunks, _ = _service(
        provider=WrongDimensionProvider()
    )

    with pytest.raises(EmbeddingError):
        await service.ingest(_request())

    assert documents.statuses == [
        DocumentProcessingStatus.PROCESSING,
        DocumentProcessingStatus.FAILED,
    ]
    assert chunks.records == []
    document = next(iter(documents.documents.values()))
    assert document.failure_reason == "Document processing failed."
