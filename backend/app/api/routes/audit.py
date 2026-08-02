"""Admin audit log API endpoints.

This module provides read-only access to administrative audit logs.
Only super_admin and auditor roles can access these endpoints.
The operator role receives a 403 Forbidden response.

All audit events are append-only - there are no endpoints for
updating or deleting audit records.
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import require_audit_read_access
from backend.app.api.schemas.audit import (
    AdminAuditEventListResponse,
    AdminAuditEventResponse,
)
from backend.app.db.base import get_db
from backend.app.services import audit_log as audit_service

router = APIRouter(
    prefix="/api/admin/audit",
    tags=["admin-audit"],
)
LOGGER = logging.getLogger(__name__)


@router.get(
    "/events",
    response_model=AdminAuditEventListResponse,
    summary="List audit events",
    description=(
        "Retrieve a paginated list of administrative audit events with "
        "optional filtering. Only accessible by super_admin and auditor roles."
    ),
)
async def list_audit_events(
    session: Annotated[AsyncSession, Depends(get_db)],
    _role: Annotated[str, Depends(require_audit_read_access)],
    actor_admin_id: Annotated[
        str | None,
        Query(description="Filter by admin user ID"),
    ] = None,
    action: Annotated[
        str | None,
        Query(
            description="Filter by action type (e.g., 'tenant.deleted')",
            max_length=100,
        ),
    ] = None,
    tenant_id: Annotated[
        str | None,
        Query(description="Filter by tenant ID", max_length=128),
    ] = None,
    resource_type: Annotated[
        str | None,
        Query(
            description="Filter by resource type (e.g., 'tenant', 'agent')",
            max_length=100,
        ),
    ] = None,
    page: Annotated[
        int,
        Query(ge=1, description="Page number (1-indexed)"),
    ] = 1,
    page_size: Annotated[
        int,
        Query(ge=1, le=100, description="Number of items per page"),
    ] = 50,
) -> AdminAuditEventListResponse:
    """List audit events with filtering and pagination.
    
    This endpoint returns audit logs of administrative actions performed
    in the system. All sensitive data in the logs has been automatically
    sanitized (passwords, tokens, secrets are redacted).
    
    Access Control:
    - super_admin: ✅ Can access
    - auditor: ✅ Can access
    - operator: ❌ 403 Forbidden
    
    Example:
        GET /api/admin/audit/events?action=tenant.deleted&page=1&page_size=20
    """
    skip = (page - 1) * page_size
    
    events, total = await audit_service.list_events(
        session,
        actor_admin_id=actor_admin_id,
        action=action,
        tenant_id=tenant_id,
        resource_type=resource_type,
        skip=skip,
        limit=page_size,
    )
    
    return AdminAuditEventListResponse.from_results(
        events=events,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/events/{event_id}",
    response_model=AdminAuditEventResponse,
    summary="Get audit event by ID",
    description=(
        "Retrieve a single audit event by its ID. "
        "Only accessible by super_admin and auditor roles."
    ),
)
async def get_audit_event(
    event_id: str,
    session: Annotated[AsyncSession, Depends(get_db)],
    _role: Annotated[str, Depends(require_audit_read_access)],
) -> AdminAuditEventResponse:
    """Retrieve a single audit event by ID.
    
    Access Control:
    - super_admin: ✅ Can access
    - auditor: ✅ Can access
    - operator: ❌ 403 Forbidden
    
    Example:
        GET /api/admin/audit/events/123e4567-e89b-12d3-a456-426614174000
    """
    event = await audit_service.get_event_by_id(session, event_id)
    
    if event is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit event not found: {event_id}",
        )
    
    return AdminAuditEventResponse.model_validate(event)
