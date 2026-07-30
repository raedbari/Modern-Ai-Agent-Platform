"""HTTP schemas for the authenticated Knowledge API."""

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from backend.app.domain.models.enums import (
    DocumentProcessingStatus,
    KnowledgeBaseStatus,
)

Name = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]
Description = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=4000),
]


class KnowledgeBaseCreate(BaseModel):
    """Create input; ownership always comes from authenticated context."""

    model_config = ConfigDict(extra="forbid")

    name: Name
    description: Description = ""


class KnowledgeBaseUpdate(BaseModel):
    """Mutable knowledge-base fields."""

    model_config = ConfigDict(extra="forbid")

    name: Name | None = None
    description: Description | None = None
    status: KnowledgeBaseStatus | None = None

    def has_changes(self) -> bool:
        return bool(self.model_fields_set)


class KnowledgeBaseResponse(BaseModel):
    id: str
    name: str
    description: str
    status: KnowledgeBaseStatus


class DocumentResponse(BaseModel):
    id: str
    knowledge_base_id: str
    original_filename: str
    source_name: str
    mime_type: str
    file_size_bytes: int = Field(ge=0)
    status: DocumentProcessingStatus
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime


class DocumentIngestionResponse(DocumentResponse):
    chunks_persisted: int = Field(ge=0)
    duplicate: bool
