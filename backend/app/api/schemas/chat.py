"""HTTP schemas for the tenant-scoped chat endpoint."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Identifier = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=128),
]
MessageText = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=8000),
]


class ChatRequest(BaseModel):
    """Untrusted client input; tenant and agent identities are forbidden."""

    model_config = ConfigDict(extra="forbid")

    message: MessageText
    conversation_id: Identifier | None = None


class TokenUsage(BaseModel):
    """Normalized token usage returned by the generation provider."""

    prompt: int = Field(ge=0)
    completion: int = Field(ge=0)


class ChatResponse(BaseModel):
    """Persisted assistant response."""

    conversation_id: str
    message_id: str
    reply: str
    model: str
    finish_reason: str | None = None
    usage: TokenUsage