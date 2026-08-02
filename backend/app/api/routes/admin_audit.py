"""Read-only endpoint for immutable administrator audit events."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import require_admin_access, require_permission
from backend.app.api.schemas.admin_audit import AdminAuditEventResponse
from backend.app.db.base import get_db
from backend.app.services.audit import AuditService


router = APIRouter(
    prefix="/api/admin/audit",
    tags=["admin-audit"],
    dependencies=[Depends(require_admin_access)],
)


@router.get(
    "",
    response_model=list[AdminAuditEventResponse],
    dependencies=[Depends(require_permission("audit:read"))],
)
async def get_audit_events(
    session: Annotated[AsyncSession, Depends(get_db)],
    event_type: Annotated[str | None, Query(max_length=64)] = None,
    admin_id: Annotated[str | None, Query(max_length=128)] = None,
    outcome: Literal["success", "failure"] | None = None,
    before_id: Annotated[int | None, Query(ge=1)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[AdminAuditEventResponse]:
    rows = await AuditService.list_events(
        session,
        event_type=event_type,
        admin_id=admin_id,
        outcome=outcome,
        before_id=before_id,
        limit=limit,
    )
    return [
        AdminAuditEventResponse(
            id=row.id,
            admin_id=row.admin_id,
            event_type=row.event_type,
            target_type=row.target_type,
            target_id=row.target_id,
            outcome=row.outcome,
            client_ip=row.client_ip,
            created_at=row.created_at,
            detail=row.detail,
        )
        for row in rows
    ]
