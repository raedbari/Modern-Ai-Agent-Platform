"""Session management operations for tenant authentication."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import Settings
from backend.app.db.models import UserRefreshSession


async def create_refresh_session(
    session: AsyncSession,
    user_id: str,
    family_id: str,
    token_hash: str,
    settings: Settings,
    *,
    client_ip: str | None = None,
    user_agent: str | None = None,
) -> UserRefreshSession:
    """Create a new refresh session for a tenant user.
    
    Args:
        session: Database session
        user_id: UUID of the user
        family_id: Session family identifier for replay detection
        token_hash: SHA-256 hash of the refresh token
        settings: Application settings
        client_ip: Client IP address (optional)
        user_agent: User agent string (optional)
    
    Returns:
        Created UserRefreshSession instance
        
    Requirements: 1.10, 1.11, 1.13, 17.1, 17.2
    """
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=settings.jwt_refresh_token_expire_days)
    
    refresh_session = UserRefreshSession(
        id=str(uuid.uuid4()),
        user_id=user_id,
        token_hash=token_hash,
        family_id=family_id,
        issued_at=now,
        expires_at=expires_at,
        revoked_at=None,
        client_ip=client_ip,
        user_agent=user_agent,
    )
    
    session.add(refresh_session)
    await session.flush()
    
    return refresh_session


async def revoke_session_by_token_hash(session: AsyncSession, token_hash: str) -> None:
    """Revoke a refresh session by its token hash.
    
    Args:
        session: Database session
        token_hash: SHA-256 hash of the refresh token
    
    Requirements: 3.3, 5.2, 5.3
    """
    result = await session.execute(
        select(UserRefreshSession).where(UserRefreshSession.token_hash == token_hash)
    )
    refresh_session = result.scalar_one_or_none()
    if refresh_session and refresh_session.revoked_at is None:
        refresh_session.revoked_at = datetime.now(timezone.utc)


async def revoke_session_family(session: AsyncSession, family_id: str) -> None:
    """Revoke all sessions in a token family.
    
    Used for replay detection - when a consumed token is reused,
    all sessions in the family are revoked as a security measure.
    
    Args:
        session: Database session
        family_id: Session family identifier
    
    Requirements: 4.2, 4.3
    """
    result = await session.execute(
        select(UserRefreshSession).where(
            UserRefreshSession.family_id == family_id,
            UserRefreshSession.revoked_at.is_(None)
        )
    )
    for refresh_session in result.scalars():
        refresh_session.revoked_at = datetime.now(timezone.utc)


async def revoke_all_user_sessions(session: AsyncSession, user_id: str) -> None:
    """Revoke all active sessions for a user.
    
    Used for security events like password changes, user deactivation,
    or when user needs to be logged out from all devices.
    
    Args:
        session: Database session
        user_id: UUID of the user
    
    Requirements: 9.1, 9.2, 10.1, 10.2
    """
    result = await session.execute(
        select(UserRefreshSession).where(
            UserRefreshSession.user_id == user_id,
            UserRefreshSession.revoked_at.is_(None)
        )
    )
    for refresh_session in result.scalars():
        refresh_session.revoked_at = datetime.now(timezone.utc)
