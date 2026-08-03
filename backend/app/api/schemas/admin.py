"""Schemas for the temporary internal administrative lifecycle API."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LifecycleStatusUpdate(BaseModel):
    """Activate or suspend one tenant or agent."""

    is_active: bool


class TenantAdminResponse(BaseModel):
    """Administrative tenant metadata."""

    id: str
    name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AgentAdminResponse(BaseModel):
    """Administrative agent metadata."""

    id: str
    tenant_id: str
    name: str
    is_active: bool
    knowledge_mode: str
    created_at: datetime
    updated_at: datetime


class ApiKeyAdminResponse(BaseModel):
    """Non-secret API-key metadata."""

    key_id: str
    tenant_id: str
    name: str | None
    is_active: bool
    created_at: datetime
    expires_at: datetime | None
    revoked_at: datetime | None
    last_used_at: datetime | None


class RevokeAllApiKeysResponse(BaseModel):
    """Count returned after revoking all active keys for one tenant."""

    revoked_count: int = Field(ge=0)


class AgentConfigUpdate(BaseModel):
    """Partial update for editable agent configuration.

    Field semantics:
    - Absent field: preserve the stored value.
    - Explicit null: permitted only for nullable fields.
    - Explicit value: validate, normalize, and update.
    """

    model_config = ConfigDict(extra="forbid")

    # These fields are optional in a PATCH request but cannot explicitly be null.
    # Pydantic accepts the omitted default while rejecting an explicit None.
    name: str = Field(
        default=None,
        min_length=1,
        max_length=255,
    )
    knowledge_mode: Literal[
        "required",
        "preferred",
        "disabled",
    ] = Field(default=None)

    # These database fields are nullable and may explicitly be cleared.
    system_prompt: str | None = Field(
        default=None,
        max_length=10_000,
    )
    contact_message: str | None = Field(
        default=None,
        max_length=1_000,
    )

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: object) -> object:
        """Strip surrounding whitespace before length validation."""

        if isinstance(value, str):
            return value.strip()
        return value

    def has_changes(self) -> bool:
        """Return whether at least one PATCH field was supplied."""

        return bool(self.model_fields_set)


class AgentConfigResponse(BaseModel):
    """Agent configuration response with non-sensitive fields."""

    id: str
    tenant_id: str
    name: str
    system_prompt: str | None
    knowledge_mode: str
    contact_message: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
