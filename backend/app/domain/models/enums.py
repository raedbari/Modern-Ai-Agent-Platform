"""Domain enumerations shared across domain models."""

from enum import Enum


class DocumentProcessingStatus(str, Enum):
    """Lifecycle states for a Document moving through the ingestion pipeline.

    Values are intentionally lowercase strings so they serialise naturally
    to JSON without any extra conversion at the API boundary.
    """

    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class KnowledgeBaseStatus(str, Enum):
    """Operational states for a KnowledgeBase.

    - ACTIVE   : accepting document ingestion and retrieval requests.
    - INACTIVE : visible to the tenant but not serving retrieval requests.
    """

    ACTIVE = "active"
    INACTIVE = "inactive"
