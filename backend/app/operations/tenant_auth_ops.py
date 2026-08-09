"""Authentication operations for tenant users."""
from __future__ import annotations


class InvalidCredentialsError(Exception):
    """Email unknown or password mismatch."""


class InactiveUserError(Exception):
    """User is_active=False."""


class UnverifiedEmailError(Exception):
    """email_verified_at is NULL."""


class NoActiveMembershipError(Exception):
    """No active TenantMembership."""


class SessionNotFoundError(Exception):
    """Refresh token invalid."""


class ReplayDetectedError(Exception):
    """Revoked token re-presented."""


import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.admin_password import verify_admin_password
from backend.app.auth.tenant_jwt import create_access_token, generate_refresh_token, hash_token
from backend.app.core.config import Settings
from backend.app.db.models import User, Tenant, TenantMembership
from backend.app.operations.tenant_session_ops import create_refresh_session


# Dummy hash for constant-time verification to prevent timing attacks
DUMMY_HASH = "$argon2id$v=19$m=65536,t=2,p=1$randomsalthere$hashhere"


async def authenticate_tenant_user(
    session: AsyncSession,
    *,
    email: str,
    plain_password: str,
    settings: Settings,
    client_ip: str | None = None,
    user_agent: str | None = None,
) -> tuple[str, str]:
    """Authenticate verified customer identity and create a session pair."""
    normalized_email = email.strip().casefold()

    user = await session.scalar(
        select(User).where(User.normalized_email == normalized_email)
    )
    if user is None:
        verify_admin_password(plain_password, DUMMY_HASH)
        raise InvalidCredentialsError("Invalid credentials.")
    if not verify_admin_password(plain_password, user.hashed_password):
        raise InvalidCredentialsError("Invalid credentials.")
    if user.email_verified_at is None:
        raise UnverifiedEmailError("Email address has not been verified.")
    if not user.is_active:
        raise InactiveUserError("User account is inactive.")

    rows = (
        await session.execute(
            select(TenantMembership, Tenant)
            .join(Tenant, Tenant.id == TenantMembership.tenant_id)
            .where(
                TenantMembership.user_id == user.id,
                TenantMembership.status == "active",
                Tenant.is_active.is_(True),
            )
            .order_by(TenantMembership.created_at.asc())
            .limit(2)
        )
    ).all()

    # Phase 1 automatically selects the tenant only when it is unambiguous.
    tenant_id = rows[0][1].id if len(rows) == 1 else None

    family_id = str(uuid.uuid4())
    refresh_token = generate_refresh_token()
    await create_refresh_session(
        session,
        user_id=user.id,
        family_id=family_id,
        token_hash=hash_token(refresh_token),
        settings=settings,
        client_ip=client_ip,
        user_agent=user_agent,
    )

    access_token = create_access_token(
        user_id=user.id,
        settings=settings,
        session_family_id=family_id,
        tenant_id=tenant_id,
    )
    user.last_login_at = datetime.now(timezone.utc)
    return access_token, refresh_token

async def rotate_refresh_token(
    session: AsyncSession,
    *,
    raw_refresh_token: str,
    settings: Settings,
    client_ip: str | None = None,
    user_agent: str | None = None,
) -> tuple[str, str]:
    """Rotate a customer refresh token without requiring tenant membership."""
    from backend.app.db.models import UserRefreshSession
    from backend.app.operations.tenant_session_ops import revoke_session_family

    token_hash = hash_token(raw_refresh_token)
    refresh_session = await session.scalar(
        select(UserRefreshSession)
        .where(UserRefreshSession.token_hash == token_hash)
        .with_for_update()
    )
    if refresh_session is None:
        raise SessionNotFoundError("Refresh token not found.")

    if refresh_session.revoked_at is not None:
        await revoke_session_family(session, refresh_session.family_id)
        await session.commit()
        raise ReplayDetectedError("Security alert: session has been compromised.")

    now = datetime.now(timezone.utc)
    expires_at = refresh_session.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        raise SessionNotFoundError("Refresh token has expired.")

    user = await session.get(User, refresh_session.user_id)
    if user is None or not user.is_active:
        raise InactiveUserError("User account is inactive.")

    rows = (
        await session.execute(
            select(TenantMembership, Tenant)
            .join(Tenant, Tenant.id == TenantMembership.tenant_id)
            .where(
                TenantMembership.user_id == user.id,
                TenantMembership.status == "active",
                Tenant.is_active.is_(True),
            )
            .order_by(TenantMembership.created_at.asc())
            .limit(2)
        )
    ).all()
    tenant_id = rows[0][1].id if len(rows) == 1 else None

    refresh_session.revoked_at = now
    new_refresh_token = generate_refresh_token()
    await create_refresh_session(
        session,
        user_id=user.id,
        family_id=refresh_session.family_id,
        token_hash=hash_token(new_refresh_token),
        settings=settings,
        client_ip=client_ip,
        user_agent=user_agent,
    )

    new_access_token = create_access_token(
        user_id=user.id,
        settings=settings,
        session_family_id=refresh_session.family_id,
        tenant_id=tenant_id,
    )
    return new_access_token, new_refresh_token

async def revoke_session(
    session: AsyncSession,
    *,
    raw_refresh_token: str,
    user_id: str,
    family_id: str | None = None,
) -> None:
    """Revoke a specific refresh token session.
    
    This operation is idempotent - returns normally if session already revoked or not found.
    
    Args:
        session: Database session
        raw_refresh_token: Raw refresh token to revoke
        user_id: User ID for validation
        family_id: Optional family ID for additional validation
    
    Requirements: 5.1-5.4
    """
    from backend.app.db.models import UserRefreshSession
    
    # Compute token hash
    token_hash = hash_token(raw_refresh_token)
    
    # Query the session
    query = select(UserRefreshSession).where(
        UserRefreshSession.token_hash == token_hash,
        UserRefreshSession.user_id == user_id
    )
    
    # Add family_id filter if provided
    if family_id is not None:
        query = query.where(UserRefreshSession.family_id == family_id)
    
    result = await session.execute(query)
    refresh_session = result.scalar_one_or_none()
    
    # Idempotent - return normally if not found or already revoked
    if refresh_session is None or refresh_session.revoked_at is not None:
        return
    
    # Mark as revoked
    refresh_session.revoked_at = datetime.now(timezone.utc)
