"""Administrative read models for tenant-scoped knowledge data."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
)


KnowledgeBaseAdminStatus = Literal[
    "active",
    "inactive",
]

DocumentAdminStatus = Literal[
    "pending",
    "processing",
    "ready",
    "failed",
]

IngestionJobAdminStatus = Literal[
    "pending",
    "processing",
    "succeeded",
    "failed",
]


class KnowledgeBaseAdminResponse(BaseModel):
    """Administrative summary for one tenant-owned knowledge base."""

    id: str
    tenant_id: str
    name: str
    description: str
    status: KnowledgeBaseAdminStatus
    created_at: datetime
    updated_at: datetime
    assigned_agent_ids: list[str] = Field(
        default_factory=list,
    )
    document_count: int = Field(ge=0)
    pending_document_count: int = Field(ge=0)
    processing_document_count: int = Field(ge=0)
    ready_document_count: int = Field(ge=0)
    failed_document_count: int = Field(ge=0)
    chunk_count: int = Field(ge=0)
    pending_job_count: int = Field(ge=0)
    processing_job_count: int = Field(ge=0)
    failed_job_count: int = Field(ge=0)


class IngestionJobAdminResponse(BaseModel):
    """Non-secret lifecycle details for one ingestion job."""

    id: str
    tenant_id: str
    agent_id: str
    knowledge_base_id: str
    document_id: str
    status: IngestionJobAdminStatus
    attempts: int = Field(ge=0)
    max_attempts: int = Field(gt=0)
    available_at: datetime
    last_error: str | None
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None


class DocumentJobAdminResponse(BaseModel):
    """Queued administrative document-ingestion operation."""

    document_id: str
    document_status: DocumentAdminStatus
    duplicate: bool = False
    job: IngestionJobAdminResponse | None = None


class DocumentAdminResponse(BaseModel):
    """Administrative document metadata with derived ingestion details."""

    id: str
    tenant_id: str
    knowledge_base_id: str
    agent_id: str | None
    original_filename: str
    source_name: str
    mime_type: str
    file_size_bytes: int = Field(ge=0)
    status: DocumentAdminStatus
    failure_reason: str | None
    created_at: datetime
    updated_at: datetime
    chunk_count: int = Field(ge=0)
    latest_job: IngestionJobAdminResponse | None


KnowledgeBaseAdminName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]

KnowledgeBaseAdminDescription = Annotated[
    str,
    StringConstraints(strip_whitespace=True, max_length=4000),
]

KnowledgeAgentIdentifier = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=128),
]


def _unique_agent_ids(values: list[str]) -> list[str]:
    if len(values) != len(set(values)):
        raise ValueError("Agent identifiers must be unique.")
    return values


class KnowledgeBaseAdminCreate(BaseModel):
    """Create one tenant-owned knowledge base."""

    model_config = ConfigDict(extra="forbid")

    name: KnowledgeBaseAdminName
    description: KnowledgeBaseAdminDescription = ""
    status: KnowledgeBaseAdminStatus = "active"
    assigned_agent_ids: list[KnowledgeAgentIdentifier] = Field(
        default_factory=list,
        max_length=100,
    )

    _validate_unique_agent_ids = field_validator(
        "assigned_agent_ids",
    )(_unique_agent_ids)


class KnowledgeBaseAdminUpdate(BaseModel):
    """Update mutable knowledge-base fields."""

    model_config = ConfigDict(extra="forbid")

    name: KnowledgeBaseAdminName | None = None
    description: KnowledgeBaseAdminDescription | None = None
    status: KnowledgeBaseAdminStatus | None = None

    def has_changes(self) -> bool:
        return bool(self.model_fields_set)


class KnowledgeBaseAgentAssignmentsUpdate(BaseModel):
    """Replace the complete agent assignment set."""

    model_config = ConfigDict(extra="forbid")

    agent_ids: list[KnowledgeAgentIdentifier] = Field(
        default_factory=list,
        max_length=100,
    )

    _validate_unique_agent_ids = field_validator(
        "agent_ids",
    )(_unique_agent_ids)
