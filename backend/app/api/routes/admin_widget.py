"""Administrator endpoints for per-agent Widget configuration."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import require_admin_access, require_permission
from backend.app.api.schemas.widget import (
    WidgetSettingsResponse,
    WidgetSettingsUpdate,
    WidgetTheme,
)
from backend.app.auth.admin_context import AdminContext
from backend.app.core.client_ip import get_client_ip
from backend.app.core.config import Settings, get_settings
from backend.app.db.base import get_db
from backend.app.operations.admin_lifecycle import AdminResourceNotFoundError
from backend.app.operations.widget import (
    InvalidWidgetOriginError,
    WidgetSettingsNotFoundError,
    get_widget_settings,
    upsert_widget_settings,
)
from backend.app.services.audit import AuditService


router = APIRouter(
    prefix="/api/admin/tenants/{tenant_id}/agents/{agent_id}/widget",
    tags=["admin-widget"],
    dependencies=[Depends(require_admin_access)],
)


def _response(widget, origins: list[str]) -> WidgetSettingsResponse:
    return WidgetSettingsResponse(
        tenant_id=widget.tenant_id,
        agent_id=widget.agent_id,
        public_widget_id=widget.public_widget_id,
        is_enabled=widget.is_enabled,
        display_name=widget.display_name,
        greeting=widget.greeting,
        theme=WidgetTheme(
            primary_color=widget.primary_color,
            text_color=widget.text_color,
            launcher_color=widget.launcher_color,
            header_color=widget.header_color,
            user_message_color=widget.user_message_color,
            position=widget.position,
            appearance=widget.appearance,
        ),
        allowed_origins=origins,
    )


@router.get(
    "",
    response_model=WidgetSettingsResponse,
    dependencies=[Depends(require_permission("widgets:read"))],
)
async def read_widget_settings(
    tenant_id: str,
    agent_id: str,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> WidgetSettingsResponse:
    try:
        widget, origins = await get_widget_settings(
            session,
            tenant_id=tenant_id,
            agent_id=agent_id,
        )
    except (AdminResourceNotFoundError, WidgetSettingsNotFoundError) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    return _response(widget, origins)


@router.put(
    "",
    response_model=WidgetSettingsResponse,
    dependencies=[Depends(require_permission("widgets:write"))],
)
async def configure_widget(
    tenant_id: str,
    agent_id: str,
    payload: WidgetSettingsUpdate,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    context: Annotated[AdminContext, Depends(require_admin_access)],
) -> WidgetSettingsResponse:
    try:
        widget, origins = await upsert_widget_settings(
            session,
            tenant_id=tenant_id,
            agent_id=agent_id,
            payload=payload,
            settings=settings,
        )
        await AuditService.write(
            session,
            event_type="widget_configured",
            outcome="success",
            admin_id=context.admin_id,
            target_type="agent",
            target_id=agent_id,
            client_ip=get_client_ip(request, settings),
            detail={
                "tenant_id": tenant_id,
                "is_enabled": payload.is_enabled,
                "allowed_origin_count": len(origins),
            },
        )
        await session.commit()
        await session.refresh(widget)
    except AdminResourceNotFoundError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except InvalidWidgetOriginError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    return _response(widget, origins)
