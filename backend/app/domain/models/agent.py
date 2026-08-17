"""Agent domain model.

An Agent is an AI assistant configured by a tenant for a specific business
purpose.  It is associated with one or more KnowledgeBases that define the
information it is allowed to retrieve and reason over.
"""

from dataclasses import dataclass, field


@dataclass
class Agent:
    """A tenant-owned AI assistant with a defined scope and knowledge sources.

    Relationships are expressed as plain identifier sets, not ORM references,
    keeping the domain layer persistence-agnostic.

    Attributes:
        id:                 Unique, opaque identifier (UUID string).
        tenant_id:          Identifier of the owning Tenant.
        prompt_version:     Prompt version identifier (default: "v1").
                            Used for evaluation tracking and A/B testing.
        knowledge_base_ids: Identifiers of KnowledgeBases this agent may use.
    """

    id: str
    tenant_id: str
    prompt_version: str = "v1"
    knowledge_base_ids: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate invariants that must hold for every Agent instance."""
        if not self.id or not self.id.strip():
            raise ValueError("Agent.id must not be empty.")
        if not self.tenant_id or not self.tenant_id.strip():
            raise ValueError("Agent.tenant_id must not be empty.")
        for kb_id in self.knowledge_base_ids:
            if not kb_id or not kb_id.strip():
                raise ValueError(
                    "All entries in Agent.knowledge_base_ids must be non-empty strings."
                )
