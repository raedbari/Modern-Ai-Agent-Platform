"""Tests for the admin JWT layer: creation, decoding, and jti revocation."""

from __future__ import annotations

import time
import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from backend.app.auth.admin_jwt import (
    AdminTokenError,
    _revoked_jtis,  # accessed only to reset state between tests
    create_access_token,
    decode_access_token,
    revoke_jti,
)
from backend.app.core.config import Settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TEST_SECRET = "a-test-secret-key-that-is-at-least-32-chars-long!!"


def _settings(
    *,
    secret: str = _TEST_SECRET,
    expire_minutes: int = 15,
) -> Settings:
    """Return a minimal Settings instance for JWT tests."""
    return Settings(
        jwt_secret_key=secret,
        jwt_access_token_expire_minutes=expire_minutes,
        _env_file=None,
    )


def _clear_revocation_cache() -> None:
    """Empty the module-level revocation cache between tests."""
    _revoked_jtis.clear()


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_revocation_cache():
    """Ensure every test starts with a clean revocation cache."""
    _clear_revocation_cache()
    yield
    _clear_revocation_cache()


# ---------------------------------------------------------------------------
# Round-trip: create → decode
# ---------------------------------------------------------------------------

def test_create_and_decode_round_trip() -> None:
    settings = _settings()
    token = create_access_token(
        admin_id="admin-001",
        username="alice",
        role="super_admin",
        settings=settings,
    )

    ctx = decode_access_token(token, settings)

    assert ctx.admin_id == "admin-001"
    assert ctx.username == "alice"
    assert ctx.role == "super_admin"


# ---------------------------------------------------------------------------
# Role claim preserved
# ---------------------------------------------------------------------------

def test_role_claim_is_preserved_for_all_roles() -> None:
    settings = _settings()
    for role in ("super_admin", "operator", "auditor"):
        token = create_access_token(
            admin_id="admin-x",
            username="user-x",
            role=role,
            settings=settings,
        )
        ctx = decode_access_token(token, settings)
        assert ctx.role == role


# ---------------------------------------------------------------------------
# jti uniqueness
# ---------------------------------------------------------------------------

def test_jti_is_unique_per_token() -> None:
    settings = _settings()
    tokens = [
        create_access_token("a", "u", "operator", settings)
        for _ in range(20)
    ]
    # Decode each token and collect all jti values.
    jtis = set()
    for token in tokens:
        payload = jwt.decode(
            token,
            _TEST_SECRET,
            algorithms=["HS256"],
        )
        jtis.add(payload["jti"])

    assert len(jtis) == 20, "Every token must carry a distinct jti"


# ---------------------------------------------------------------------------
# Expired token rejection
# ---------------------------------------------------------------------------

def test_expired_token_is_rejected() -> None:
    # Build a token that expired 1 second ago using PyJWT directly.
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "admin-exp",
        "username": "expired-user",
        "role": "operator",
        "jti": str(uuid.uuid4()),
        "iat": now - timedelta(minutes=20),
        "exp": now - timedelta(seconds=1),
    }
    expired_token = jwt.encode(payload, _TEST_SECRET, algorithm="HS256")
    settings = _settings()

    with pytest.raises(AdminTokenError, match="expired"):
        decode_access_token(expired_token, settings)


# ---------------------------------------------------------------------------
# Invalid signature rejection
# ---------------------------------------------------------------------------

def test_invalid_signature_is_rejected() -> None:
    settings = _settings()
    token = create_access_token("admin-sig", "bob", "auditor", settings)

    # Tamper: sign with a different secret.
    wrong_settings = _settings(secret="wrong-secret-key-that-is-32-plus-chars!!")

    with pytest.raises(AdminTokenError, match="invalid"):
        decode_access_token(token, wrong_settings)


# ---------------------------------------------------------------------------
# Revoked jti rejection
# ---------------------------------------------------------------------------

def test_revoked_jti_is_rejected() -> None:
    settings = _settings()
    token = create_access_token("admin-rev", "carol", "super_admin", settings)

    # Extract jti and revoke it.
    payload = jwt.decode(token, _TEST_SECRET, algorithms=["HS256"])
    revoke_jti(payload["jti"], settings)

    with pytest.raises(AdminTokenError, match="revoked"):
        decode_access_token(token, settings)


# ---------------------------------------------------------------------------
# Non-revoked token remains valid
# ---------------------------------------------------------------------------

