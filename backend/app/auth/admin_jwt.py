"""JWT access-token creation, decoding, and jti revocation for admin accounts.

Public API
----------
create_access_token   -- sign a new HS256 JWT and return the encoded string
decode_access_token   -- verify and decode a token, returning AdminContext
revoke_jti            -- add a jti to the in-process revocation cache

The revocation cache is intentionally in-memory only.  Its TTL equals the
access-token lifetime, so the worst-case exposure window after a process
restart is bounded by that lifetime (default 15 minutes).

No token value or secret key is ever logged or embedded in an exception.
"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from jwt.exceptions import (
    ExpiredSignatureError,
    InvalidAlgorithmError,
    InvalidSignatureError,
    InvalidTokenError,
)

from backend.app.auth.admin_context import AdminContext
from backend.app.core.config import Settings

# ---------------------------------------------------------------------------
# Algorithm constant — never deviate from HS256
# ---------------------------------------------------------------------------

_ALGORITHM = "HS256"

# ---------------------------------------------------------------------------
# In-memory jti revocation cache
# ---------------------------------------------------------------------------
# Structure: { jti: expiry_datetime_utc }
# A revoked jti is kept until its natural expiry, after which it cannot
# be presented to a running server anyway (token is expired).
# Thread-safety: a single Lock guards all mutations.

_revoked_jtis: dict[str, datetime] = {}
_cache_lock = threading.Lock()


def _purge_expired_jtis(now: datetime) -> None:
    """Remove entries whose access token has already expired.

    Called on every cache mutation to prevent unbounded growth.
    Must be called while *_cache_lock* is held.
    """
    expired_keys = [k for k, exp in _revoked_jtis.items() if exp <= now]
    for k in expired_keys:
        del _revoked_jtis[k]


def revoke_jti(jti: str, settings: Settings) -> None:
    """Add *jti* to the revocation cache.

    The entry expires after the configured access-token lifetime so the
    cache cannot grow without bound during normal operation.
    """
    ttl_minutes = settings.jwt_access_token_expire_minutes
    now = datetime.now(timezone.utc)
    expiry = now + timedelta(minutes=ttl_minutes)

    with _cache_lock:
        _purge_expired_jtis(now)
        _revoked_jtis[jti] = expiry


def _is_revoked(jti: str) -> bool:
    """Return True if *jti* is present in the revocation cache."""
    now = datetime.now(timezone.utc)
    with _cache_lock:
        _purge_expired_jtis(now)
        return jti in _revoked_jtis


# ---------------------------------------------------------------------------
# Token creation
# ---------------------------------------------------------------------------

def create_access_token(
    admin_id: str,
    username: str,
    role: str,
    settings: Settings,
) -> str:
    """Create and sign a new HS256 JWT access token.

    Claims
    ------
    sub   -- admin_id (subject)
    role  -- the admin role string
    jti   -- unique UUID4 token identifier
    iat   -- issued-at timestamp (UTC)
    exp   -- expiry timestamp (UTC, iat + configured lifetime)

    The *username* is included as a non-standard claim ``username`` so
    callers can reconstruct ``AdminContext`` from the token without an
    extra database lookup.
    """
    if settings.jwt_secret_key is None:
        raise ValueError(
            "MAAP_JWT_SECRET_KEY must be configured to issue admin tokens."
        )

    secret = settings.jwt_secret_key.get_secret_value()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.jwt_access_token_expire_minutes)

    payload: dict[str, Any] = {
        "sub": admin_id,
        "username": username,
        "role": role,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": expire,
    }

    return jwt.encode(payload, secret, algorithm=_ALGORITHM)


# ---------------------------------------------------------------------------
# Token decoding and validation
# ---------------------------------------------------------------------------

class AdminTokenError(Exception):
    """Raised when an admin JWT fails any validation step.

    The message is safe to forward to an HTTP 401 response — it never
    contains the raw token value or the signing secret.
    """


def decode_access_token(token: str, settings: Settings) -> AdminContext:
    """Decode and fully validate *token*, returning an ``AdminContext``.

    Validation steps
    ----------------
    1. Decode with algorithm whitelist restricted to HS256.
    2. Verify signature using the configured secret.
    3. Verify ``exp`` — reject expired tokens.
    4. Verify ``iat`` is not in the future (clock-skew tolerance: 30 s).
    5. Verify ``sub`` is a non-empty string.
    6. Verify ``role`` is present.
    7. Verify ``jti`` is present and not in the revocation cache.

    Raises ``AdminTokenError`` for every failure mode.  The raw token and
    secret are never embedded in the exception message.
    """
    if settings.jwt_secret_key is None:
        raise AdminTokenError("JWT authentication is not configured.")

    secret = settings.jwt_secret_key.get_secret_value()

    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            secret,
            algorithms=[_ALGORITHM],     # explicit whitelist — no "none"
            options={
                "require": ["sub", "role", "jti", "iat", "exp"],
                "verify_exp": True,
                "verify_iat": True,
                "verify_signature": True,
            },
        )
    except ExpiredSignatureError:
        raise AdminTokenError("Token has expired.")
    except InvalidAlgorithmError:
        raise AdminTokenError("Token uses an unsupported algorithm.")
    except InvalidSignatureError:
        raise AdminTokenError("Token signature is invalid.")
    except InvalidTokenError:
        # Covers missing claims, malformed tokens, decode errors, etc.
        raise AdminTokenError("Token is invalid.")

    # --- iat clock-skew guard (30 second tolerance) ---------------------
    iat = payload.get("iat")
    if isinstance(iat, (int, float)):
        issued_at = datetime.fromtimestamp(iat, tz=timezone.utc)
        if issued_at > datetime.now(timezone.utc) + timedelta(seconds=30):
            raise AdminTokenError("Token issued-at time is in the future.")

    # --- sub must be a non-empty string ---------------------------------
    sub = payload.get("sub", "")
    if not isinstance(sub, str) or not sub.strip():
        raise AdminTokenError("Token subject claim is missing or empty.")

    # --- role must be present -------------------------------------------
    role = payload.get("role", "")
    if not isinstance(role, str) or not role.strip():
        raise AdminTokenError("Token role claim is missing or empty.")

    # --- username (non-standard, optional but expected) -----------------
    username = payload.get("username", "")
    if not isinstance(username, str):
        username = ""

    # --- jti revocation check -------------------------------------------
    jti = payload.get("jti", "")
    if not jti:
        raise AdminTokenError("Token identifier (jti) is missing.")
    if _is_revoked(jti):
        raise AdminTokenError("Token has been revoked.")

    return AdminContext(
        admin_id=sub,
        username=username,
        role=role,  # type: ignore[arg-type]
    )
