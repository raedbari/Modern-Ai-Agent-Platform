"""Document domain model.

A Document represents a single file that has been uploaded by a tenant and
is being processed (or has been processed) for ingestion into a KnowledgeBase.
It tracks the full lifecycle from upload through chunking and embedding.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone

from backend.app.domain.models.enums import DocumentProcessingStatus


@dataclass
class Document:
    """A file uploaded by a tenant that is ingested into a KnowledgeBase.

    Multi-tenant isolation: every query and mutation that touches a Document
    must filter by both tenant_id and knowledge_base_id.

    Attributes:
        id:                Unique, opaque identifier (UUID string).
        tenant_id:         Identifier of the owning Tenant.
        knowledge_base_id: Identifier of the target KnowledgeBase.
        agent_id:          Identifier of the Agent this document was uploaded
                           for, when the upload was initiated in the context of
                           a specific agent.  Optional — a document may be
                           associated with a KnowledgeBase directly without
                           going through an agent.
        source_name:       Logical source label (e.g. URL, system name).
        original_filename: Original name of the uploaded file.
        mime_type:         MIME type of the uploaded file (e.g. "application/pdf").
        file_size_bytes:   Size of the uploaded file in bytes.
        content_hash:      xxHash or SHA-256 hex digest of the raw file content
                           used for deduplication.
        status:            Current processing state of the document.
        failure_reason:    Safe, human-readable message explaining why processing
                           failed.  Must never contain raw exception traces or
                           internal infrastructure details.
        version_number:    Monotonically increasing integer starting at 1.
                           Incremented each time the document is reindexed.
        superseded_by_id:  ID of the Document that replaces this one, when this
                           document has been superseded by a newer version.
                           None while this is the current version.
        created_by:        Identifier of the user or system that created this
                           document record (optional).
        created_at:        UTC timestamp of record creation.
        updated_at:        UTC timestamp of the last status change.
    """

    id: str
    tenant_id: str
    knowledge_base_id: str
    source_name: str
    original_filename: str
    mime_type: str
    file_size_bytes: int
    content_hash: str
    agent_id: str | None = None
    status: DocumentProcessingStatus = DocumentProcessingStatus.PENDING
    failure_reason: str | None = None
    version_number: int = 1
    version_family_id: str | None = None
    predecessor_id: str | None = None
    superseded_by_id: str | None = None
    created_by: str | None = None
    created_at: datetime = field(
        default_factory=lambda: datetime.now(tz=timezone.utc)
    )
    updated_at: datetime = field(
        default_factory=lambda: datetime.now(tz=timezone.utc)
    )

    def __post_init__(self) -> None:
        """Validate invariants that must hold for every Document instance."""
        if not self.id or not self.id.strip():
            raise ValueError("Document.id must not be empty.")
        if not self.tenant_id or not self.tenant_id.strip():
            raise ValueError("Document.tenant_id must not be empty.")
        if not self.knowledge_base_id or not self.knowledge_base_id.strip():
            raise ValueError("Document.knowledge_base_id must not be empty.")
        if not self.source_name or not self.source_name.strip():
            raise ValueError("Document.source_name must not be empty.")
        if not self.original_filename or not self.original_filename.strip():
            raise ValueError("Document.original_filename must not be empty.")
        if not self.mime_type or not self.mime_type.strip():
            raise ValueError("Document.mime_type must not be empty.")
        if self.file_size_bytes < 0:
            raise ValueError(
                f"Document.file_size_bytes must be non-negative, "
                f"got {self.file_size_bytes}."
            )
        if not self.content_hash or not self.content_hash.strip():
            raise ValueError("Document.content_hash must not be empty.")
        if self.agent_id is not None and not self.agent_id.strip():
            raise ValueError(
                "Document.agent_id must be None or a non-empty string."
            )
        if self.version_number < 1:
            raise ValueError(
                f"Document.version_number must be >= 1, got {self.version_number}."
            )
        if self.version_family_id is None:
            self.version_family_id = self.id
        if not self.version_family_id.strip():
            raise ValueError("Document.version_family_id must not be empty.")
        if self.predecessor_id is not None and not self.predecessor_id.strip():
            raise ValueError("Document.predecessor_id must be non-empty when set.")
        if self.superseded_by_id is not None and not self.superseded_by_id.strip():
            raise ValueError(
                "Document.superseded_by_id must be None or a non-empty string."
            )
