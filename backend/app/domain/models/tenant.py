"""Tenant domain model.

A Tenant represents a single company or organisation that has been onboarded
onto the platform.  Every other entity in the system is scoped to a Tenant,
making it the root of the multi-tenant isolation hierarchy.
"""

from dataclasses import dataclass, field


@dataclass
class Tenant:
    """A company or organisation that owns agents and knowledge bases.

    Attributes:
        id:           Unique, opaque identifier (UUID string).
        display_name: Human-readable name shown in the UI.
    """

    id: str
    display_name: str

    def __post_init__(self) -> None:
        """Validate invariants that must hold for every Tenant instance."""
        if not self.id or not self.id.strip():
            raise ValueError("Tenant.id must not be empty.")
        if not self.display_name or not self.display_name.strip():
            raise ValueError("Tenant.display_name must not be empty.")