def test_non_revoked_token_is_still_valid() -> None:
    settings = _settings()
    token_a = create_access_token("admin-a", "alice", "operator", settings)
    token_b = create_access_token("admin-b", "bob", "auditor", settings)

    # Revoke only token_a.
    payload_a = jwt.decode(token_a, _TEST_SECRET, algorithms=["HS256"])
    revoke_jti(payload_a["jti"], settings)

    # token_b must still decode successfully.
    ctx = decode_access_token(token_b, settings)
    assert ctx.admin_id == "admin-b"


# ---------------------------------------------------------------------------
# Missing jwt_secret_key
# ---------------------------------------------------------------------------

def test_create_token_raises_when_secret_is_not_configured() -> None:
    settings = Settings(jwt_secret_key=None, _env_file=None)

    with pytest.raises(ValueError, match="MAAP_JWT_SECRET_KEY"):
        create_access_token("admin-x", "user-x", "operator", settings)


def test_decode_token_raises_when_secret_is_not_configured() -> None:
    settings_with = _settings()
    token = create_access_token("admin-x", "user-x", "operator", settings_with)

    settings_without = Settings(jwt_secret_key=None, _env_file=None)
    with pytest.raises(AdminTokenError, match="not configured"):
        decode_access_token(token, settings_without)


# ---------------------------------------------------------------------------
# Malformed token
# ---------------------------------------------------------------------------

def test_malformed_token_is_rejected() -> None:
    settings = _settings()

    with pytest.raises(AdminTokenError):
        decode_access_token("this.is.not.a.valid.jwt", settings)


def test_empty_token_is_rejected() -> None:
    settings = _settings()

    with pytest.raises(AdminTokenError):
        decode_access_token("", settings)


# ---------------------------------------------------------------------------
# Token carries required claims
# ---------------------------------------------------------------------------

def test_decoded_payload_contains_required_claims() -> None:
    settings = _settings()
    token = create_access_token("admin-claims", "dave", "operator", settings)

    payload = jwt.decode(token, _TEST_SECRET, algorithms=["HS256"])

    for claim in ("sub", "role", "jti", "iat", "exp", "username"):
        assert claim in payload, f"Missing required claim: {claim}"


def test_jti_claim_is_a_valid_uuid4() -> None:
    settings = _settings()
    token = create_access_token("admin-uuid", "eve", "auditor", settings)

    payload = jwt.decode(token, _TEST_SECRET, algorithms=["HS256"])
    jti = payload["jti"]

    # This raises ValueError if jti is not a valid UUID.
    parsed = uuid.UUID(jti)
    assert parsed.version == 4


# ---------------------------------------------------------------------------
# Wrong algorithm rejection
# ---------------------------------------------------------------------------

def test_token_signed_with_wrong_algorithm_is_rejected() -> None:
    """A token signed with HS512 instead of HS256 must be rejected.

    The decoder enforces an explicit HS256-only whitelist, so any token
    using a different algorithm — even with the correct secret — must
    raise AdminTokenError.
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": "admin-alg",
        "username": "alg-user",
        "role": "operator",
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(minutes=15),
    }
    # Sign with HS512 — a valid but disallowed algorithm.
    hs512_token = jwt.encode(payload, _TEST_SECRET, algorithm="HS512")
    settings = _settings()

    with pytest.raises(AdminTokenError):
        decode_access_token(hs512_token, settings)


# ---------------------------------------------------------------------------
# Payload tampering rejection
# ---------------------------------------------------------------------------

def test_tampered_payload_is_rejected() -> None:
    """Manually modifying the payload and re-encoding without signing must fail.

    Scenario:
    1. Create a valid token.
    2. Decode the payload without verification.
    3. Change the role claim to escalate privileges.
    4. Re-encode the header+payload with a *different* secret (simulating
       a forged token where the attacker does not know the real secret).
    5. decode_access_token must raise AdminTokenError.
    """
    settings = _settings()

    # Step 1: create a legitimate operator token.
    original_token = create_access_token(
        "admin-tamper", "mallory", "operator", settings
    )

    # Step 2: decode without verification to read the payload.
    original_payload = jwt.decode(
        original_token,
        options={"verify_signature": False},
        algorithms=["HS256"],
    )

    # Step 3: escalate role to super_admin.
    tampered_payload = dict(original_payload)
    tampered_payload["role"] = "super_admin"

    # Step 4: re-sign with a different secret (attacker does not know the real one).
    forged_token = jwt.encode(
        tampered_payload,
        "attacker-controlled-secret-32-chars!!",
        algorithm="HS256",
    )

    # Step 5: the decoder must reject the forged signature.
    with pytest.raises(AdminTokenError):
        decode_access_token(forged_token, settings)
