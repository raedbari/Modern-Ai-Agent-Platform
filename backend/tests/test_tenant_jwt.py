"""Tests for the tenant JWT layer: creation, decoding, and jti revocation."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from backend.app.auth.tenant_jwt import (
    TenantTokenError,
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


_create_access_token_impl = create_access_token


def _issue_access_token(
    user_id,
    tenant_id,
    settings,
    *,
    session_family_id=None,
):
    """Issue a valid test token under the new identity contract."""
    return _create_access_token_impl(
        user_id=user_id,
        settings=settings,
        session_family_id=(
            session_family_id
            or str(uuid.uuid4())
        ),
        tenant_id=tenant_id,
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
    """Verify that a token can be created and decoded successfully."""
    settings = _settings()
    user_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())
    
    token = _issue_access_token(
        user_id=user_id,
        tenant_id=tenant_id,
        settings=settings,
    )

    payload = decode_access_token(token, settings)

    assert payload["sub"] == user_id
    assert payload["tenant_id"] == tenant_id
    assert "jti" in payload
    assert "iat" in payload
    assert "exp" in payload


# ---------------------------------------------------------------------------
# Session family ID inclusion
# ---------------------------------------------------------------------------

def test_session_family_id_is_included_when_provided() -> None:
    """Verify that session_family_id is included in the JWT when provided."""
    settings = _settings()
    user_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())
    family_id = str(uuid.uuid4())
    
    token = _issue_access_token(
        user_id=user_id,
        tenant_id=tenant_id,
        settings=settings,
        session_family_id=family_id,
    )

    payload = decode_access_token(token, settings)

    assert payload["sid"] == family_id



def test_session_family_id_is_required() -> None:
    """Customer access tokens must be bound to a session family."""
    settings = _settings()
    user_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())

    with pytest.raises(TypeError):
        _create_access_token_impl(
            user_id=user_id,
            settings=settings,
            tenant_id=tenant_id,
        )

# ---------------------------------------------------------------------------
# jti uniqueness
# ---------------------------------------------------------------------------

def test_jti_is_unique_per_token() -> None:
    """Verify that each token has a unique jti."""
    settings = _settings()
    user_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())
    
    tokens = [
        _issue_access_token(user_id, tenant_id, settings)
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
    """An expired token is rejected after satisfying required claims."""
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(uuid.uuid4()),
        "tenant_id": str(uuid.uuid4()),
        "sid": str(uuid.uuid4()),
        "jti": str(uuid.uuid4()),
        "iat": now - timedelta(minutes=20),
        "exp": now - timedelta(seconds=1),
    }

    expired_token = jwt.encode(
        payload,
        _TEST_SECRET,
        algorithm="HS256",
    )

    with pytest.raises(
        TenantTokenError,
        match="expired",
    ):
        decode_access_token(
            expired_token,
            _settings(),
        )

# ---------------------------------------------------------------------------
# Invalid signature rejection
# ---------------------------------------------------------------------------

def test_invalid_signature_is_rejected() -> None:
    """Verify that tokens with invalid signatures are rejected."""
    settings = _settings()
    user_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())
    
    token = _issue_access_token(user_id, tenant_id, settings)

    # Tamper: sign with a different secret.
    wrong_settings = _settings(secret="wrong-secret-key-that-is-32-plus-chars!!")

    with pytest.raises(TenantTokenError, match="invalid"):
        decode_access_token(token, wrong_settings)


# ---------------------------------------------------------------------------
# Revoked jti rejection
# ---------------------------------------------------------------------------

def test_revoked_jti_is_rejected() -> None:
    """Verify that tokens with revoked jti are rejected."""
    settings = _settings()
    user_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())
    
    token = _issue_access_token(user_id, tenant_id, settings)

    # Extract jti and revoke it.
    payload = jwt.decode(token, _TEST_SECRET, algorithms=["HS256"])
    revoke_jti(payload["jti"], settings)

    with pytest.raises(TenantTokenError, match="revoked"):
        decode_access_token(token, settings)


# ---------------------------------------------------------------------------
# Non-revoked token remains valid
# ---------------------------------------------------------------------------

def test_non_revoked_token_is_still_valid() -> None:
    """Verify that non-revoked tokens remain valid after revoking other tokens."""
    settings = _settings()
    user_a_id = str(uuid.uuid4())
    user_b_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())
    
    token_a = _issue_access_token(user_a_id, tenant_id, settings)
    token_b = _issue_access_token(user_b_id, tenant_id, settings)

    # Revoke only token_a.
    payload_a = jwt.decode(token_a, _TEST_SECRET, algorithms=["HS256"])
    revoke_jti(payload_a["jti"], settings)

    # token_b must still decode successfully.
    payload_b = decode_access_token(token_b, settings)
    assert payload_b["sub"] == user_b_id


# ---------------------------------------------------------------------------
# Missing jwt_secret_key
# ---------------------------------------------------------------------------

def test_create_token_raises_when_secret_is_not_configured() -> None:
    """Verify that token creation fails when secret key is not configured."""
    settings = Settings(jwt_secret_key=None, _env_file=None)
    user_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())

    with pytest.raises(ValueError, match="MAAP_JWT_SECRET_KEY"):
        _issue_access_token(user_id, tenant_id, settings)


def test_decode_token_raises_when_secret_is_not_configured() -> None:
    """Verify that token decoding fails when secret key is not configured."""
    settings_with = _settings()
    user_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())
    token = _issue_access_token(user_id, tenant_id, settings_with)

    settings_without = Settings(jwt_secret_key=None, _env_file=None)
    with pytest.raises(TenantTokenError, match="not configured"):
        decode_access_token(token, settings_without)


# ---------------------------------------------------------------------------
# Malformed token
# ---------------------------------------------------------------------------

def test_malformed_token_is_rejected() -> None:
    """Verify that malformed tokens are rejected."""
    settings = _settings()

    with pytest.raises(TenantTokenError):
        decode_access_token("this.is.not.a.valid.jwt", settings)


def test_empty_token_is_rejected() -> None:
    """Verify that empty tokens are rejected."""
    settings = _settings()

    with pytest.raises(TenantTokenError):
        decode_access_token("", settings)


# ---------------------------------------------------------------------------
# Token carries required claims
# ---------------------------------------------------------------------------

def test_decoded_payload_contains_required_claims() -> None:
    """Verify that decoded payload contains all required claims."""
    settings = _settings()
    user_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())
    
    token = _issue_access_token(user_id, tenant_id, settings)

    payload = jwt.decode(token, _TEST_SECRET, algorithms=["HS256"])

    for claim in ("sub", "tenant_id", "jti", "iat", "exp"):
        assert claim in payload, f"Missing required claim: {claim}"


def test_jti_claim_is_a_valid_uuid4() -> None:
    """Verify that jti claim is a valid UUID4."""
    settings = _settings()
    user_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())
    
    token = _issue_access_token(user_id, tenant_id, settings)

    payload = jwt.decode(token, _TEST_SECRET, algorithms=["HS256"])
    jti = payload["jti"]

    # This raises ValueError if jti is not a valid UUID.
    parsed = uuid.UUID(jti)
    assert parsed.version == 4


# ---------------------------------------------------------------------------
# Wrong algorithm rejection
# ---------------------------------------------------------------------------

def test_token_signed_with_wrong_algorithm_is_rejected() -> None:
    """Verify that tokens signed with wrong algorithm are rejected.

    The decoder enforces an explicit HS256-only whitelist, so any token
    using a different algorithm — even with the correct secret — must
    raise TenantTokenError.
    """
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(uuid.uuid4()),
        "tenant_id": str(uuid.uuid4()),
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(minutes=15),
    }
    # Sign with HS512 — a valid but disallowed algorithm.
    hs512_token = jwt.encode(payload, _TEST_SECRET, algorithm="HS512")
    settings = _settings()

    with pytest.raises(TenantTokenError):
        decode_access_token(hs512_token, settings)


# ---------------------------------------------------------------------------
# Access token expiry is within 15 minutes (Requirement 8.2)
# ---------------------------------------------------------------------------

def test_access_token_expiry_is_within_15_minutes() -> None:
    """Verify that access token expiry is no more than 15 minutes."""
    settings = _settings(expire_minutes=15)
    user_id = str(uuid.uuid4())
    tenant_id = str(uuid.uuid4())
    
    before_creation = datetime.now(timezone.utc)
    token = _issue_access_token(user_id, tenant_id, settings)
    after_creation = datetime.now(timezone.utc)

    payload = jwt.decode(token, _TEST_SECRET, algorithms=["HS256"])
    
    exp_timestamp = payload["exp"]
    exp_datetime = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
    
    # Verify expiry is within 15 minutes from creation
    max_expiry = after_creation + timedelta(minutes=15)
    assert exp_datetime <= max_expiry, "Access token expiry exceeds 15 minutes"


# ---------------------------------------------------------------------------
# Missing tenant_id claim rejection
# ---------------------------------------------------------------------------

def test_missing_tenant_id_is_rejected() -> None:
    """Verify that tokens missing tenant_id claim are rejected."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(uuid.uuid4()),
        # Missing "tenant_id" claim
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(minutes=15),
    }
    token = jwt.encode(payload, _TEST_SECRET, algorithm="HS256")
    settings = _settings()

    with pytest.raises(TenantTokenError):
        decode_access_token(token, settings)


