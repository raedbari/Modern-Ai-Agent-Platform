"""Short-lived, origin-bound JWTs for browser Widget sessions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Literal
from uuid import UUID, uuid4

import jwt
from jwt.exceptions import InvalidTokenError

from backend.app.auth.origin import normalize_origin
from backend.app.core.config import Settings


_ALGORITHM = "HS256"


class WidgetTokenError(Exception):
    """Raised for every invalid Widget token without exposing token data."""


@dataclass(frozen=True, slots=True)
class WidgetTokenContext:
    tenant_id: str
    agent_id: str
    public_widget_id: str
    origin: str
    session_id: str
    jti: str
    token_type: Literal[
        "widget_session",
        "widget_preview_session",
        "widget_config_proof",
    ]


def _secret(settings: Settings) -> str:
    if settings.widget_jwt_secret_key is None:
        raise WidgetTokenError("Widget authentication is not configured.")
    return settings.widget_jwt_secret_key.get_secret_value()


def create_widget_token(
    *,
    tenant_id: str,
    agent_id: str,
    public_widget_id: str,
    origin: str,
    session_id: str,
    settings: Settings,
    token_type: Literal[
        "widget_session",
        "widget_preview_session",
        "widget_config_proof",
    ] = "widget_session",
) -> str:
    normalized_origin = normalize_origin(origin)
    if normalized_origin is None:
        raise ValueError("A valid normalized origin is required.")

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(
        seconds=settings.widget_token_lifetime_seconds
    )
    payload: dict[str, Any] = {
        "iss": settings.widget_jwt_issuer,
        "aud": settings.widget_jwt_audience,
        "sub": session_id,
        "jti": str(uuid4()),
        "iat": now,
        "nbf": now,
        "exp": expires_at,
        "tenant_id": tenant_id,
        "agent_id": agent_id,
        "widget_id": public_widget_id,
        "origin": normalized_origin,
        "token_type": token_type,
    }
    return jwt.encode(payload, _secret(settings), algorithm=_ALGORITHM)


def decode_widget_token(
    token: str,
    settings: Settings,
) -> WidgetTokenContext:
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            _secret(settings),
            algorithms=[_ALGORITHM],
            issuer=settings.widget_jwt_issuer,
            audience=settings.widget_jwt_audience,
            options={
                "require": [
                    "iss",
                    "aud",
                    "sub",
                    "jti",
                    "iat",
                    "nbf",
                    "exp",
                    "tenant_id",
                    "agent_id",
                    "widget_id",
                    "origin",
                    "token_type",
                ]
            },
        )
    except (InvalidTokenError, WidgetTokenError) as exc:
        raise WidgetTokenError("Widget token is invalid or expired.") from exc

    token_type = payload.get("token_type")
    if token_type not in {
        "widget_session",
        "widget_preview_session",
        "widget_config_proof",
    }:
        raise WidgetTokenError("Widget token type is invalid.")

    string_claims = {
        key: payload.get(key)
        for key in (
            "tenant_id",
            "agent_id",
            "widget_id",
            "origin",
            "sub",
            "jti",
        )
    }
    if any(
        not isinstance(value, str) or not value or len(value) > 255
        for value in string_claims.values()
    ):
        raise WidgetTokenError("Widget token claims are invalid.")

    normalized_origin = normalize_origin(string_claims["origin"])
    if normalized_origin != string_claims["origin"]:
        raise WidgetTokenError("Widget token origin is invalid.")
    try:
        UUID(string_claims["sub"])
        UUID(string_claims["jti"])
    except ValueError as exc:
        raise WidgetTokenError("Widget token identifiers are invalid.") from exc

    return WidgetTokenContext(
        tenant_id=string_claims["tenant_id"],
        agent_id=string_claims["agent_id"],
        public_widget_id=string_claims["widget_id"],
        origin=normalized_origin,
        session_id=string_claims["sub"],
        jti=string_claims["jti"],
        token_type=token_type,
    )
