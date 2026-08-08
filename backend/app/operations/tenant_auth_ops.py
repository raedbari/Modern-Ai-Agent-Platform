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
    """Authenticate tenant user and create new session pair.
    
    Steps:
    1. Normalize email to lowercase
    2. Lookup User by normalized_email
    3. Perform constant-time password verification
    4. Check email_verified_at IS NOT NULL
    5. Check user.is_active = True
    6. Query for active TenantMembership
    7. Check membership.status = 'active'
    8. Check tenant.is_active = True
    9. Generate refresh token and family_id
    10. Store SHA-256 token hash in UserRefreshSession
    11. Create access token
    12. Update user.last_login_at
    
    Args:
        session: Database session
        email: User email address
        plain_password: Plain text password
        settings: Application settings
        client_ip: Client IP address (optional)
        user_agent: User agent string (optional)
    
    Returns:
        Tuple of (access_token, refresh_token)
        
    Raises:
        InvalidCredentialsError: Email unknown or password mismatch
        UnverifiedEmailError: Email not verified
        InactiveUserError: User is not active
        NoActiveMembershipError: No active membership or inactive tenant
    
    Requirements: 1.2-1.14
    """
    # 1. Normalize email to lowercase
    normalized_email = email.strip().lower()
    
    # 2. Lookup User by normalized_email
    result = await session.execute(
        select(User).where(User.normalized_email == normalized_email)
    )
    user = result.scalar_one_or_none()
    
    # 3. Constant-time password verification (use dummy hash if user not found)
    if user is None:
        verify_admin_password(plain_password, DUMMY_HASH)
        raise InvalidCredentialsError("Invalid credentials.")
    
    if not verify_admin_password(plain_password, user.hashed_password):
        raise InvalidCredentialsError("Invalid credentials.")
    
    # 4. Check email_verified_at IS NOT NULL
    if user.email_verified_at is None:
        raise UnverifiedEmailError("Email address has not been verified.")
    
    # 5. Check user.is_active = True
    if not user.is_active:
        raise InactiveUserError("User account is inactive.")
    
    # 6-7. Query for active TenantMembership
    membership_result = await session.execute(
        select(TenantMembership).where(
            TenantMembership.user_id == user.id,
            TenantMembership.status == "active"
        )
    )
    membership = membership_result.scalar_one_or_none()
    
    if membership is None:
        raise NoActiveMembershipError("No active tenant membership found.")
    
    # 8. Check tenant.is_active = True
    tenant_result = await session.execute(
        select(Tenant).where(Tenant.id == membership.tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()
    
    if tenant is None or not tenant.is_active:
        raise NoActiveMembershipError("Tenant is not active.")
    
    # 9. Generate refresh token and family_id
    family_id = str(uuid.uuid4())
    refresh_token = generate_refresh_token()
    token_hash = hash_token(refresh_token)
    
    # 10. Store SHA-256 token hash in UserRefreshSession
    await create_refresh_session(
        session,
        user_id=user.id,
        family_id=family_id,
        token_hash=token_hash,
        settings=settings,
        client_ip=client_ip,
        user_agent=user_agent,
    )
    
    # 11. Create access token with user_id, tenant_id, family_id
    access_token = create_access_token(
        user_id=user.id,
        tenant_id=tenant.id,
        settings=settings,
        session_family_id=family_id,
    )
    
    # 12. Update user.last_login_at
    user.last_login_at = datetime.now(timezone.utc)
    
    return (access_token, refresh_token)



async def rotate_refresh_token(
    session: AsyncSession,
    *,
    raw_refresh_token: str,
    settings: Settings,
    client_ip: str | None = None,
    user_agent: str | None = None,
) -> tuple[str, str]:
    """Rotate refresh token with replay detection.
    
    Steps:
    1. Compute SHA-256 hash of raw token
    2. Query UserRefreshSession with FOR UPDATE lock
    3. If revoked_at IS NOT NULL: detect replay attack, revoke entire family
    4. Check expires_at > now
    5. Load User and verify is_active = True
    6. Load TenantMembership and verify status = 'active'
    7. Load Tenant and verify is_active = True
    8. Mark old session as consumed (set revoked_at)
    9. Create new session with same family_id
    10. Generate new access token
    
    Args:
        session: Database session
        raw_refresh_token: Raw refresh token from client
        settings: Application settings
        client_ip: Client IP address (optional)
        user_agent: User agent string (optional)
    
    Returns:
        Tuple of (new_access_token, new_refresh_token)
        
    Raises:
        SessionNotFoundError: Token not found in database
        ReplayDetectedError: Token already consumed (replay attack)
        InactiveUserError: User is not active
        NoActiveMembershipError: No active membership or inactive tenant
    
    Requirements: 3.1-3.9, 4.1-4.5
    """
    from backend.app.db.models import UserRefreshSession
    from backend.app.operations.tenant_session_ops import revoke_session_family
    
    # 1. Compute SHA-256 hash
    token_hash = hash_token(raw_refresh_token)
    
    # 2. Query with FOR UPDATE lock
    result = await session.execute(
        select(UserRefreshSession)
        .where(UserRefreshSession.token_hash == token_hash)
        .with_for_update()
    )
    refresh_session = result.scalar_one_or_none()
    
    if refresh_session is None:
        raise SessionNotFoundError("Refresh token not found.")
    
    # 3. Replay detection - if already revoked, this is a replay attack
    if refresh_session.revoked_at is not None:
        # Log security event
        import logging
        logger = logging.getLogger(__name__)
        logger.warning(
            f"SECURITY: Replay attack detected. "
            f"family_id={refresh_session.family_id}, "
            f"user_id={refresh_session.user_id}, "
            f"client_ip={client_ip}, "
            f"user_agent={user_agent}"
        )
        
        # Revoke entire session family
        await revoke_session_family(session, refresh_session.family_id)
        await session.commit()
        
        raise ReplayDetectedError("Security alert: session has been compromised.")
    
    # 4. Check not expired
    now = datetime.now(timezone.utc)
    if refresh_session.expires_at <= now:
        raise SessionNotFoundError("Refresh token has expired.")
    
    # 5. Load User and check is_active
    user_result = await session.execute(
        select(User).where(User.id == refresh_session.user_id)
    )
    user = user_result.scalar_one_or_none()
    
    if user is None or not user.is_active:
        raise InactiveUserError("User account is inactive.")
    
    # 6. Load TenantMembership and check status = 'active'
    membership_result = await session.execute(
        select(TenantMembership).where(
            TenantMembership.user_id == user.id,
            TenantMembership.status == "active"
        )
    )
    membership = membership_result.scalar_one_or_none()
    
    if membership is None:
        raise NoActiveMembershipError("No active tenant membership found.")
    
    # 7. Load Tenant and check is_active
    tenant_result = await session.execute(
        select(Tenant).where(Tenant.id == membership.tenant_id)
    )
    tenant = tenant_result.scalar_one_or_none()
    
    if tenant is None or not tenant.is_active:
        raise NoActiveMembershipError("Tenant is not active.")
    
    # 8. Mark old session as consumed
    refresh_session.revoked_at = now
    
    # 9. Create new session with same family_id
    new_refresh_token = generate_refresh_token()
    new_token_hash = hash_token(new_refresh_token)
    
    await create_refresh_session(
        session,
        user_id=user.id,
        family_id=refresh_session.family_id,  # Same family!
        token_hash=new_token_hash,
        settings=settings,
        client_ip=client_ip,
        user_agent=user_agent,
    )
    
    # 10. Generate new access token
    new_access_token = create_access_token(
        user_id=user.id,
        tenant_id=tenant.id,
        settings=settings,
        session_family_id=refresh_session.family_id,
    )
    
    return (new_access_token, new_refresh_token)



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
