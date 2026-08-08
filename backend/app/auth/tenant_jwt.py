"""JWT access-token creation, decoding, and jti revocation for tenant user accounts.

Public API
----------
create_access_token   -- sign a new HS256 JWT and return the encoded string
decode_access_token   -- verify and decode a token, returning claims dict
revoke_jti            -- add a jti to the in-process revocation cache
generate_refresh_token -- generate a cryptographically secure refresh token
hash_token            -- compute SHA-256 hash of a token for secure storage

The revocation cache is intentionally in-memory only.  Its TTL equals the
access-token lifetime, so the worst-case exposure window after a process
restart is bounded by that lifetime (default 15 minutes).

No token value or secret key is ever logged or embedded in an exception.
"""

from __future__ import annotations

import hashlib
import secrets
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
    user_id: str,
    tenant_id: str,
    settings: Settings,
    *,
    session_family_id: str | None = None,
) -> str:
    """Create and sign a new HS256 JWT access token for tenant user.

    Claims
    ------
    sub        -- user_id (subject)
    tenant_id  -- tenant UUID
    jti        -- unique UUID4 token identifier
    sid        -- session family identifier (if provided)
    iat        -- issued-at timestamp (UTC)
    exp        -- expiry timestamp (UTC, iat + configured lifetime)

    The role is NOT included in JWT claims. The authoritative role comes
    from the database TenantMembership.role field during validation.
    """
    if settings.jwt_secret_key is None:
        raise ValueError(
            "MAAP_JWT_SECRET_KEY must be configured to issue tenant tokens."
        )

    secret = settings.jwt_secret_key.get_secret_value()
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.jwt_access_token_expire_minutes)

    payload: dict[str, Any] = {
        "sub": user_id,
        "tenant_id": tenant_id,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": expire,
    }
    if session_family_id is not None:
        payload["sid"] = session_family_id

    return jwt.encode(payload, secret, algorithm=_ALGORITHM)


# ---------------------------------------------------------------------------
# Token decoding and validation
# ---------------------------------------------------------------------------

class TenantTokenError(Exception):
    """Raised when a tenant JWT fails any validation step.

    The message is safe to forward to an HTTP 401 response — it never
    contains the raw token value or the signing secret.
    """


def decode_access_token(token: str, settings: Settings) -> dict[str, Any]:
    """Decode and fully validate *token*, returning claims dict.

    Validation steps
    ----------------
    1. Decode with algorithm whitelist restricted to HS256.
    2. Verify signature using the configured secret.
    3. Verify ``exp`` — reject expired tokens.
    4. Verify ``iat`` is not in the future (clock-skew tolerance: 30 s).
    5. Verify ``sub`` is a non-empty string.
    6. Verify ``tenant_id`` is present.
    7. Verify ``jti`` is present and not in the revocation cache.

    Raises ``TenantTokenError`` for every failure mode.  The raw token and
    secret are never embedded in the exception message.
    """
    if settings.jwt_secret_key is None:
        raise TenantTokenError("JWT authentication is not configured.")

    secret = settings.jwt_secret_key.get_secret_value()

    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            secret,
            algorithms=[_ALGORITHM],     # explicit whitelist — no "none"
            options={
                "require": ["sub", "tenant_id", "jti", "iat", "exp"],
                "verify_exp": True,
                "verify_iat": True,
                "verify_signature": True,
            },
        )
    except ExpiredSignatureError:
        raise TenantTokenError("Token has expired.")
    except InvalidAlgorithmError:
        raise TenantTokenError("Token uses an unsupported algorithm.")
    except InvalidSignatureError:
        raise TenantTokenError("Token signature is invalid.")
    except InvalidTokenError:
        # Covers missing claims, malformed tokens, decode errors, etc.
        raise TenantTokenError("Token is invalid.")

    # --- iat clock-skew guard (30 second tolerance) ---------------------
    iat = payload.get("iat")
    if isinstance(iat, (int, float)):
        issued_at = datetime.fromtimestamp(iat, tz=timezone.utc)
        if issued_at > datetime.now(timezone.utc) + timedelta(seconds=30):
            raise TenantTokenError("Token issued-at time is in the future.")

    # --- sub must be a non-empty string ---------------------------------
    sub = payload.get("sub", "")
    if not isinstance(sub, str) or not sub.strip():
        raise TenantTokenError("Token subject claim is missing or empty.")

    # --- tenant_id must be present --------------------------------------
    tenant_id = payload.get("tenant_id", "")
    if not isinstance(tenant_id, str) or not tenant_id.strip():
        raise TenantTokenError("Token tenant_id claim is missing or empty.")

    # --- jti revocation check -------------------------------------------
    jti = payload.get("jti", "")
    if not isinstance(jti, str) or not jti:
        raise TenantTokenError("Token identifier (jti) is missing.")
    if _is_revoked(jti):
        raise TenantTokenError("Token has been revoked.")

    # --- sid validation (optional claim) --------------------------------
    session_family_id = payload.get("sid")
    if session_family_id is not None and (
        not isinstance(session_family_id, str)
        or not session_family_id.strip()
    ):
        raise TenantTokenError("Token session claim is invalid.")

    return payload


# ---------------------------------------------------------------------------
# Refresh token utilities
# ---------------------------------------------------------------------------

def generate_refresh_token() -> str:
    """Generate a cryptographically secure refresh token for tenant users.
    
    Format: maap_usr_{32_bytes_urlsafe_base64}
    
    The token contains 256 bits of entropy from a cryptographically secure
    random source, suitable for use as a long-lived refresh token. The prefix
    'maap_usr_' distinguishes tenant user tokens from admin tokens.
    
    Returns:
        str: A refresh token string (approximately 50 characters).
    
    Example:
        >>> token = generate_refresh_token()
        >>> token.startswith('maap_usr_')
        True
        >>> len(token) > 40
        True
    """
    random_part = secrets.token_urlsafe(32)
    return f"maap_usr_{random_part}"


def hash_token(raw_token: str) -> str:
    """Compute SHA-256 hash of a token for secure storage in database.
    
    The raw token is hashed using SHA-256 to produce a 64-character
    hexadecimal digest. This ensures that even if the database is
    compromised, raw tokens cannot be recovered.
    
    Args:
        raw_token: The raw token string to hash.
    
    Returns:
        str: A 64-character hexadecimal SHA-256 hash digest.
    
    Example:
        >>> token = "maap_usr_example_token_value"
        >>> token_hash = hash_token(token)
        >>> len(token_hash)
        64
        >>> token_hash == hash_token(token)  # Deterministic
        True
    """
    token_bytes = raw_token.encode("utf-8")
    hash_obj = hashlib.sha256(token_bytes)
    return hash_obj.hexdigest()
