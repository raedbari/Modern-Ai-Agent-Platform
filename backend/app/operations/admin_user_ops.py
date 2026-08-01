"""Service-layer operations for admin account management.

All functions accept an open AsyncSession.  Callers commit or rollback.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import AdminRefreshSession, AdminUser
from backend.app.services.audit import AuditService


# ---------------------------------------------------------------------------
# Typed exceptions
# ---------------------------------------------------------------------------

class AdminUserNotFoundError(LookupError):
    """Raised when the requested admin account does not exist."""


class DuplicateUsernameError(ValueError):
    """Raised when the requested username is already taken."""


class SelfDeactivationError(ValueError):
    """Raised when an admin attempts to deactivate their own account."""


# ---------------------------------------------------------------------------
# list_admins
# ---------------------------------------------------------------------------

async def list_admins(session: AsyncSession) -> list[AdminUser]:
    """Return all admin accounts ordered by creation time."""
    return list(
        (
            await session.scalars(
                select(AdminUser).order_by(AdminUser.created_at, AdminUser.id)
            )
        ).all()
    )


# ---------------------------------------------------------------------------
# create_admin
# ---------------------------------------------------------------------------

async def create_admin(
    session: AsyncSession,
    *,
    username: str,
    plain_password: str,
    role: str,
    created_by_id: str,
    settings,
    client_ip: str | None = None,
) -> AdminUser:
    """Create a new admin account.

    Raises
    ------
    DuplicateUsernameError
        If the username is already in use.
    """
    from backend.app.auth.admin_password import hash_admin_password
    from backend.app.operations.admin_auth_ops import (
        WeakPasswordError,
        _validate_password_strength,
    )

    _validate_password_strength(plain_password)

    existing = await session.scalar(
        select(AdminUser).where(AdminUser.username == username).limit(1)
    )
    if existing is not None:
        raise DuplicateUsernameError(f"Username '{username}' is already taken.")

    hashed = hash_admin_password(plain_password, settings)
    admin = AdminUser(
        id=str(uuid.uuid4()),
        username=username,
        hashed_password=hashed,
        role=role,
        is_active=True,
        created_by=created_by_id,
    )
    session.add(admin)
    await session.flush()

    await AuditService.write(
        session,
        event_type="admin_created",
        outcome="success",
        admin_id=created_by_id,
        target_type="admin",
        target_id=admin.id,
        client_ip=client_ip,
        detail={"username": username, "role": role},
    )

    return admin


# ---------------------------------------------------------------------------
# set_admin_active
# ---------------------------------------------------------------------------

async def set_admin_active(
    session: AsyncSession,
    *,
    target_admin_id: str,
    is_active: bool,
    requesting_admin_id: str,
    client_ip: str | None = None,
) -> AdminUser:
    """Activate or deactivate an admin account.

    Raises
    ------
    AdminUserNotFoundError
        If the target admin does not exist.
    SelfDeactivationError
        If the admin tries to deactivate their own account.
    """
    if not is_active and target_admin_id == requesting_admin_id:
        raise SelfDeactivationError("Cannot deactivate your own account.")

    admin = await session.get(AdminUser, target_admin_id)
    if admin is None:
        raise AdminUserNotFoundError(f"Admin '{target_admin_id}' not found.")

    admin.is_active = is_active
    await session.flush()

    # Revoke all sessions when deactivating.
    if not is_active:
        now = datetime.now(timezone.utc)
        active_sessions = list(
            (
                await session.scalars(
                    select(AdminRefreshSession).where(
                        AdminRefreshSession.admin_id == target_admin_id,
                        AdminRefreshSession.revoked_at.is_(None),
                    )
                )
            ).all()
        )
        for sess in active_sessions:
            sess.revoked_at = now

    event_type = "admin_deactivated" if not is_active else "admin_reactivated"
    await AuditService.write(
        session,
        event_type=event_type,
        outcome="success",
        admin_id=requesting_admin_id,
        target_type="admin",
        target_id=target_admin_id,
        client_ip=client_ip,
    )

    return admin


# ---------------------------------------------------------------------------
# revoke_all_admin_sessions
# ---------------------------------------------------------------------------

async def revoke_all_admin_sessions(
    session: AsyncSession,
    *,
    target_admin_id: str,
    requesting_admin_id: str,
    client_ip: str | None = None,
) -> int:
    """Force-revoke all active sessions for one admin.  Returns revoked count.

    Raises
    ------
    AdminUserNotFoundError
        If the target admin does not exist.
    """
    admin = await session.get(AdminUser, target_admin_id)
    if admin is None:
        raise AdminUserNotFoundError(f"Admin '{target_admin_id}' not found.")

    now = datetime.now(timezone.utc)
    active_sessions = list(
        (
            await session.scalars(
                select(AdminRefreshSession).where(
                    AdminRefreshSession.admin_id == target_admin_id,
                    AdminRefreshSession.revoked_at.is_(None),
                )
            )
        ).all()
    )

    for sess in active_sessions:
        sess.revoked_at = now

    await session.flush()

    await AuditService.write(
        session,
        event_type="admin_sessions_revoked",
        outcome="success",
        admin_id=requesting_admin_id,
        target_type="admin",
        target_id=target_admin_id,
        client_ip=client_ip,
        detail={"revoked_count": len(active_sessions)},
    )

    return len(active_sessions)
