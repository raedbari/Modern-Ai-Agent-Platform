"""Admin authentication endpoints.

Routes
------
POST /api/admin/auth/login           -- issue access + refresh tokens
POST /api/admin/auth/refresh         -- rotate refresh token
POST /api/admin/auth/logout          -- revoke refresh session
GET  /api/admin/auth/me              -- current admin profile
POST /api/admin/auth/change-password -- change password + revoke all sessions
"""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import require_admin_jwt
from backend.app.api.schemas.admin_auth import (
    AdminProfileResponse,
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    LogoutRequest,
    RefreshRequest,
)
from backend.app.core.config import Settings, get_settings
from backend.app.core.client_ip import get_client_ip
from backend.app.core.rate_limit import RateLimiter, get_rate_limiter
from backend.app.db.base import get_db
from backend.app.auth.admin_context import AdminContext
from backend.app.services.audit import AuditService
from backend.app.operations.admin_auth_ops import (
    InactiveAdminError,
    InvalidCredentialsError,
    ReplayDetectedError,
    SessionNotFoundError,
    WeakPasswordError,
    WrongCurrentPasswordError,
    authenticate_admin,
    change_password,
    revoke_session,
    rotate_refresh_token,
)

router = APIRouter(prefix="/api/admin/auth", tags=["admin-auth"])

LOGGER = logging.getLogger(__name__)

# Generic error message — never reveals whether username or password failed.
_INVALID_CREDENTIALS_DETAIL = "Invalid credentials."


@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin login",
    description=(
        "Authenticate with username and password. "
        "Returns a short-lived JWT access token and a long-lived opaque "
        "refresh token."
    ),
)
async def login(
    payload: LoginRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    rate_limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
) -> LoginResponse:
    """Issue an access token and refresh token for valid admin credentials."""

    client_ip = get_client_ip(request, settings)
    user_agent = request.headers.get("User-Agent", "")[:512] or None

    try:
        account_limit = await rate_limiter.check(
            bucket="admin-login-account",
            identity=payload.username.strip().casefold(),
            limit=settings.admin_login_rate_limit_per_account,
            window_seconds=settings.admin_login_rate_limit_window_seconds,
        )
        ip_limit = await rate_limiter.check(
            bucket="admin-login-ip",
            identity=client_ip or "unknown",
            limit=settings.admin_login_rate_limit_per_ip,
            window_seconds=settings.admin_login_rate_limit_window_seconds,
        )
    except Exception:
        LOGGER.exception("Admin login rate limiter is unavailable")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is temporarily unavailable.",
        )

    if not account_limit.allowed or not ip_limit.allowed:
        retry_after = max(
            account_limit.retry_after_seconds,
            ip_limit.retry_after_seconds,
        )
        await AuditService.write(
            session,
            event_type="login_rate_limited",
            outcome="failure",
            client_ip=client_ip,
            detail={"reason": "rate_limit_exceeded"},
        )
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    try:
        access_token, refresh_token = await authenticate_admin(
            session,
            username=payload.username,
            plain_password=payload.password,
            settings=settings,
            client_ip=client_ip,
            user_agent=user_agent,
        )
        await session.commit()
    except (InvalidCredentialsError, InactiveAdminError):
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=_INVALID_CREDENTIALS_DETAIL,
        )
    except Exception:
        await session.rollback()
        LOGGER.exception("Unexpected error during admin login")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred.",
        )

    expires_in = settings.jwt_access_token_expire_minutes * 60

    # Decode the token minimally to read admin_id and role for the response.
    # We just created the token, so we skip full verification here.
    import jwt as _jwt  # local import to avoid confusion with module name

    raw_payload = _jwt.decode(
        access_token,
        options={"verify_signature": False},
        algorithms=["HS256"],
    )

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="Bearer",
        expires_in=expires_in,
        admin_id=raw_payload["sub"],
        role=raw_payload["role"],
    )


