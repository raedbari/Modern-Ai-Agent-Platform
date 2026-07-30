"""HTTP schemas for tenant-scoped handoff management."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from typing_extensions import Annotated

HandoffStatus = Literal["open", "assigned", "closed"]
OptionalText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1),
]


class HandoffResponse(BaseModel):
    """Safe handoff representation returned to trusted tenant servers."""

    id: str
    conversation_id: str
    trigger_message_id: str
    reason: str
    status: HandoffStatus
    assigned_to: str | None
    resolution_note: str | None
    created_at: datetime
    updated_at: datetime


class HandoffUpdate(BaseModel):
    """Allowed handoff workflow changes."""

    model_config = ConfigDict(extra="forbid")

    status: HandoffStatus | None = None
    assigned_to: Annotated[
        str | None,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
    ] = None
    resolution_note: Annotated[
        str | None,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=8000),
    ] = None

    def has_changes(self) -> bool:
        return bool(self.model_fields_set)
