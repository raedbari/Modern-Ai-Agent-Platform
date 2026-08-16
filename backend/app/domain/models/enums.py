"""Domain enumerations shared across domain models."""

from enum import Enum


class DocumentProcessingStatus(str, Enum):
    """Lifecycle states for a Document moving through the ingestion pipeline.

    Values are intentionally lowercase strings so they serialise naturally
    to JSON without any extra conversion at the API boundary.

    States (6 total):
    - PENDING    : document has been accepted and is queued for ingestion.
    - PROCESSING : ingestion pipeline is actively parsing, chunking, and embedding.
    - READY      : ingestion complete; document is active and available for retrieval.
    - FAILED     : ingestion encountered an unrecoverable error.
    - SUPERSEDED : a newer version of this document has been atomically reindexed;
                   this version is no longer served for retrieval but is retained for
                   audit and rollback purposes.
    - ARCHIVED   : document has been soft-deleted or explicitly archived by a
                   tenant administrator; excluded from retrieval and normal listings.
    """

    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    SUPERSEDED = "superseded"
    ARCHIVED = "archived"


class KnowledgeBaseStatus(str, Enum):
    """Operational states for a KnowledgeBase.

    - ACTIVE   : accepting document ingestion and retrieval requests.
    - INACTIVE : visible to the tenant but not serving retrieval requests.
    """

    ACTIVE = "active"
    INACTIVE = "inactive"
