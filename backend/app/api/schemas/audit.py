"""Pydantic schemas for admin audit log API."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class AdminAuditEventResponse(BaseModel):
    """Response schema for a single audit event."""

    id: str
    actor_admin_id: str | None
    actor_username: str
    actor_role: str
    action: str
    tenant_id: str | None
    resource_type: str
    resource_id: str | None
    changed_fields: dict[str, Any] | None
    metadata: dict[str, Any] | None
    ip_address: str | None
    request_id: str | None
    success: bool
    error_message: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class AdminAuditEventListResponse(BaseModel):
    """Response schema for paginated list of audit events."""

    events: list[AdminAuditEventResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

    @classmethod
    def from_results(
        cls,
        events: list[Any],
        total: int,
        page: int,
        page_size: int,
    ) -> "AdminAuditEventListResponse":
        """Create response from repository results.
        
        Args:
            events: List of audit event models
            total: Total count of matching events
            page: Current page number (1-indexed)
            page_size: Number of items per page
        
        Returns:
            Formatted response with pagination metadata
        """
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        
        return cls(
            events=[AdminAuditEventResponse.model_validate(e) for e in events],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


class AdminAuditEventFilters(BaseModel):
    """Query parameters for filtering audit events."""

    actor_admin_id: str | None = Field(
        None,
        description="Filter by admin user ID",
    )
    action: str | None = Field(
        None,
        description="Filter by action type (e.g., 'tenant.deleted')",
        max_length=100,
    )
    tenant_id: str | None = Field(
        None,
        description="Filter by tenant ID",
        max_length=128,
    )
    resource_type: str | None = Field(
        None,
        description="Filter by resource type (e.g., 'tenant', 'agent')",
        max_length=100,
    )
    start_date: datetime | None = Field(
        None,
        description="Filter events after this date (ISO 8601)",
    )
    end_date: datetime | None = Field(
        None,
        description="Filter events before this date (ISO 8601)",
    )

    @field_validator("start_date", "end_date")
    @classmethod
    def validate_dates(cls, value: datetime | None) -> datetime | None:
        """Ensure dates are timezone-aware."""
        if value is not None and value.tzinfo is None:
            raise ValueError("Dates must be timezone-aware (ISO 8601)")
        return value


class AdminAuditEventStatsResponse(BaseModel):
    """Statistics about audit events."""

    total_events: int
    unique_actors: int
    unique_actions: int
    success_count: int
    failure_count: int
    date_range: dict[str, datetime | None] = Field(
        description="Earliest and latest event dates",
    )
