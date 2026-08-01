"""Schemas for the temporary internal administrative lifecycle API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


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
