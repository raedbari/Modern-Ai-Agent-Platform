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


async def validate_tenant_user_context(
    token: str,
    session: AsyncSession,
    settings: Settings,
) -> TenantUserContext:
    """
    Perform 10-step authoritative database validation for tenant authentication.
    
    Validation Steps:
    1. Verify JWT cryptographic signature
    2. Extract user_id from JWT claims
    3. Query database to confirm User record exists
    4. Verify user.is_active is True
    5. Extract tenant_id and family_id from JWT claims
    6. Query for UserRefreshSession in the claimed family_id
    7. Verify session is unexpired and revoked_at is NULL
    8. Query for TenantMembership matching user_id and tenant_id
    9. Verify membership.status is 'active'
    10. Query Tenant record and verify tenant.is_active is True
    
    Args:
        token: JWT access token from Authorization header
        session: AsyncSession for database queries
        settings: Application settings
    
    Returns:
        TenantUserContext with authoritative role from database
    
    Raises:
        InvalidTokenError: If JWT validation fails
        InactiveUserError: If user is not active
        InvalidSessionError: If session is invalid or revoked
        NoActiveMembershipError: If no active membership found
        InactiveTenantError: If tenant is not active
    """
    # -----------------------------------------------------------------------
    # Step 1: Verify JWT cryptographic signature and decode claims
    # -----------------------------------------------------------------------
    if settings.jwt_secret_key is None:
        raise InvalidTokenError("JWT authentication is not configured.")
    
    secret = settings.jwt_secret_key.get_secret_value()
    
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            secret,
            algorithms=[_ALGORITHM],  # explicit whitelist - no "none"
            options={
                "require": ["sub", "tenant_id", "jti", "iat", "exp"],
                "verify_exp": True,
                "verify_iat": True,
                "verify_signature": True,
            },
        )
    except ExpiredSignatureError:
        raise InvalidTokenError("Token has expired.")
    except InvalidAlgorithmError:
        raise InvalidTokenError("Token uses an unsupported algorithm.")
    except InvalidSignatureError:
        raise InvalidTokenError("Token signature is invalid.")
    except (JWTInvalidTokenError, Exception):
        # Covers missing claims, malformed tokens, decode errors, etc.
        raise InvalidTokenError("Token is invalid.")
    
    # -----------------------------------------------------------------------
    # Step 2: Extract user_id from JWT claims
    # -----------------------------------------------------------------------
    user_id = payload.get("sub", "")
    if not isinstance(user_id, str) or not user_id.strip():
        raise InvalidTokenError("Token subject claim is missing or empty.")
    
    # -----------------------------------------------------------------------
    # Step 3: Query database to confirm User record exists
    # -----------------------------------------------------------------------
    result = await session.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise InvalidTokenError("User not found.")
    
    # -----------------------------------------------------------------------
    # Step 4: Verify user.is_active is True
    # -----------------------------------------------------------------------
    if not user.is_active:
        raise InactiveUserError("User account is inactive.")
    
    # -----------------------------------------------------------------------
    # Step 5: Extract tenant_id and family_id from JWT claims
    # -----------------------------------------------------------------------
    tenant_id = payload.get("tenant_id", "")
    if not isinstance(tenant_id, str) or not tenant_id.strip():
        raise InvalidTokenError("Token tenant_id claim is missing or empty.")
    
    family_id = payload.get("sid")
    jti = payload.get("jti", "")
    
    # -----------------------------------------------------------------------
    # Step 6: Query for UserRefreshSession in the claimed family_id
    # -----------------------------------------------------------------------
    # Only validate session if family_id is present in JWT claims
    if family_id is not None:
        if not isinstance(family_id, str) or not family_id.strip():
            raise InvalidTokenError("Token session claim is invalid.")
        
        session_result = await session.execute(
            select(UserRefreshSession).where(
                UserRefreshSession.user_id == user_id,
                UserRefreshSession.family_id == family_id,
                UserRefreshSession.revoked_at.is_(None),
            )
        )
        refresh_session = session_result.scalar_one_or_none()
        
        if refresh_session is None:
            raise InvalidSessionError("No active session found for this token family.")
        
        # -------------------------------------------------------------------
        # Step 7: Verify session is unexpired
        # -------------------------------------------------------------------
        now = datetime.now(timezone.utc)
        if refresh_session.expires_at <= now:
            raise InvalidSessionError("Session has expired.")
    
    # -----------------------------------------------------------------------
    # Step 8: Query for TenantMembership matching user_id and tenant_id
    # -----------------------------------------------------------------------
    membership_result = await session.execute(
        select(TenantMembership).where(
            TenantMembership.user_id == user_id,
            TenantMembership.tenant_id == tenant_id,
        )
    )
    membership = membership_result.scalar_one_or_none()
    
    if membership is None:
        raise NoActiveMembershipError(
            "No membership found for this user and tenant."
        )
    
    # -----------------------------------------------------------------------
    # Step 9: Verify membership.status is 'active'
    # -----------------------------------------------------------------------
    if membership.status != "active":
        raise NoActiveMembershipError(
            f"Membership status is '{membership.status}', not 'active'."
        )
    
    # -----------------------------------------------------------------------
    # Step 10: Query Tenant record and verify tenant.is_active is True
    # -----------------------------------------------------------------------
    tenant_result = await session.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()
    
    if tenant is None:
        raise InactiveTenantError("Tenant not found.")
    
    if not tenant.is_active:
        raise InactiveTenantError("Tenant is inactive.")
    
    # -----------------------------------------------------------------------
    # Return TenantUserContext with authoritative role from database
    # -----------------------------------------------------------------------
    return TenantUserContext(
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        tenant_id=tenant.id,
        membership_id=membership.id,
        role=membership.role,  # type: ignore[arg-type]
        auth_method="jwt",
        session_family_id=family_id,
        jti=jti if jti else None,
    )
