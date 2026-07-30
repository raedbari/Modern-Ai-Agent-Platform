"""Repository port interfaces for the Knowledge RAG Pipeline.

Each interface defines the persistence contract that the service layer depends
on.  Infrastructure implementations (SQLAlchemy, in-memory, etc.) must satisfy
these contracts without the domain layer knowing anything about them.

Rules enforced at this layer:
- Every method that touches tenant-owned data accepts ``tenant_id`` as an
  explicit parameter so callers cannot accidentally omit the isolation scope.
- No ORM types, no database sessions, no framework imports.
- All methods are declared async — the platform uses an async database driver.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from backend.app.domain.models.chunk import Chunk
from backend.app.domain.models.document import Document
from backend.app.domain.models.enums import DocumentProcessingStatus
from backend.app.domain.models.knowledge_base import KnowledgeBase


@dataclass(frozen=True)
class ChunkWrite:
    """One chunk and its vector, persisted atomically by a repository."""

    chunk: Chunk
    embedding: tuple[float, ...]


# ---------------------------------------------------------------------------
# DocumentRepository
# ---------------------------------------------------------------------------


class DocumentRepository(ABC):
    """Persistence contract for Document entities.

    Implementations must enforce tenant isolation on every operation.
    """

    @abstractmethod
    async def create(self, document: Document) -> Document:
        """Persist a new Document and return the saved instance.

        Args:
            document: A fully constructed ``Document`` domain entity.

        Returns:
            The persisted ``Document``, identical to the input in the common
            case but may carry any persistence-layer–generated fields.
        """

    @abstractmethod
    async def update(self, document: Document) -> Document:
        """Replace the persisted state of an existing Document.

        Args:
            document: The ``Document`` entity carrying updated field values.
                      The ``id`` and ``tenant_id`` fields are used to locate
                      the existing record.

        Returns:
            The updated ``Document`` as reflected by the persistence layer.

        Raises:
            DocumentNotFoundError: When no document with the given ``id``
                exists for the given ``tenant_id``.
        """

    @abstractmethod
    async def get_by_id(
        self,
        document_id: str,
        tenant_id: str,
    ) -> Document | None:
        """Retrieve a Document by its identifier within a tenant scope.

        Args:
            document_id: Unique identifier of the target document.
            tenant_id:   Identifier of the owning tenant.

        Returns:
            The matching ``Document``, or ``None`` when not found.
        """

    @abstractmethod
    async def get_by_content_hash(
        self,
        content_hash: str,
        tenant_id: str,
        knowledge_base_id: str,
    ) -> Document | None:
        """Look up an existing Document by its content hash.

        Used by the ingestion pipeline to detect duplicate uploads before
        starting expensive processing.

        Args:
            content_hash:      Hash of the raw file bytes.
            tenant_id:         Identifier of the owning tenant.
            knowledge_base_id: Scope the lookup to a specific KnowledgeBase.

        Returns:
            The matching ``Document``, or ``None`` when not found.
        """

    @abstractmethod
    async def list_by_knowledge_base(
        self,
        knowledge_base_id: str,
        tenant_id: str,
    ) -> list[Document]:
        """Return all Documents belonging to a KnowledgeBase.

        Args:
            knowledge_base_id: Identifier of the target KnowledgeBase.
            tenant_id:         Identifier of the owning tenant.

        Returns:
            A list of ``Document`` entities, which may be empty.
        """

    @abstractmethod
    async def update_processing_status(
        self,
        document_id: str,
        tenant_id: str,
        status: DocumentProcessingStatus,
        failure_reason: str | None = None,
    ) -> None:
        """Update only the processing status of a Document.

        This targeted mutation avoids loading the full entity for a simple
        status transition, which is the most frequent write during ingestion.

        Args:
            document_id:    Identifier of the target document.
            tenant_id:      Identifier of the owning tenant.
            status:         The new ``DocumentProcessingStatus`` value.
            failure_reason: Optional human-readable explanation for a
                            ``FAILED`` transition.  Must never contain raw
                            exception traces or infrastructure details.
        """


# ---------------------------------------------------------------------------
# ChunkRepository
# ---------------------------------------------------------------------------


class ChunkRepository(ABC):
    """Persistence contract for Chunk entities.

    Implementations must enforce tenant and agent isolation on every
    operation, including vector similarity search.
    """

    @abstractmethod
    async def create_many(self, records: list[ChunkWrite]) -> list[Chunk]:
        """Persist chunks and their embeddings in a single operation.

        Bulk insertion is preferred over individual ``create`` calls because
        a single document can produce hundreds of chunks.

        Args:
            records: Fully constructed chunks paired with their vectors.
                     All records must belong to the same tenant and agent.

        Returns:
            The list of persisted ``Chunk`` entities.
        """

    @abstractmethod
    async def delete_by_document(
        self,
        document_id: str,
        tenant_id: str,
    ) -> int:
        """Delete all Chunks associated with a Document.

        Called when a Document is deleted or re-ingested so that stale
        chunks and their embeddings are removed before new ones are inserted.

        Args:
            document_id: Identifier of the parent document.
            tenant_id:   Identifier of the owning tenant.

        Returns:
            The number of Chunk records deleted.
        """

    @abstractmethod
    async def list_by_document(
        self,
        document_id: str,
        tenant_id: str,
    ) -> list[Chunk]:
        """Return all Chunks belonging to a Document, ordered by chunk_index.

        Args:
            document_id: Identifier of the parent document.
            tenant_id:   Identifier of the owning tenant.

        Returns:
            An ordered list of ``Chunk`` entities, which may be empty.
        """

    @abstractmethod
    async def semantic_search(
        self,
        query_embedding: list[float],
        tenant_id: str,
        agent_id: str,
        knowledge_base_id: str,
        top_k: int,
        min_similarity: float,
    ) -> list[tuple[Chunk, float]]:
        """Search for Chunks semantically similar to a query embedding.

        Isolation contract: implementations MUST apply ``tenant_id``,
        ``agent_id``, and ``knowledge_base_id`` filters BEFORE ranking by
        similarity.  A chunk that belongs to a different tenant or agent must
        never appear in the results regardless of its similarity score.

        Args:
            query_embedding:   Dense vector representation of the query text.
            tenant_id:         Scope results to this tenant.
            agent_id:          Scope results to this agent.
            knowledge_base_id: Scope results to this knowledge base.
            top_k:             Maximum number of results to return.
            min_similarity:    Minimum cosine similarity threshold (0.0–1.0).
                               Chunks below this threshold are excluded.

        Returns:
            A list of ``(Chunk, similarity_score)`` pairs, ordered by
            descending similarity score.  May be empty.
        """


# ---------------------------------------------------------------------------
# KnowledgeBaseRepository
# ---------------------------------------------------------------------------


class KnowledgeBaseRepository(ABC):
    """Persistence contract for KnowledgeBase entities."""

    @abstractmethod
    async def get_by_id(
        self,
        knowledge_base_id: str,
        tenant_id: str,
    ) -> KnowledgeBase | None:
        """Retrieve a KnowledgeBase by its identifier within a tenant scope.

        Args:
            knowledge_base_id: Unique identifier of the target knowledge base.
            tenant_id:         Identifier of the owning tenant.

        Returns:
            The matching ``KnowledgeBase``, or ``None`` when not found.
        """

    @abstractmethod
    async def list_for_agent(
        self,
        agent_id: str,
        tenant_id: str,
    ) -> list[KnowledgeBase]:
        """Return all KnowledgeBases associated with a given Agent.

        Used by the retrieval service to resolve which knowledge bases are
        in scope for a given conversation.

        Args:
            agent_id:  Identifier of the requesting agent.
            tenant_id: Identifier of the owning tenant.

        Returns:
            A list of ``KnowledgeBase`` entities, which may be empty.
        """

    @abstractmethod
    async def exists_for_tenant(
        self,
        knowledge_base_id: str,
        tenant_id: str,
    ) -> bool:
        """Check whether a KnowledgeBase exists and belongs to a tenant.

        Preferred over ``get_by_id`` when only existence needs to be verified
        (e.g., during upload validation) to avoid loading the full entity.

        Args:
            knowledge_base_id: Identifier of the target knowledge base.
            tenant_id:         Identifier of the owning tenant.

        Returns:
            ``True`` if the knowledge base exists for the given tenant,
            ``False`` otherwise.
        """
