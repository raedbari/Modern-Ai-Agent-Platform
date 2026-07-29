"""API request and response schemas."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints


class ChatRequest(BaseModel):
    """Request to send a message to an AI agent."""

    agent_id: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=128),
    ]
    message: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1),
    ]
    conversation_id: Annotated[
        str | None,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=128),
    ] = None
    user_identifier: Annotated[
        str | None,
        StringConstraints(strip_whitespace=True, max_length=255),
    ] = None
    idempotency_key: Annotated[
        str | None,
        StringConstraints(strip_whitespace=True, max_length=255),
    ] = None
    temperature: float = Field(default=0.2, ge=0, le=2)
    max_tokens: int = Field(default=1024, gt=0, le=4096)


class MessageResponse(BaseModel):
    """Response containing a single message."""

    id: str
    role: Literal["user", "assistant", "system"]
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatResponse(BaseModel):
    """Response from chat endpoint."""

    conversation_id: str
    message: MessageResponse
    request_id: str | None = None


class ConversationResponse(BaseModel):
    """Response containing conversation details."""

    id: str
    client_id: str
    agent_id: str
    user_identifier: str | None
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    class Config:
        from_attributes = True


class ConversationMessagesResponse(BaseModel):
    """Response containing conversation messages."""

    conversation_id: str
    messages: list[MessageResponse]
    total: int
