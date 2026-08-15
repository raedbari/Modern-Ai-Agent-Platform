"""Customer-facing Widget Settings API routes with JWT authentication."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import require_tenant_user_jwt
from backend.app.auth.tenant_context import TenantUserContext
from backend.app.auth.tenant_rbac import TenantPermission, require_tenant_permission
from backend.app.db.base import get_db
from backend.app.infrastructure.database.tenant_repositories import (
    TenantScopedWidgetRepository,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["customer-widgets"])


# --- Schemas ---

class WidgetSettingsUpdateRequest(BaseModel):
    """Request schema for updating widget settings."""

    model_config = ConfigDict(extra="forbid")

    is_enabled: bool | None = None
    display_name: str | None = Field(default=None, max_length=255)
    greeting: str | None = Field(default=None, max_length=500)
    primary_color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    text_color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    launcher_color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    header_color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    user_message_color: str | None = Field(default=None, pattern=r"^#[0-9A-Fa-f]{6}$")
    position: str | None = Field(default=None, pattern=r"^(left|right)$")
    appearance: str | None = Field(default=None, pattern=r"^(light|dark)$")
    allowed_origins: list[str] | None = None


class WidgetSettingsResponse(BaseModel):
    """Response schema for widget settings."""

    tenant_id: str
    agent_id: str
    public_widget_id: str
    is_enabled: bool
    display_name: str | None
    greeting: str | None
    primary_color: str
    text_color: str
    launcher_color: str
    header_color: str
    user_message_color: str
    position: str
    appearance: str
    allowed_origins: list[str]


def _widget_response(settings, allowed_origins: list[str]) -> WidgetSettingsResponse:
    """Convert database model to response schema."""
    return WidgetSettingsResponse(
        tenant_id=settings.tenant_id,
        agent_id=settings.agent_id,
        public_widget_id=settings.public_widget_id,
        is_enabled=settings.is_enabled,
        display_name=settings.display_name,
        greeting=settings.greeting,
        primary_color=settings.primary_color,
        text_color=settings.text_color,
        launcher_color=settings.launcher_color,
        header_color=settings.header_color,
        user_message_color=settings.user_message_color,
        position=settings.position,
        appearance=settings.appearance,
        allowed_origins=allowed_origins,
    )


# --- Routes ---

@router.get(
    "/api/customer/agents/{agent_id}/widget-settings",
    response_model=WidgetSettingsResponse,
    dependencies=[Depends(require_tenant_permission(TenantPermission.can_read_agents))],
)
async def get_widget_settings(
    agent_id: str,
    context: Annotated[TenantUserContext, Depends(require_tenant_user_jwt)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> WidgetSettingsResponse:
    """
    Get widget settings for a specific agent.
    
    Returns 404 if the agent doesn't exist or belongs to another tenant.
    Requires: Any approved role
    """
    repo = TenantScopedWidgetRepository(session)
    
    result = await repo.get_by_agent(agent_id, context.tenant_id)
    
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found or widget settings not configured",
        )
    
    settings, allowed_origins = result
    
    return _widget_response(settings, allowed_origins)


@router.put(
    "/api/customer/agents/{agent_id}/widget-settings",
    response_model=WidgetSettingsResponse,
    dependencies=[Depends(require_tenant_permission(TenantPermission.can_manage_widget_settings))],
)
async def update_widget_settings(
    agent_id: str,
    request: WidgetSettingsUpdateRequest,
    context: Annotated[TenantUserContext, Depends(require_tenant_user_jwt)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> WidgetSettingsResponse:
    """
    Update widget settings for a specific agent.
    
    Returns 404 if the agent doesn't exist or belongs to another tenant.
    Requires: knowledge_editor, tenant_admin, or tenant_owner role
    """
    repo = TenantScopedWidgetRepository(session)
    
    # Build updates dict (only include fields that were provided)
    updates = {}
    if request.is_enabled is not None:
        updates["is_enabled"] = request.is_enabled
    if request.display_name is not None:
        updates["display_name"] = request.display_name
    if request.greeting is not None:
        updates["greeting"] = request.greeting
    if request.primary_color is not None:
        updates["primary_color"] = request.primary_color
    if request.text_color is not None:
        updates["text_color"] = request.text_color
    if request.launcher_color is not None:
        updates["launcher_color"] = request.launcher_color
    if request.header_color is not None:
        updates["header_color"] = request.header_color
    if request.user_message_color is not None:
        updates["user_message_color"] = request.user_message_color
    if request.position is not None:
        updates["position"] = request.position
    if request.appearance is not None:
        updates["appearance"] = request.appearance
    
    try:
        result = await repo.update(
            agent_id,
            context.tenant_id,
            updates,
            allowed_origins=request.allowed_origins,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    settings, allowed_origins = result
    response = _widget_response(
        settings,
        allowed_origins,
    )
    await session.commit()
    
    logger.info(
        "Widget settings updated",
        extra={
            "agent_id": agent_id,
            "tenant_id": context.tenant_id,
            "user_id": context.user_id,
            "updates": list(updates.keys()),
        },
    )
    
    return response
