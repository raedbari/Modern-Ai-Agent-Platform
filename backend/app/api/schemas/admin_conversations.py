"""Administrative read models for tenant-scoped conversations."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


MessageAdminRole = Literal[
    "system",
    "user",
    "assistant",
    "tool",
]


class ConversationAdminResponse(BaseModel):
    """Administrative summary for one tenant-owned conversation."""

    id: str
    tenant_id: str
    agent_id: str
    agent_name: str
    user_identifier: str | None
    metadata: dict[str, Any] | None
    message_count: int = Field(ge=0)
    user_message_count: int = Field(ge=0)
    assistant_message_count: int = Field(ge=0)
    last_message_role: MessageAdminRole | None
    last_message_preview: str | None
    created_at: datetime
    updated_at: datetime


class ConversationAdminListResponse(BaseModel):
    """Paginated tenant conversation collection."""

    items: list[ConversationAdminResponse] = Field(
        default_factory=list,
    )
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=200)
    offset: int = Field(ge=0)


class MessageAdminResponse(BaseModel):
    """One persisted tenant-scoped conversation message."""

    id: str
    tenant_id: str
    conversation_id: str
    role: MessageAdminRole
    content: str
    metadata: dict[str, Any] | None
    created_at: datetime


class MessageAdminListResponse(BaseModel):
    """Paginated messages for one conversation."""

    items: list[MessageAdminResponse] = Field(
        default_factory=list,
    )
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=500)
    offset: int = Field(ge=0)
