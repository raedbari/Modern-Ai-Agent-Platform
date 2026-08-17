"""Chunk domain model.

A Chunk is a fixed-size text segment extracted from a Document during the
ingestion pipeline.  Each chunk is independently embedded and stored in the
vector store for similarity-based retrieval.

Retrieval must always filter by tenant_id, agent_id, and knowledge_base_id
before applying any similarity ranking.  This is enforced at the repository
and service layers; the domain model carries the identifiers required for
those checks.
"""

from dataclasses import dataclass


@dataclass
class Chunk:
    """A text segment extracted from a Document and prepared for retrieval.

    Attributes:
        id:                Unique, opaque identifier (UUID string).
        tenant_id:         Identifier of the owning Tenant.
        agent_id:          Identifier of the Agent this chunk belongs to.
        knowledge_base_id: Identifier of the KnowledgeBase this chunk is part of.
        document_id:       Identifier of the parent Document.
        source_name:       Logical source label inherited from the parent Document.
        page_number:       0-based page index within the source file.
                           Use 0 for non-paginated formats (plain text, HTML).
        chunk_index:       0-based position of this chunk within the document.
        content:           Raw text content of this chunk.
        content_hash:      Hash of the content field used for deduplication.
    """

    id: str
    tenant_id: str
    agent_id: str | None
    knowledge_base_id: str
    document_id: str
    source_name: str
    page_number: int
    chunk_index: int
    content: str
    content_hash: str

    def __post_init__(self) -> None:
        """Validate invariants that must hold for every Chunk instance."""
        if not self.id or not self.id.strip():
            raise ValueError("Chunk.id must not be empty.")
        if not self.tenant_id or not self.tenant_id.strip():
            raise ValueError("Chunk.tenant_id must not be empty.")
        if self.agent_id is not None and not self.agent_id.strip():
            raise ValueError("Chunk.agent_id must be non-empty when set.")
        if not self.knowledge_base_id or not self.knowledge_base_id.strip():
            raise ValueError("Chunk.knowledge_base_id must not be empty.")
        if not self.document_id or not self.document_id.strip():
            raise ValueError("Chunk.document_id must not be empty.")
        if not self.source_name or not self.source_name.strip():
            raise ValueError("Chunk.source_name must not be empty.")
        if self.page_number < 0:
            raise ValueError(
                f"Chunk.page_number must be non-negative, got {self.page_number}."
            )
        if self.chunk_index < 0:
            raise ValueError(
                f"Chunk.chunk_index must be non-negative, got {self.chunk_index}."
            )
        if not self.content or not self.content.strip():
            raise ValueError("Chunk.content must not be empty.")
        if not self.content_hash or not self.content_hash.strip():
            raise ValueError("Chunk.content_hash must not be empty.")