# ---------------------------------------------------------------------------
# Empty tenant_id claim rejection
# ---------------------------------------------------------------------------


def test_empty_tenant_id_is_rejected() -> None:
    """tenant_id may be absent, but may not be an empty claim."""
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(uuid.uuid4()),
        "tenant_id": "",
        "sid": str(uuid.uuid4()),
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(minutes=15),
    }

    token = jwt.encode(
        payload,
        _TEST_SECRET,
        algorithm="HS256",
    )

    with pytest.raises(
        TenantTokenError,
        match="tenant_id",
    ):
        decode_access_token(
            token,
            _settings(),
        )



def test_identity_token_allows_missing_tenant_id() -> None:
    """Pending customers may authenticate without tenant authorization."""
    settings = _settings()
    user_id = str(uuid.uuid4())
    family_id = str(uuid.uuid4())

    token = _create_access_token_impl(
        user_id=user_id,
        settings=settings,
        session_family_id=family_id,
        tenant_id=None,
    )

    payload = decode_access_token(
        token,
        settings,
    )

    assert payload["sub"] == user_id
    assert payload["sid"] == family_id
    assert "tenant_id" not in payload


def test_decode_rejects_missing_session_family_id() -> None:
    """A customer JWT without sid must never authenticate."""
    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(uuid.uuid4()),
        "tenant_id": str(uuid.uuid4()),
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + timedelta(minutes=15),
    }

    token = jwt.encode(
        payload,
        _TEST_SECRET,
        algorithm="HS256",
    )

    with pytest.raises(
        TenantTokenError,
        match="invalid",
    ):
        decode_access_token(
            token,
            _settings(),
        )
