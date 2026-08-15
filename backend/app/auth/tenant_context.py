"""Trusted authorization context for authenticated tenant users."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal

import jwt
from jwt.exceptions import (
    ExpiredSignatureError,
    InvalidAlgorithmError,
    InvalidSignatureError,
    InvalidTokenError as JWTInvalidTokenError,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.auth.tenant_jwt import TenantTokenError, decode_access_token

from backend.app.core.config import Settings
from backend.app.db.models import User, UserRefreshSession, TenantMembership, Tenant


# ---------------------------------------------------------------------------
# Exception Classes
# ---------------------------------------------------------------------------


class TenantAuthError(Exception):
    """Base exception for tenant authentication failures.
    
    All tenant authentication errors inherit from this class.
    The message is safe to forward to an HTTP 401 response.
    """


class InvalidTokenError(TenantAuthError):
    """Raised when JWT validation fails."""


class InactiveUserError(TenantAuthError):
    """Raised when user exists but is_active=False."""


class InvalidSessionError(TenantAuthError):
    """Raised when session family is invalid or revoked."""


class NoActiveMembershipError(TenantAuthError):
    """Raised when no active TenantMembership found for user."""


class InactiveTenantError(TenantAuthError):
    """Raised when tenant is_active=False."""


# ---------------------------------------------------------------------------
# TenantUserContext Dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UserContext:
    """Authenticated customer identity backed by current DB/session state."""

    user_id: str
    email: str
    display_name: str | None
    auth_method: Literal["jwt"] = "jwt"
    session_family_id: str = ""
    jti: str | None = None

@dataclass(frozen=True, slots=True)
class TenantUserContext:
    """Tenant user identity and membership resolved by JWT authentication + DB validation."""

    user_id: str
    email: str
    display_name: str
    tenant_id: str
    membership_id: str
    role: Literal[
        "tenant_owner",
        "tenant_admin",
        "knowledge_editor",
        "conversation_viewer",
        "billing_manager",
    ]
    auth_method: Literal["jwt"] = "jwt"
    session_family_id: str | None = None
    jti: str | None = None


# ---------------------------------------------------------------------------
# JWT Algorithm Constant
# ---------------------------------------------------------------------------

_ALGORITHM = "HS256"


# ---------------------------------------------------------------------------
# TenantUserContext Validation Function
# ---------------------------------------------------------------------------


async def validate_user_context(
    token: str,
    session: AsyncSession,
    settings: Settings,
) -> UserContext:
    """Validate customer identity without requiring tenant membership."""
    try:
        payload = decode_access_token(token, settings)
    except TenantTokenError as exc:
        raise InvalidTokenError(str(exc)) from exc

    user_id = payload["sub"]
    family_id = payload["sid"]
    jti = payload.get("jti")

    user = await session.get(User, user_id)
    if user is None:
        raise InvalidTokenError("User not found.")
    if not user.is_active:
        raise InactiveUserError("User account is inactive.")

    refresh_session = await session.scalar(
        select(UserRefreshSession)
        .where(
            UserRefreshSession.user_id == user_id,
            UserRefreshSession.family_id == family_id,
            UserRefreshSession.revoked_at.is_(None),
        )
        .order_by(UserRefreshSession.expires_at.desc())
        .limit(1)
    )
    if refresh_session is None:
        raise InvalidSessionError("No active session found for this token family.")

    expires_at = refresh_session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= datetime.now(timezone.utc):
        raise InvalidSessionError("Session has expired.")

    return UserContext(
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        auth_method="jwt",
        session_family_id=family_id,
        jti=jti if isinstance(jti, str) and jti else None,
    )

async def validate_tenant_user_context(
    token: str,
    session: AsyncSession,
    settings: Settings,
) -> TenantUserContext:
    """Resolve tenant authorization on top of authenticated identity."""
    identity = await validate_user_context(token, session, settings)

    try:
        payload = decode_access_token(token, settings)
    except TenantTokenError as exc:
        raise InvalidTokenError(str(exc)) from exc

    tenant_id = payload.get("tenant_id")
    if not isinstance(tenant_id, str) or not tenant_id.strip():
        raise NoActiveMembershipError(
            "This authenticated session has no selected tenant."
        )

    membership = await session.scalar(
        select(TenantMembership).where(
            TenantMembership.user_id == identity.user_id,
            TenantMembership.tenant_id == tenant_id,
        )
    )
    if membership is None or membership.status != "active":
        raise NoActiveMembershipError(
            "No active membership found for this user and tenant."
        )

    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        raise InactiveTenantError("Tenant not found.")
    if not tenant.is_active:
        raise InactiveTenantError("Tenant is inactive.")

    return TenantUserContext(
        user_id=identity.user_id,
        email=identity.email,
        display_name=identity.display_name,
        tenant_id=tenant.id,
        membership_id=membership.id,
        role=membership.role,  # type: ignore[arg-type]
        auth_method="jwt",
        session_family_id=identity.session_family_id,
        jti=identity.jti,
    )
