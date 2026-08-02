"""Tenant-safe operations for Widget configuration and public lookup."""

from __future__ import annotations

import secrets
from urllib.parse import urlsplit

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.schemas.widget import WidgetSettingsUpdate
from backend.app.auth.origin import (
    is_development_origin_allowed,
    normalize_origin,
)
from backend.app.core.config import Settings
from backend.app.db.models import (
    Agent,
    AgentWidgetSettings,
    Tenant,
    WidgetAllowedOrigin,
)
from backend.app.operations.admin_lifecycle import require_agent


class WidgetSettingsNotFoundError(LookupError):
    """Raised when an agent has no Widget configuration yet."""


class InvalidWidgetOriginError(ValueError):
    """Raised when an origin cannot be safely normalized or enabled."""


def _normalize_allowed_origins(
    raw_origins: list[str],
    settings: Settings,
) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw_origin in raw_origins:
        origin = normalize_origin(raw_origin)
        if origin is None or len(origin) > 255:
            raise InvalidWidgetOriginError(
                f"Invalid Widget origin: {raw_origin!r}"
            )
        if (
            urlsplit(origin).scheme != "https"
            and not is_development_origin_allowed(
                origin,
                settings.environment,
            )
        ):
            raise InvalidWidgetOriginError(
                "Widget origins must use HTTPS outside local development."
            )
        if origin in seen:
            raise InvalidWidgetOriginError(
                f"Duplicate Widget origin after normalization: {origin}"
            )
        seen.add(origin)
        normalized.append(origin)
    return normalized


async def _new_public_widget_id(session: AsyncSession) -> str:
    for _ in range(5):
        candidate = f"wgt_{secrets.token_urlsafe(24)}"
        exists = await session.scalar(
            select(AgentWidgetSettings.public_widget_id).where(
                AgentWidgetSettings.public_widget_id == candidate
            )
        )
        if exists is None:
            return candidate
    raise RuntimeError("Could not allocate a unique public Widget identifier.")


async def get_widget_settings(
    session: AsyncSession,
    *,
    tenant_id: str,
    agent_id: str,
) -> tuple[AgentWidgetSettings, list[str]]:
    await require_agent(session, tenant_id=tenant_id, agent_id=agent_id)
    widget = await session.get(
        AgentWidgetSettings,
        {"tenant_id": tenant_id, "agent_id": agent_id},
    )
    if widget is None:
        raise WidgetSettingsNotFoundError("Widget settings not found.")
    origins = list(
        (
            await session.scalars(
                select(WidgetAllowedOrigin.origin)
                .where(
                    WidgetAllowedOrigin.tenant_id == tenant_id,
                    WidgetAllowedOrigin.agent_id == agent_id,
                )
                .order_by(WidgetAllowedOrigin.origin)
            )
        ).all()
    )
    return widget, origins


async def upsert_widget_settings(
    session: AsyncSession,
    *,
    tenant_id: str,
    agent_id: str,
    payload: WidgetSettingsUpdate,
    settings: Settings,
) -> tuple[AgentWidgetSettings, list[str]]:
    await require_agent(session, tenant_id=tenant_id, agent_id=agent_id)
    origins = _normalize_allowed_origins(payload.allowed_origins, settings)
    if (
        payload.is_enabled
        and not origins
        and settings.environment not in {"development", "test"}
    ):
        raise InvalidWidgetOriginError(
            "At least one allowed origin is required before enabling a Widget."
        )

    widget = await session.get(
        AgentWidgetSettings,
        {"tenant_id": tenant_id, "agent_id": agent_id},
    )
    theme = payload.theme
    if widget is None:
        widget = AgentWidgetSettings(
            tenant_id=tenant_id,
            agent_id=agent_id,
            public_widget_id=await _new_public_widget_id(session),
        )
        session.add(widget)

    widget.is_enabled = payload.is_enabled
    widget.display_name = payload.display_name
    widget.greeting = payload.greeting
    widget.primary_color = theme.primary_color
    widget.text_color = theme.text_color
    widget.launcher_color = theme.launcher_color
    widget.header_color = theme.header_color
    widget.user_message_color = theme.user_message_color
    widget.position = theme.position
    widget.appearance = theme.appearance
    await session.flush()

    await session.execute(
        delete(WidgetAllowedOrigin).where(
            WidgetAllowedOrigin.tenant_id == tenant_id,
            WidgetAllowedOrigin.agent_id == agent_id,
        )
    )
    session.add_all(
        [
            WidgetAllowedOrigin(
                tenant_id=tenant_id,
                agent_id=agent_id,
                origin=origin,
            )
            for origin in origins
        ]
    )
    await session.flush()
    return widget, origins


async def resolve_public_widget(
    session: AsyncSession,
    public_widget_id: str,
) -> tuple[AgentWidgetSettings, Agent, Tenant] | None:
    return (
        await session.execute(
            select(AgentWidgetSettings, Agent, Tenant)
            .join(
                Agent,
                (Agent.tenant_id == AgentWidgetSettings.tenant_id)
                & (Agent.id == AgentWidgetSettings.agent_id),
            )
            .join(Tenant, Tenant.id == AgentWidgetSettings.tenant_id)
            .where(
                AgentWidgetSettings.public_widget_id == public_widget_id,
                AgentWidgetSettings.is_enabled.is_(True),
                Agent.is_active.is_(True),
                Tenant.is_active.is_(True),
            )
        )
    ).one_or_none()


async def is_widget_origin_allowed(
    session: AsyncSession,
    *,
    tenant_id: str,
    agent_id: str,
    origin: str,
    environment: str,
) -> bool:
    if is_development_origin_allowed(origin, environment):
        return True
    allowed = await session.scalar(
        select(WidgetAllowedOrigin.id).where(
            WidgetAllowedOrigin.tenant_id == tenant_id,
            WidgetAllowedOrigin.agent_id == agent_id,
            WidgetAllowedOrigin.origin == origin,
        )
    )
    return allowed is not None
