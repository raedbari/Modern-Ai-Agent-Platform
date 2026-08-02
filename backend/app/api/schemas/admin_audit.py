"""Schemas for reading immutable administrator audit events."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel


class AdminAuditEventResponse(BaseModel):
    id: int
    admin_id: str | None
    event_type: str
    target_type: str | None
    target_id: str | None
    outcome: Literal["success", "failure"]
    client_ip: str | None
    created_at: datetime
    detail: dict[str, Any] | None
