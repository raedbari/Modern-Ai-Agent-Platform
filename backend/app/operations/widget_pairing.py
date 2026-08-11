"""Operations for short-lived Widget Connector pairing codes."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import secrets
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import Settings
from backend.app.db.models import WidgetConnectorPairing
from backend.app.operations.widget import (
    InvalidWidgetOriginError,
    _normalize_allowed_origins,
    get_widget_settings,
)


PAIRING_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
PAIRING_CODE_GROUPS = 4
PAIRING_CODE_GROUP_SIZE = 4
PAIRING_TTL_SECONDS = 600


class WidgetPairingOriginNotAllowedError(ValueError):
    """Raised when pairing is requested for an origin not enabled for the Widget."""


class WidgetPairingDisabledError(ValueError):
    """Raised when Connector pairing is requested for a disabled Widget."""


def _new_pairing_code() -> str:
    groups = [
        "".join(
            secrets.choice(PAIRING_CODE_ALPHABET)
            for _ in range(PAIRING_CODE_GROUP_SIZE)
        )
        for _ in range(PAIRING_CODE_GROUPS)
    ]
    return "ATK-" + "-".join(groups)


def pairing_code_digest(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


async def create_widget_connector_pairing(
    session: AsyncSession,
    *,
    tenant_id: str,
    agent_id: str,
    origin: str,
    connector_type: str,
    created_by_admin_id: str,
    settings: Settings,
) -> tuple[WidgetConnectorPairing, str]:
    widget, allowed_origins = await get_widget_settings(
        session,
        tenant_id=tenant_id,
        agent_id=agent_id,
    )

    if not widget.is_enabled:
        raise WidgetPairingDisabledError(
            "Widget must be enabled before creating a Connector pairing."
        )

    normalized_origin = _normalize_allowed_origins(
        [origin],
        settings,
    )[0]

    if normalized_origin not in allowed_origins:
        raise WidgetPairingOriginNotAllowedError(
            "Connector origin must already exist in the Widget allowed origins."
        )

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(
        seconds=PAIRING_TTL_SECONDS,
    )

    # Collision is extraordinarily unlikely, but the DB also has a unique
    # constraint on code_digest. Check before insert so creation remains clean.
    for _ in range(5):
        pairing_code = _new_pairing_code()
        code_digest = pairing_code_digest(pairing_code)

        existing = await session.scalar(
            select(WidgetConnectorPairing.id).where(
                WidgetConnectorPairing.code_digest == code_digest
            )
        )

        if existing is None:
            break
    else:
        raise RuntimeError(
            "Unable to allocate a unique Connector pairing code."
        )

    pairing = WidgetConnectorPairing(
        id=str(uuid4()),
        tenant_id=tenant_id,
        agent_id=agent_id,
        origin=normalized_origin,
        connector_type=connector_type,
        code_digest=code_digest,
        expires_at=expires_at,
        used_at=None,
        connected_at=None,
        created_by_admin_id=created_by_admin_id,
    )

    session.add(pairing)

    return pairing, pairing_code
