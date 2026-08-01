"""Service-layer operations for admin authentication.

This module contains pure business-logic functions with no HTTP concerns.
Each function accepts an open AsyncSession and returns domain objects or
raises typed exceptions.  Callers are responsible for commit/rollback.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.admin_jwt import create_access_token
from backend.app.auth.admin_password import needs_rehash, verify_admin_password
from backend.app.core.config import Settings
from backend.app.db.models import AdminRefreshSession, AdminUser
from backend.app.services.audit import AuditService


# ---------------------------------------------------------------------------
# Typed exceptions
# ---------------------------------------------------------------------------

class InvalidCredentialsError(Exception):
    """Raised when username is unknown or password does not match."""


class InactiveAdminError(Exception):
    """Raised when the admin account exists but is deactivated."""


class SessionNotFoundError(Exception):
    """Raised when a refresh token resolves to no active session."""


class ReplayDetectedError(Exception):
    """Raised when a revoked refresh token is re-presented."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _hash_refresh_token(raw_token: str) -> str:
    """Return the SHA-256 hex digest of a raw refresh token."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def _generate_refresh_token() -> str:
    """Generate a cryptographically strong opaque refresh token."""
    return f"maap_adm_{secrets.token_urlsafe(32)}"


async def _get_admin_by_username(
    session: AsyncSession,
    username: str,
) -> AdminUser | None:
    return await session.scalar(
        select(AdminUser).where(AdminUser.username == username)
    )


# ---------------------------------------------------------------------------
# authenticate_admin
# ---------------------------------------------------------------------------

async def authenticate_admin(
    session: AsyncSession,
    *,
    username: str,
    plain_password: str,
    settings: Settings,
    client_ip: str | None = None,
    user_agent: str | None = None,
) -> tuple[str, str]:
    """Verify credentials and create a new session pair.

    Returns
    -------
    tuple[access_token, refresh_token]
        Both tokens as plain strings.

    Raises
    ------
    InvalidCredentialsError
        Username unknown or password mismatch.
    InactiveAdminError
        Account exists but is deactivated.
    """
    admin = await _get_admin_by_username(session, username)

    # --- authentication -------------------------------------------------
    # Use a constant-time stub verify when admin is None to prevent
    # timing-based username enumeration.
    if admin is None:
        # Deliberate dummy verify — discards result, always fails below.
        verify_admin_password(plain_password, "$argon2id$v=19$m=8192,t=1,p=1"
                              "$AAAAAAAAAAAAAAAAAAAAAA$AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
        await AuditService.write(
            session,
            event_type="login_failure",
            outcome="failure",
            admin_id=None,
            client_ip=client_ip,
            detail={"reason": "unknown_username"},
        )
        raise InvalidCredentialsError("Invalid credentials.")

    if not verify_admin_password(plain_password, admin.hashed_password):
        await AuditService.write(
            session,
            event_type="login_failure",
            outcome="failure",
            admin_id=admin.id,
            client_ip=client_ip,
            detail={"reason": "wrong_password"},
        )
        raise InvalidCredentialsError("Invalid credentials.")

    if not admin.is_active:
        await AuditService.write(
            session,
            event_type="login_failure",
            outcome="failure",
            admin_id=admin.id,
            client_ip=client_ip,
            detail={"reason": "account_inactive"},
        )
        raise InactiveAdminError("Account is not active.")

    # --- optional hash upgrade (transparent rehash) ----------------------
    if needs_rehash(admin.hashed_password, settings):
        from backend.app.auth.admin_password import hash_admin_password
        admin.hashed_password = hash_admin_password(plain_password, settings)

    # --- issue tokens ----------------------------------------------------
    access_token = create_access_token(
        admin_id=admin.id,
        username=admin.username,
        role=admin.role,
        settings=settings,
    )

    raw_refresh = _generate_refresh_token()
    family_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=settings.jwt_refresh_token_expire_days)

    session.add(
        AdminRefreshSession(
            id=str(uuid.uuid4()),
            admin_id=admin.id,
            token_hash=_hash_refresh_token(raw_refresh),
            family_id=family_id,
            issued_at=now,
            expires_at=expires_at,
            client_ip=client_ip,
            user_agent=user_agent,
        )
    )

    # --- update last_login_at -------------------------------------------
    admin.last_login_at = now

    await AuditService.write(
        session,
        event_type="login_success",
        outcome="success",
        admin_id=admin.id,
        client_ip=client_ip,
    )

    return access_token, raw_refresh


# ---------------------------------------------------------------------------
# rotate_refresh_token
# ---------------------------------------------------------------------------

async def rotate_refresh_token(
    session: AsyncSession,
    *,
    raw_refresh_token: str,
    settings: Settings,
    client_ip: str | None = None,
    user_agent: str | None = None,
) -> tuple[str, str]:
    """Rotate a refresh token: revoke the presented one, issue a replacement.

    Implements refresh-token rotation with replay detection:
    - If the token is unknown → SessionNotFoundError
    - If the token is already revoked → ReplayDetectedError (entire family
      is revoked immediately as a security response)
    - If the token is expired → SessionNotFoundError
    - If the admin is inactive → InactiveAdminError
    - On success → new (access_token, refresh_token) pair, same family_id

    The caller must commit the session after a successful return.

    Returns
    -------
    tuple[access_token, refresh_token]
    """
    token_hash = _hash_refresh_token(raw_refresh_token)
    now = datetime.now(timezone.utc)

    # --- look up the presented session -----------------------------------
    presented = await session.scalar(
        select(AdminRefreshSession).where(
            AdminRefreshSession.token_hash == token_hash
        )
    )

    if presented is None:
        raise SessionNotFoundError("Refresh token not found.")

    # --- replay detection ------------------------------------------------
    # A revoked token being re-presented means a stolen token is in use.
    # Revoke the entire family immediately.
    if presented.revoked_at is not None:
        await _revoke_family(session, family_id=presented.family_id, now=now)
        await AuditService.write(
            session,
            event_type="token_replay_detected",
            outcome="failure",
            admin_id=presented.admin_id,
            client_ip=client_ip,
            detail={"family_id": presented.family_id},
        )
        raise ReplayDetectedError("Replay detected — session family revoked.")

    # --- expiry check ----------------------------------------------------
    expires_at = presented.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if expires_at <= now:
        raise SessionNotFoundError("Refresh token has expired.")

    # --- load admin and check active status ------------------------------
    admin = await session.get(AdminUser, presented.admin_id)
    if admin is None or not admin.is_active:
        raise InactiveAdminError("Admin account is not active.")

    # --- atomic rotation: revoke old, issue new (same family) ------------
    presented.revoked_at = now   # mark old token as rotated/revoked

    new_raw_refresh = _generate_refresh_token()
    new_expires_at = now + timedelta(days=settings.jwt_refresh_token_expire_days)

    session.add(
        AdminRefreshSession(
            id=str(uuid.uuid4()),
            admin_id=admin.id,
            token_hash=_hash_refresh_token(new_raw_refresh),
            family_id=presented.family_id,   # preserve lineage
            issued_at=now,
            expires_at=new_expires_at,
            client_ip=client_ip,
            user_agent=user_agent,
        )
    )

    new_access_token = create_access_token(
        admin_id=admin.id,
        username=admin.username,
        role=admin.role,
        settings=settings,
    )

    await AuditService.write(
        session,
        event_type="token_refreshed",
        outcome="success",
        admin_id=admin.id,
        client_ip=client_ip,
    )

    return new_access_token, new_raw_refresh


async def _revoke_family(
    session: AsyncSession,
    *,
    family_id: str,
    now: datetime,
) -> None:
    """Revoke all non-revoked sessions belonging to *family_id*."""
    active_sessions = list(
        (
            await session.scalars(
                select(AdminRefreshSession).where(
                    AdminRefreshSession.family_id == family_id,
                    AdminRefreshSession.revoked_at.is_(None),
                )
            )
        ).all()
    )
    for sess in active_sessions:
        sess.revoked_at = now
    await session.flush()

# ---------------------------------------------------------------------------
# revoke_session  (T-10 — logout)
# ---------------------------------------------------------------------------

async def revoke_session(
    session: AsyncSession,
    *,
    raw_refresh_token: str,
    admin_id: str,
    client_ip: str | None = None,
) -> None:
    """Revoke the refresh session identified by *raw_refresh_token*.

    Idempotent — if the session is already revoked or not found the
    function returns normally (no error raised).  This prevents leaking
    information about session state to callers.

    The caller must commit the session after a successful return.
    """
    token_hash = _hash_refresh_token(raw_refresh_token)
    now = datetime.now(timezone.utc)

    presented = await session.scalar(
        select(AdminRefreshSession).where(
            AdminRefreshSession.token_hash == token_hash,
            AdminRefreshSession.admin_id == admin_id,
        )
    )

    if presented is not None and presented.revoked_at is None:
        presented.revoked_at = now
        await session.flush()

    await AuditService.write(
        session,
        event_type="logout",
        outcome="success",
        admin_id=admin_id,
        client_ip=client_ip,
    )


# ---------------------------------------------------------------------------
# change_password  (T-12)
# ---------------------------------------------------------------------------

class WeakPasswordError(Exception):
    """Raised when the new password does not meet strength requirements."""


class WrongCurrentPasswordError(Exception):
    """Raised when the supplied current password does not match."""


_PASSWORD_SPECIAL_CHARS = set("!@#$%^&*()_+-=[]{}|;':\",./<>?`~\\")


def _validate_password_strength(password: str) -> None:
    """Raise WeakPasswordError if *password* does not meet requirements.

    Rules (REQ-SEC-005):
    - At least 12 characters
    - At least one uppercase letter
    - At least one digit
    - At least one special character
    """
    if len(password) < 12:
        raise WeakPasswordError(
            "Password must be at least 12 characters long."
        )
    if not any(c.isupper() for c in password):
        raise WeakPasswordError(
            "Password must contain at least one uppercase letter."
        )
    if not any(c.isdigit() for c in password):
        raise WeakPasswordError(
            "Password must contain at least one digit."
        )
    if not any(c in _PASSWORD_SPECIAL_CHARS for c in password):
        raise WeakPasswordError(
            "Password must contain at least one special character."
        )


async def change_password(
    session: AsyncSession,
    *,
    admin_id: str,
    current_password: str,
    new_password: str,
    settings: Settings,
    client_ip: str | None = None,
) -> None:
    """Verify the current password, set a new one, and revoke all sessions.

    Steps
    -----
    1. Load the AdminUser — raises SessionNotFoundError if not found.
    2. Verify current_password — raises WrongCurrentPasswordError on mismatch.
    3. Validate new_password strength — raises WeakPasswordError on failure.
    4. Hash and store the new password.
    5. Revoke all active refresh sessions for the account.
    6. Write a password_changed audit entry.

    The caller must commit the session after a successful return.
    """
    admin = await session.get(AdminUser, admin_id)
    if admin is None:
        raise SessionNotFoundError("Admin account not found.")

    if not verify_admin_password(current_password, admin.hashed_password):
        await AuditService.write(
            session,
            event_type="password_changed",
            outcome="failure",
            admin_id=admin_id,
            client_ip=client_ip,
            detail={"reason": "wrong_current_password"},
        )
        raise WrongCurrentPasswordError("Current password is incorrect.")

    _validate_password_strength(new_password)

    from backend.app.auth.admin_password import hash_admin_password
    admin.hashed_password = hash_admin_password(new_password, settings)

    # Revoke all active refresh sessions.
    now = datetime.now(timezone.utc)
    active_sessions = list(
        (
            await session.scalars(
                select(AdminRefreshSession).where(
                    AdminRefreshSession.admin_id == admin_id,
                    AdminRefreshSession.revoked_at.is_(None),
                )
            )
        ).all()
    )
    for sess in active_sessions:
        sess.revoked_at = now

    await AuditService.write(
        session,
        event_type="password_changed",
        outcome="success",
        admin_id=admin_id,
        client_ip=client_ip,
        detail={"sessions_revoked": len(active_sessions)},
    )
