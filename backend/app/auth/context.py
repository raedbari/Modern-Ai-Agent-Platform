"""Trusted authorization context passed into application services."""

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class ChatExecutionContext:
    """Tenant and agent identity resolved by the backend."""

    tenant_id: str
    agent_id: str
    system_prompt: str | None
    knowledge_mode: Literal["required", "preferred", "disabled"] = "preferred"
    contact_message: str | None = None
