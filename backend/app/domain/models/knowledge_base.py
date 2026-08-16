"""KnowledgeBase domain model.

A KnowledgeBase is a curated collection of documents belonging to a tenant.
One or more Agents may reference a KnowledgeBase, but retrieval is always
scoped to the specific agent making the request to prevent cross-agent
data leakage.
"""

from dataclasses import dataclass
from typing import ClassVar

from backend.app.domain.models.enums import KnowledgeBaseStatus


@dataclass
class KnowledgeBase:
    """A tenant-owned collection of documents available to one or more agents.

    Attributes:
        id:             Unique, opaque identifier (UUID string).
        tenant_id:      Identifier of the owning Tenant.
        name:           Short human-readable label for the collection.
        description:    Optional longer description of the collection's purpose.
        status:         Current operational state of the knowledge base.
        classification: Data sensitivity level. One of "public", "internal",
                        or "restricted". Defaults to "internal".
    """

    _VALID_CLASSIFICATIONS: ClassVar[frozenset[str]] = frozenset({"public", "internal", "restricted"})

    id: str
    tenant_id: str
    name: str
    description: str = ""
    status: KnowledgeBaseStatus = KnowledgeBaseStatus.ACTIVE
    classification: str = "internal"

    def __post_init__(self) -> None:
        """Validate invariants that must hold for every KnowledgeBase instance."""
        if not self.id or not self.id.strip():
            raise ValueError("KnowledgeBase.id must not be empty.")
        if not self.tenant_id or not self.tenant_id.strip():
            raise ValueError("KnowledgeBase.tenant_id must not be empty.")
        if not self.name or not self.name.strip():
            raise ValueError("KnowledgeBase.name must not be empty.")
        if self.classification not in self._VALID_CLASSIFICATIONS:
            raise ValueError(
                f"KnowledgeBase.classification must be one of "
                f"{sorted(self._VALID_CLASSIFICATIONS)}, got {self.classification!r}."
            )
