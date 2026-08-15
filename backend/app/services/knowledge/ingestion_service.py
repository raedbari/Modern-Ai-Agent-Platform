"""Application service coordinating one complete document ingestion."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from backend.app.domain.exceptions import (
    DomainError,
    DocumentNotFoundError,
    EmbeddingError,
    KnowledgeBaseNotFoundError,
    ParseError,
    UnsupportedDocumentTypeError,
)
from backend.app.domain.models.chunk import Chunk
from backend.app.domain.models.document import Document
from backend.app.domain.models.enums import (
    DocumentProcessingStatus,
    KnowledgeBaseStatus,
)
from backend.app.domain.ports.parser import (
    ParsedDocument,
    ParserFactory,
    SupportedDocumentType,
)
from backend.app.domain.ports.repositories import (
    ChunkRepository,
    ChunkWrite,
    DocumentRepository,
    KnowledgeBaseRepository,
)
from backend.app.services.knowledge.chunking_service import ChunkingService
from backend.app.services.knowledge.embedding_service import EmbeddingService


@dataclass(frozen=True)
class IngestionRequest:
    """Validated-by-service input for one tenant-scoped upload."""

    content: bytes
    filename: str
    mime_type: str
    tenant_id: str
    agent_id: str
    knowledge_base_id: str
    source_name: str = "upload"


@dataclass(frozen=True)
class IngestionResult:
    """Outcome of ingestion or an idempotent duplicate upload."""

    document: Document
    chunks_persisted: int
    duplicate: bool = False


@dataclass(frozen=True)
class PreparedReindex:
    """Replacement chunks prepared without changing active knowledge."""

    content_hash: str
    mime_type: str
    records: tuple[ChunkWrite, ...]


class IngestionService:
    """Validate, parse, chunk, embed, and persist one uploaded document."""

    def __init__(
        self,
        *,
        parser_factory: ParserFactory,
        chunking_service: ChunkingService,
        embedding_service: EmbeddingService,
        document_repository: DocumentRepository,
        chunk_repository: ChunkRepository,
        knowledge_base_repository: KnowledgeBaseRepository,
        max_upload_size_bytes: int,
        max_pdf_pages: int,
        allowed_extensions: frozenset[str],
        allowed_mime_types: frozenset[str],
    ) -> None:
        if max_upload_size_bytes <= 0:
            raise ValueError("max_upload_size_bytes must be positive.")
        if max_pdf_pages <= 0:
            raise ValueError("max_pdf_pages must be positive.")
        self._parser_factory = parser_factory
        self._chunking_service = chunking_service
        self._embedding_service = embedding_service
        self._document_repository = document_repository
        self._chunk_repository = chunk_repository
        self._knowledge_base_repository = knowledge_base_repository
        self._max_upload_size_bytes = max_upload_size_bytes
        self._max_pdf_pages = max_pdf_pages
        self._allowed_extensions = {
            self._normalise_extension(value) for value in allowed_extensions
        }
        self._allowed_mime_types = {
            self._normalise_mime(value) for value in allowed_mime_types
        }

    async def ingest(self, request: IngestionRequest) -> IngestionResult:
        """Run the ingestion pipeline with tenant and agent authorization."""
        prepared = await self.prepare(request)
        if prepared.duplicate:
            return prepared

        extension, mime_type = self._validate_upload(request)
        document = prepared.document

        try:
            await self._set_status(
                document,
                DocumentProcessingStatus.PROCESSING,
            )
            records = await self._prepare_chunk_records(
                document=document,
                request=request,
                extension=extension,
                mime_type=mime_type,
            )
            persisted = await self._persist_all(records)

            await self._set_status(document, DocumentProcessingStatus.READY)
            return IngestionResult(
                document=document,
                chunks_persisted=len(persisted),
            )
        except Exception:
            await self._set_status(
                document,
                DocumentProcessingStatus.FAILED,
                failure_reason="Document processing failed.",
            )
            raise

    async def prepare(self, request: IngestionRequest) -> IngestionResult:
        """Validate and persist a pending document without processing it."""

        _, mime_type = self._validate_upload(request)
        await self._require_authorized_knowledge_base(request)

        content_hash = hashlib.sha256(request.content).hexdigest()
        existing = await self._document_repository.get_by_content_hash(
            content_hash=content_hash,
            tenant_id=request.tenant_id,
            knowledge_base_id=request.knowledge_base_id,
        )
        if existing is not None:
            return IngestionResult(
                document=existing,
                chunks_persisted=0,
                duplicate=True,
            )

        document = Document(
            id=str(uuid4()),
            tenant_id=request.tenant_id,
            knowledge_base_id=request.knowledge_base_id,
            agent_id=request.agent_id,
            source_name=request.source_name,
            original_filename=request.filename,
            mime_type=mime_type,
            file_size_bytes=len(request.content),
            content_hash=content_hash,
        )
        document = await self._document_repository.create(document)
        return IngestionResult(
            document=document,
            chunks_persisted=0,
            duplicate=False,
        )

    async def validate_reindex_target(
        self,
        *,
        document_id: str,
        request: IngestionRequest,
    ) -> Document:
        """Validate one replacement against current database state."""

        self._validate_upload(request)
        await self._require_authorized_knowledge_base(request)

        document = await self._document_repository.get_by_id(
            document_id=document_id,
            tenant_id=request.tenant_id,
        )

        if (
            document is None
            or document.knowledge_base_id
            != request.knowledge_base_id
            or document.agent_id != request.agent_id
        ):
            raise DocumentNotFoundError(
                "The document is unavailable for this agent."
            )

        content_hash = hashlib.sha256(request.content).hexdigest()

        duplicate = await self._document_repository.get_by_content_hash(
            content_hash=content_hash,
            tenant_id=request.tenant_id,
            knowledge_base_id=request.knowledge_base_id,
        )

        if duplicate is not None and duplicate.id != document.id:
            raise DomainError(
                "An identical document already exists "
                "in this knowledge base."
            )

        return document

    async def prepare_reindex(
        self,
        *,
        document: Document,
        request: IngestionRequest,
    ) -> PreparedReindex:
        """Parse, chunk, and embed without mutating active database rows."""

        extension, mime_type = self._validate_upload(request)

        if (
            document.tenant_id != request.tenant_id
            or document.knowledge_base_id
            != request.knowledge_base_id
            or document.agent_id != request.agent_id
        ):
            raise DocumentNotFoundError(
                "The document is unavailable for this agent."
            )

        records = await self._prepare_chunk_records(
            document=document,
            request=request,
            extension=extension,
            mime_type=mime_type,
        )

        return PreparedReindex(
            content_hash=hashlib.sha256(request.content).hexdigest(),
            mime_type=mime_type,
            records=tuple(records),
        )

    async def activate_prepared_reindex(
        self,
        *,
        document_id: str,
        request: IngestionRequest,
        prepared: PreparedReindex,
    ) -> IngestionResult:
        """Atomically replace active chunks after preparation succeeds."""

        _, mime_type = self._validate_upload(request)
        content_hash = hashlib.sha256(request.content).hexdigest()

        if (
            prepared.content_hash != content_hash
            or prepared.mime_type != mime_type
        ):
            raise DomainError(
                "Prepared replacement does not match the upload."
            )

        document = await self.validate_reindex_target(
            document_id=document_id,
            request=request,
        )

        expected_scope = (
            document.tenant_id,
            document.agent_id,
            document.knowledge_base_id,
            document.id,
        )

        for record in prepared.records:
            actual_scope = (
                record.chunk.tenant_id,
                record.chunk.agent_id,
                record.chunk.knowledge_base_id,
                record.chunk.document_id,
            )

            if actual_scope != expected_scope:
                raise DomainError(
                    "Prepared replacement chunk scope is invalid."
                )

        await self._chunk_repository.delete_by_document(
            document_id=document.id,
            tenant_id=document.tenant_id,
        )

        persisted = await self._persist_all(
            list(prepared.records)
        )

        document.source_name = request.source_name
        document.original_filename = request.filename
        document.mime_type = mime_type
        document.file_size_bytes = len(request.content)
        document.content_hash = content_hash
        document.status = DocumentProcessingStatus.READY
        document.failure_reason = None
        document.updated_at = datetime.now(timezone.utc)

        document = await self._document_repository.update(
            document
        )

        await self._set_status(
            document,
            DocumentProcessingStatus.READY,
        )

        return IngestionResult(
            document=document,
            chunks_persisted=len(persisted),
        )

    async def reindex(
        self,
        *,
        document_id: str,
        request: IngestionRequest,
    ) -> IngestionResult:
        """Prepare and activate a replacement.

        Transaction-sensitive callers should use the split prepare and
        activation methods so external embedding work occurs outside the
        final write transaction.
        """

        document = await self.validate_reindex_target(
            document_id=document_id,
            request=request,
        )

        prepared = await self.prepare_reindex(
            document=document,
            request=request,
        )

        return await self.activate_prepared_reindex(
            document_id=document_id,
            request=request,
            prepared=prepared,
        )

    async def _prepare_chunk_records(
        self,
        *,
        document: Document,
        request: IngestionRequest,
        extension: str,
        mime_type: str,
    ) -> list[ChunkWrite]:
        parser = self._parser_factory.get_parser(
            mime_type=mime_type,
            extension=extension,
        )
        parsed = await parser.parse(request.content, request.filename)
        self._enforce_pdf_page_limit(parsed)

        chunks = self._chunking_service.chunk_document(
            parsed,
            document_id=document.id,
            tenant_id=request.tenant_id,
            agent_id=request.agent_id,
            knowledge_base_id=request.knowledge_base_id,
            source_name=request.source_name,
        )
        embedding_result = await self._embedding_service.embed_chunks(chunks)
        if embedding_result.has_failures:
            raise EmbeddingError(
                "One or more chunks could not be embedded."
            )
        return [
            ChunkWrite(
                chunk=embedded.chunk,
                embedding=tuple(embedded.embedding),
            )
            for embedded in embedding_result.embedded
        ]

    async def _persist_all(
        self,
        records: list[ChunkWrite],
    ) -> list[Chunk]:
        persisted = await self._chunk_repository.create_many(records)
        if len(persisted) != len(records):
            raise DomainError(
                "The chunk repository did not persist every record."
            )
        return persisted

    def _validate_upload(
        self,
        request: IngestionRequest,
    ) -> tuple[str, str]:
        for field_name, value in (
            ("filename", request.filename),
            ("mime_type", request.mime_type),
            ("tenant_id", request.tenant_id),
            ("agent_id", request.agent_id),
            ("knowledge_base_id", request.knowledge_base_id),
            ("source_name", request.source_name),
        ):
            if not value or not value.strip():
                raise ValueError(f"{field_name} must not be empty.")
        if not request.content:
            raise ParseError("The uploaded document is empty.")
        if len(request.content) > self._max_upload_size_bytes:
            raise ParseError("The uploaded document exceeds the size limit.")

        extension = self._normalise_extension(Path(request.filename).suffix)
        mime_type = self._normalise_mime(request.mime_type)
        if extension not in self._allowed_extensions:
            raise UnsupportedDocumentTypeError(
                mime_type=mime_type,
                extension=extension,
            )
        if mime_type not in self._allowed_mime_types:
            raise UnsupportedDocumentTypeError(
                mime_type=mime_type,
                extension=extension,
            )

        # The factory rejects a known extension paired with an incompatible
        # MIME type before any parser handles attacker-controlled bytes.
        self._parser_factory.get_parser(
            mime_type=mime_type,
            extension=extension,
        )
        return extension, mime_type

    async def _require_authorized_knowledge_base(
        self,
        request: IngestionRequest,
    ) -> None:
        knowledge_bases = (
            await self._knowledge_base_repository.list_for_agent(
                agent_id=request.agent_id,
                tenant_id=request.tenant_id,
            )
        )
        authorized = any(
            knowledge_base.id == request.knowledge_base_id
            and knowledge_base.tenant_id == request.tenant_id
            and knowledge_base.status == KnowledgeBaseStatus.ACTIVE
            for knowledge_base in knowledge_bases
        )
        if not authorized:
            raise KnowledgeBaseNotFoundError(
                "The knowledge base is unavailable for this agent."
            )

    def _enforce_pdf_page_limit(
        self,
        parsed_document: ParsedDocument,
    ) -> None:
        if (
            parsed_document.document_type == SupportedDocumentType.PDF
            and len(parsed_document.pages) > self._max_pdf_pages
        ):
            raise ParseError("The PDF exceeds the configured page limit.")

    async def _set_status(
        self,
        document: Document,
        status: DocumentProcessingStatus,
        failure_reason: str | None = None,
    ) -> None:
        await self._document_repository.update_processing_status(
            document_id=document.id,
            tenant_id=document.tenant_id,
            status=status,
            failure_reason=failure_reason,
        )
        document.status = status
        document.failure_reason = failure_reason

    @staticmethod
    def _normalise_extension(extension: str) -> str:
        value = extension.strip().lower()
        if value and not value.startswith("."):
            value = f".{value}"
        return value

    @staticmethod
    def _normalise_mime(mime_type: str) -> str:
        return mime_type.split(";", 1)[0].strip().lower()
