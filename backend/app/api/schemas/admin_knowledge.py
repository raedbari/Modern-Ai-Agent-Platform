"""Administrative read models for tenant-scoped knowledge data."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


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
