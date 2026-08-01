"""Admin account management endpoints (T-16).

Routes
------
GET    /api/admin/admins                       -- list all admins
POST   /api/admin/admins                       -- create new admin
PATCH  /api/admin/admins/{admin_id}/status     -- activate / deactivate
DELETE /api/admin/admins/{admin_id}/sessions   -- force-revoke all sessions
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import require_admin_access, require_permission
from backend.app.api.schemas.admin import LifecycleStatusUpdate
from backend.app.api.schemas.admin_auth import (
    AdminUserResponse,
    CreateAdminRequest,
    RevokeAdminSessionsResponse,
)
from backend.app.auth.admin_context import AdminContext
from backend.app.core.config import Settings, get_settings
from backend.app.db.base import get_db
from backend.app.operations.admin_user_ops import (
    AdminUserNotFoundError,
    DuplicateUsernameError,
    SelfDeactivationError,
    create_admin,
    list_admins,
    revoke_all_admin_sessions,
    set_admin_active,
)

router = APIRouter(
    prefix="/api/admin/admins",
    tags=["admin-users"],
    dependencies=[Depends(require_admin_access)],
)
LOGGER = logging.getLogger(__name__)


def _admin_response(item) -> AdminUserResponse:
    return AdminUserResponse(
        admin_id=item.id,
        username=item.username,
        role=item.role,
        is_active=item.is_active,
        created_at=item.created_at,
        last_login_at=item.last_login_at,
    )


def _get_ctx(request: Request, settings: Settings) -> AdminContext | None:
    """Re-decode the Bearer token from the request to get the calling context."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    from backend.app.auth.admin_jwt import AdminTokenError, decode_access_token
    try:
        return decode_access_token(auth[len("Bearer "):], settings)
    except AdminTokenError:
        return None


def _client_ip(request: Request) -> str | None:
    fwd = request.headers.get("X-Forwarded-For")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None


# ---------------------------------------------------------------------------
# GET /api/admin/admins
# ---------------------------------------------------------------------------

@router.get(
    "",
    response_model=list[AdminUserResponse],
    dependencies=[Depends(require_permission("admins:read"))],
)
async def get_admins(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[AdminUserResponse]:
    return [_admin_response(a) for a in await list_admins(session)]


# ---------------------------------------------------------------------------
# POST /api/admin/admins
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=AdminUserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("admins:write"))],
)
async def create_admin_endpoint(
    payload: CreateAdminRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AdminUserResponse:
    ctx = _get_ctx(request, settings)
    creator_id = ctx.admin_id if ctx else "legacy"
    client_ip = _client_ip(request)

    try:
        admin = await create_admin(
            session,
            username=payload.username,
            plain_password=payload.password,
            role=payload.role,
            created_by_id=creator_id,
            settings=settings,
            client_ip=client_ip,
        )
        await session.commit()
        await session.refresh(admin)
    except DuplicateUsernameError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )
    except ValueError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except Exception:
        await session.rollback()
        LOGGER.exception("Unexpected error creating admin")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred.",
        )

    return _admin_response(admin)


# ---------------------------------------------------------------------------
# PATCH /api/admin/admins/{admin_id}/status
# ---------------------------------------------------------------------------

@router.patch(
    "/{admin_id}/status",
    response_model=AdminUserResponse,
    dependencies=[Depends(require_permission("admins:write"))],
)
async def update_admin_status(
    admin_id: str,
    payload: LifecycleStatusUpdate,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AdminUserResponse:
    ctx = _get_ctx(request, settings)
    requester_id = ctx.admin_id if ctx else "legacy"
    client_ip = _client_ip(request)

    try:
        admin = await set_admin_active(
            session,
            target_admin_id=admin_id,
            is_active=payload.is_active,
            requesting_admin_id=requester_id,
            client_ip=client_ip,
        )
        await session.commit()
        await session.refresh(admin)
    except SelfDeactivationError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except AdminUserNotFoundError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except Exception:
        await session.rollback()
        LOGGER.exception("Unexpected error updating admin status")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred.",
        )

    return _admin_response(admin)


# ---------------------------------------------------------------------------
# DELETE /api/admin/admins/{admin_id}/sessions
# ---------------------------------------------------------------------------

@router.delete(
    "/{admin_id}/sessions",
    response_model=RevokeAdminSessionsResponse,
    dependencies=[Depends(require_permission("admins:delete"))],
)
async def revoke_admin_sessions(
    admin_id: str,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> RevokeAdminSessionsResponse:
    ctx = _get_ctx(request, settings)
    requester_id = ctx.admin_id if ctx else "legacy"
    client_ip = _client_ip(request)

    try:
        count = await revoke_all_admin_sessions(
            session,
            target_admin_id=admin_id,
            requesting_admin_id=requester_id,
            client_ip=client_ip,
        )
        await session.commit()
    except AdminUserNotFoundError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    except Exception:
        await session.rollback()
        LOGGER.exception("Unexpected error revoking admin sessions")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred.",
        )

    return RevokeAdminSessionsResponse(revoked_count=count)