@router.post(
    "/refresh",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Rotate admin refresh token",
    description=(
        "Exchange a valid refresh token for a new access token and a new "
        "refresh token.  The presented token is immediately revoked. "
        "Re-presenting a revoked token triggers session-family revocation."
    ),
)
async def refresh(
    payload: RefreshRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> LoginResponse:
    """Rotate a refresh token and return a new token pair."""

    client_ip = get_client_ip(request, settings)
    user_agent = request.headers.get("User-Agent", "")[:512] or None

    try:
        access_token, new_refresh_token = await rotate_refresh_token(
            session,
            raw_refresh_token=payload.refresh_token,
            settings=settings,
            client_ip=client_ip,
            user_agent=user_agent,
        )
        await session.commit()
    except ReplayDetectedError:
        await session.commit()   # replay already wrote audit + revocations
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Security alert: session has been compromised.",
        )
    except (SessionNotFoundError, InactiveAdminError):
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token.",
        )
    except Exception:
        await session.rollback()
        LOGGER.exception("Unexpected error during token refresh")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred.",
        )

    expires_in = settings.jwt_access_token_expire_minutes * 60

    import jwt as _jwt

    raw_payload = _jwt.decode(
        access_token,
        options={"verify_signature": False},
        algorithms=["HS256"],
    )

    return LoginResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        token_type="Bearer",
        expires_in=expires_in,
        admin_id=raw_payload["sub"],
        role=raw_payload["role"],
    )


# ---------------------------------------------------------------------------
# Helper: extract Bearer token from Authorization header
# ---------------------------------------------------------------------------

def _bearer_token(request: Request) -> str | None:
    """Return the raw token from 'Authorization: Bearer <token>', or None."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[len("Bearer "):]
    return None


# ---------------------------------------------------------------------------
# POST /logout
# ---------------------------------------------------------------------------

class _LogoutResponse:
    detail: str


@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
    summary="Admin logout",
    description=(
        "Revoke the presented refresh token.  Idempotent — calling logout "
        "on an already-revoked session returns 200 without error."
    ),
)
async def logout(
    payload: LogoutRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict:
    """Revoke a refresh session. Requires a valid Bearer access token."""

    # Validate the access token so only the legitimate holder can logout.
    from backend.app.auth.admin_jwt import AdminTokenError, decode_access_token

    raw_token = _bearer_token(request)
    if raw_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header with Bearer token is required.",
        )

    try:
        ctx = decode_access_token(raw_token, settings)
    except AdminTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        )

    client_ip = get_client_ip(request, settings)

    try:
        await revoke_session(
            session,
            raw_refresh_token=payload.refresh_token,
            admin_id=ctx.admin_id,
            family_id=ctx.session_family_id,
            client_ip=client_ip,
        )
        await session.commit()
    except Exception:
        await session.rollback()
        LOGGER.exception("Unexpected error during admin logout")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred.",
        )

    return {"detail": "Logged out successfully."}


# ---------------------------------------------------------------------------
# GET /me  (T-11)
# ---------------------------------------------------------------------------

@router.get(
    "/me",
    response_model=AdminProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Current admin profile",
    description="Return the profile of the authenticated admin operator.",
)
async def me(
    session: Annotated[AsyncSession, Depends(get_db)],
    ctx: Annotated[AdminContext, Depends(require_admin_jwt)],
) -> AdminProfileResponse:
    """Return the profile of the currently authenticated admin."""
    from backend.app.db.models import AdminUser

    admin = await session.get(AdminUser, ctx.admin_id)
    if admin is None or not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin account is not active.",
        )

    return AdminProfileResponse(
        admin_id=admin.id,
        username=admin.username,
        role=admin.role,
        is_active=admin.is_active,
        created_at=admin.created_at,
        last_login_at=admin.last_login_at,
    )


# ---------------------------------------------------------------------------
# POST /change-password  (T-12)
# ---------------------------------------------------------------------------

@router.post(
    "/change-password",
    status_code=status.HTTP_200_OK,
    summary="Change admin password",
    description=(
        "Verify the current password, set a new one, and immediately "
        "revoke all active refresh sessions for the account."
    ),
)
async def change_password_endpoint(
    payload: ChangePasswordRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    ctx: Annotated[AdminContext, Depends(require_admin_jwt)],
) -> dict:
    """Change password and revoke all sessions."""
    client_ip = get_client_ip(request, settings)

    try:
        await change_password(
            session,
            admin_id=ctx.admin_id,
            current_password=payload.current_password,
            new_password=payload.new_password,
            settings=settings,
            client_ip=client_ip,
        )
        await session.commit()
    except WrongCurrentPasswordError:
        # The operation changed no account state; commit its failure audit.
        await session.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect.",
        )
    except WeakPasswordError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )
    except Exception:
        await session.rollback()
        LOGGER.exception("Unexpected error during password change")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred.",
        )

    return {"detail": "Password changed. All sessions have been revoked."}
