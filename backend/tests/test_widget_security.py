"""Unit tests for Widget origin and short-lived token security."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest

from backend.app.auth.origin import (
    is_development_origin_allowed,
    normalize_origin,
)
from backend.app.auth.widget_jwt import (
    WidgetTokenError,
    create_widget_token,
    decode_widget_token,
)
from backend.app.core.config import Settings


_WIDGET_SECRET = "widget-test-secret-key-with-at-least-32-bytes!!"


def _settings(**overrides) -> Settings:
    values = {
        "widget_jwt_secret_key": _WIDGET_SECRET,
        "widget_token_lifetime_seconds": 600,
        "_env_file": None,
    }
    values.update(overrides)
    return Settings(**values)


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("https://Example.COM", "https://example.com"),
        ("https://example.com/", "https://example.com"),
        ("https://example.com:443", "https://example.com"),
        ("http://example.com:80", "http://example.com"),
        ("http://localhost:3000", "http://localhost:3000"),
        ("https://[::1]:8443", "https://[::1]:8443"),
        (None, None),
        ("", None),
        ("null", None),
        ("ftp://example.com", None),
        ("https://user:pass@example.com", None),
        ("https://example.com/path", None),
        ("https://example.com?query=1", None),
        ("https://example.com#fragment", None),
        ("https://*.example.com", None),
        ("https://example.com evil", None),
        ("not-a-url", None),
    ],
)
def test_normalize_origin_is_strict(
    raw: str | None,
    expected: str | None,
) -> None:
    assert normalize_origin(raw) == expected


@pytest.mark.parametrize(
    "origin,allowed",
    [
        ("http://localhost:3000", True),
        ("https://localhost", True),
        ("http://127.0.0.1:8000", True),
        ("http://[::1]:5173", True),
        ("http://localhost.attacker.example", False),
        ("http://127.0.0.10", False),
        ("https://example.com", False),
        (None, False),
    ],
)
def test_development_origin_requires_exact_loopback_host(
    origin: str | None,
    allowed: bool,
) -> None:
    assert is_development_origin_allowed(origin, "development") is allowed
    assert is_development_origin_allowed(origin, "production") is False


def test_widget_token_round_trip_preserves_isolation_claims() -> None:
    settings = _settings()
    session_id = str(uuid4())
    token = create_widget_token(
        tenant_id="tenant-a",
        agent_id="agent-a",
        public_widget_id="wgt_secure_public_identifier_1234",
        origin="https://Example.com:443",
        session_id=session_id,
        settings=settings,
    )

    context = decode_widget_token(token, settings)

    assert context.tenant_id == "tenant-a"
    assert context.agent_id == "agent-a"
    assert context.public_widget_id == "wgt_secure_public_identifier_1234"
    assert context.origin == "https://example.com"
    assert context.session_id == session_id


def test_widget_token_signed_with_another_secret_is_rejected() -> None:
    token = create_widget_token(
        tenant_id="tenant-a",
        agent_id="agent-a",
        public_widget_id="wgt_secure_public_identifier_1234",
        origin="https://example.com",
        session_id=str(uuid4()),
        settings=_settings(),
    )
    wrong_settings = _settings(
        widget_jwt_secret_key=(
            "another-widget-secret-key-with-at-least-32-bytes!"
        )
    )

    with pytest.raises(WidgetTokenError):
        decode_widget_token(token, wrong_settings)


def test_widget_token_wrong_audience_is_rejected() -> None:
    token = create_widget_token(
        tenant_id="tenant-a",
        agent_id="agent-a",
        public_widget_id="wgt_secure_public_identifier_1234",
        origin="https://example.com",
        session_id=str(uuid4()),
        settings=_settings(),
    )

    with pytest.raises(WidgetTokenError):
        decode_widget_token(
            token,
            _settings(widget_jwt_audience="different-audience"),
        )


def test_expired_widget_token_is_rejected() -> None:
    settings = _settings()
    now = datetime.now(timezone.utc)
    expired_payload = {
        "iss": settings.widget_jwt_issuer,
        "aud": settings.widget_jwt_audience,
        "sub": str(uuid4()),
        "jti": str(uuid4()),
        "iat": now - timedelta(minutes=2),
        "nbf": now - timedelta(minutes=2),
        "exp": now - timedelta(minutes=1),
        "tenant_id": "tenant-a",
        "agent_id": "agent-a",
        "widget_id": "wgt_secure_public_identifier_1234",
        "origin": "https://example.com",
        "token_type": "widget_session",
    }
    token = jwt.encode(
        expired_payload,
        _WIDGET_SECRET,
        algorithm="HS256",
    )

    with pytest.raises(WidgetTokenError):
        decode_widget_token(token, settings)
