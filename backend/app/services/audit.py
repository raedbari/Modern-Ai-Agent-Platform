"""Append-only audit logging service for administrative actions.

AuditService.write() is the single write path into admin_audit_log.
No UPDATE or DELETE on that table is exposed anywhere in this module.
"""

from __future__ import annotations

from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import AdminAuditLog


class AuditService:
    """Write structured audit entries into admin_audit_log.

    Usage
    -----
    Call ``AuditService.write()`` inside the same database transaction as the
    operation being audited so that the log entry and the state change commit
    or roll back together.

    The service is intentionally stateless — every method is a classmethod so
    callers do not need to manage an instance.
    """

    @classmethod
    async def write(
        cls,
        session: AsyncSession,
        *,
        event_type: str,
        outcome: Literal["success", "failure"],
        admin_id: str | None = None,
        target_type: str | None = None,
        target_id: str | None = None,
        client_ip: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> int:
        """Insert one immutable audit record and return its generated id.

        Parameters
        ----------
        session:
            The active async SQLAlchemy session.  The row is added to the
            session but NOT committed here — commit is the caller's responsibility.
        event_type:
            Short string identifying the action, e.g. ``"login_success"``.
        outcome:
            Either ``"success"`` or ``"failure"``.
        admin_id:
            Identity of the acting administrator.  May be ``None`` for
            pre-authentication events (e.g. ``login_failure`` when the
            username is unknown).
        target_type:
            Resource kind being acted on, e.g. ``"tenant"``, ``"agent"``.
        target_id:
            Identifier of the specific resource, e.g. a tenant_id string.
        client_ip:
            IPv4 or IPv6 address of the request originator.
        detail:
            Arbitrary JSON-serialisable dict with additional context.
            Must never contain passwords or raw tokens.

        Returns
        -------
        int
            The auto-generated primary key of the inserted row.
        """
        row = AdminAuditLog(
            admin_id=admin_id,
            event_type=event_type,
            target_type=target_type,
            target_id=target_id,
            outcome=outcome,
            client_ip=client_ip,
            detail=detail,
        )
        session.add(row)
        await session.flush()   # populate row.id without committing
        return row.id

    @classmethod
    async def list_events(
        cls,
        session: AsyncSession,
        *,
        event_type: str | None = None,
        admin_id: str | None = None,
        outcome: Literal["success", "failure"] | None = None,
        before_id: int | None = None,
        limit: int = 100,
    ) -> list[AdminAuditLog]:
        """Return a stable newest-first page without exposing mutation APIs."""

        statement = select(AdminAuditLog)
        if event_type is not None:
            statement = statement.where(
                AdminAuditLog.event_type == event_type
            )
        if admin_id is not None:
            statement = statement.where(AdminAuditLog.admin_id == admin_id)
        if outcome is not None:
            statement = statement.where(AdminAuditLog.outcome == outcome)
        if before_id is not None:
            statement = statement.where(AdminAuditLog.id < before_id)

        return list(
            (
                await session.scalars(
                    statement.order_by(AdminAuditLog.id.desc()).limit(limit)
                )
            ).all()
        )
