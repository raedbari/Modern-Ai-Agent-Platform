"""Customer-facing Widget Settings API routes with JWT authentication."""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import require_tenant_user_jwt
from backend.app.api.schemas.widget import (
    WidgetBootstrapResponse,
    WidgetConnectorPairingCreate,
    WidgetConnectorPairingCreated,
    WidgetPublicConfig,
    WidgetTheme,
)
from backend.app.auth.origin import normalize_origin
from backend.app.auth.tenant_context import TenantUserContext
from backend.app.auth.tenant_rbac import TenantPermission, require_tenant_permission
from backend.app.auth.widget_jwt import WidgetTokenError, create_widget_token
from backend.app.core.client_ip import get_client_ip
from backend.app.core.config import Settings, get_settings
from backend.app.core.rate_limit import RateLimiter, get_rate_limiter
from backend.app.db.base import get_db
from backend.app.infrastructure.database.tenant_repositories import (
    TenantScopedWidgetRepository,
)
from backend.app.operations.admin_lifecycle import AdminResourceNotFoundError
from backend.app.operations.widget import WidgetSettingsNotFoundError
from backend.app.operations.widget_pairing import (
    PAIRING_TTL_SECONDS,
    WidgetPairingDisabledError,
    WidgetPairingOriginNotAllowedError,
    create_widget_connector_pairing,
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

    @model_validator(mode="after")
    def reject_null_origins(self) -> "WidgetSettingsUpdateRequest":
        if "allowed_origins" in self.model_fields_set and self.allowed_origins is None:
            raise ValueError("allowed_origins must be an array when provided.")
        return self


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
    if "display_name" in request.model_fields_set:
        updates["display_name"] = request.display_name
    if "greeting" in request.model_fields_set:
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


@router.post(
    "/api/customer/agents/{agent_id}/widget-settings/pairings",
    response_model=WidgetConnectorPairingCreated,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(
            require_tenant_permission(
                TenantPermission.can_manage_widget_settings
            )
        )
    ],
)
async def create_customer_connector_pairing(
    agent_id: str,
    payload: WidgetConnectorPairingCreate,
    context: Annotated[TenantUserContext, Depends(require_tenant_user_jwt)],
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> WidgetConnectorPairingCreated:
    try:
        pairing, pairing_code = await create_widget_connector_pairing(
            session,
            tenant_id=context.tenant_id,
            agent_id=agent_id,
            origin=payload.origin,
            connector_type=payload.connector_type,
            created_by_admin_id=None,
            settings=settings,
        )
        await session.commit()
        await session.refresh(pairing)
    except (AdminResourceNotFoundError, WidgetSettingsNotFoundError) as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Widget not found.",
        ) from exc
    except WidgetPairingDisabledError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except WidgetPairingOriginNotAllowedError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    return WidgetConnectorPairingCreated(
        pairing_id=pairing.id,
        pairing_code=pairing_code,
        origin=pairing.origin,
        connector_type=pairing.connector_type,
        expires_at=pairing.expires_at,
        expires_in=PAIRING_TTL_SECONDS,
    )


@router.post(
    "/api/customer/agents/{agent_id}/widget-settings/preview/bootstrap",
    response_model=WidgetBootstrapResponse,
    dependencies=[
        Depends(
            require_tenant_permission(
                TenantPermission.can_manage_widget_settings
            )
        )
    ],
)
async def bootstrap_customer_widget_preview(
    agent_id: str,
    request: Request,
    context: Annotated[TenantUserContext, Depends(require_tenant_user_jwt)],
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    rate_limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
    origin_header: Annotated[str | None, Header(alias="Origin")] = None,
) -> WidgetBootstrapResponse:
    origin = normalize_origin(origin_header)
    if origin is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A valid Origin header is required.",
        )

    repository = TenantScopedWidgetRepository(session)
    result = await repository.get_by_agent(agent_id, context.tenant_id)
    agent = await repository.get_active_agent(agent_id, context.tenant_id)
    if result is None or agent is None or not agent.is_active:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Widget not found.",
        )

    client_ip = get_client_ip(request, settings)
    try:
        widget_limit = await rate_limiter.check(
            bucket="widget-preview-agent",
            identity=f"{context.tenant_id}:{agent_id}",
            limit=settings.widget_bootstrap_rate_limit_per_widget,
            window_seconds=settings.widget_bootstrap_rate_limit_window_seconds,
        )
        ip_limit = await rate_limiter.check(
            bucket="widget-preview-ip",
            identity=client_ip or "unknown",
            limit=settings.widget_bootstrap_rate_limit_per_ip,
            window_seconds=settings.widget_bootstrap_rate_limit_window_seconds,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Widget preview is temporarily unavailable.",
        ) from exc
    if not widget_limit.allowed or not ip_limit.allowed:
        retry_after = max(
            widget_limit.retry_after_seconds,
            ip_limit.retry_after_seconds,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many Widget preview requests.",
            headers={"Retry-After": str(retry_after)},
        )

    widget, _allowed_origins = result
    session_id = str(uuid4())
    try:
        token = create_widget_token(
            tenant_id=context.tenant_id,
            agent_id=agent_id,
            public_widget_id=widget.public_widget_id,
            origin=origin,
            session_id=session_id,
            settings=settings,
            token_type="widget_preview_session",
        )
    except WidgetTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Widget authentication is not configured.",
        ) from exc

    return WidgetBootstrapResponse(
        session_token=token,
        expires_in=settings.widget_token_lifetime_seconds,
        session_id=session_id,
        widget=WidgetPublicConfig(
            widget_id=widget.public_widget_id,
            display_name=widget.display_name or agent.name,
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
        ),
    )
