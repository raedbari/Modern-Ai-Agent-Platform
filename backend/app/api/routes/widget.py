"""Public bootstrap endpoint for origin-bound browser Widget sessions."""

from __future__ import annotations

from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.schemas.widget import (
    WidgetBootstrapRequest,
    WidgetBootstrapResponse,
    WidgetPublicConfig,
    WidgetTheme,
)
from backend.app.auth.origin import normalize_origin
from backend.app.auth.widget_jwt import WidgetTokenError, create_widget_token
from backend.app.core.client_ip import get_client_ip
from backend.app.core.config import Settings, get_settings
from backend.app.core.rate_limit import RateLimiter, get_rate_limiter
from backend.app.db.base import get_db
from backend.app.operations.widget import (
    is_widget_origin_allowed,
    resolve_public_widget,
)


router = APIRouter(prefix="/api/widget", tags=["widget"])


@router.post(
    "/config",
    response_model=WidgetPublicConfig,
    status_code=status.HTTP_200_OK,
)
async def get_public_widget_config(
    payload: WidgetBootstrapRequest,
    request: Request,
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    origin_header: Annotated[str | None, Header(alias="Origin")] = None,
) -> WidgetPublicConfig:
    """Return browser-safe Widget appearance without issuing a session."""

    origin = normalize_origin(origin_header)
    if origin is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="A valid Origin header is required.",
        )

    resolved = await resolve_public_widget(
        session,
        payload.widget_id,
    )
    if resolved is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Widget not found.",
        )

    widget, agent, tenant = resolved

    if not await is_widget_origin_allowed(
        session,
        tenant_id=tenant.id,
        agent_id=agent.id,
        origin=origin,
        environment=settings.environment,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Origin is not allowed for this Widget.",
        )

    request.state.widget_cors_origin = origin
    response.headers["Cache-Control"] = "no-store"

    return WidgetPublicConfig(
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
    )


@router.post(
    "/bootstrap",
    response_model=WidgetBootstrapResponse,
    status_code=status.HTTP_200_OK,
)
async def bootstrap_widget(
    payload: WidgetBootstrapRequest,
    request: Request,
    response: Response,
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

    client_ip = get_client_ip(request, settings)
    try:
        widget_limit = await rate_limiter.check(
            bucket="widget-bootstrap-widget",
            identity=payload.widget_id,
            limit=settings.widget_bootstrap_rate_limit_per_widget,
            window_seconds=(
                settings.widget_bootstrap_rate_limit_window_seconds
            ),
        )
        ip_limit = await rate_limiter.check(
            bucket="widget-bootstrap-ip",
            identity=client_ip or "unknown",
            limit=settings.widget_bootstrap_rate_limit_per_ip,
            window_seconds=(
                settings.widget_bootstrap_rate_limit_window_seconds
            ),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Widget service is temporarily unavailable.",
        ) from exc

    if not widget_limit.allowed or not ip_limit.allowed:
        retry_after = max(
            widget_limit.retry_after_seconds,
            ip_limit.retry_after_seconds,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many Widget bootstrap requests.",
            headers={"Retry-After": str(retry_after)},
        )

    resolved = await resolve_public_widget(session, payload.widget_id)
    if resolved is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Widget not found.",
        )
    widget, agent, tenant = resolved

    if not await is_widget_origin_allowed(
        session,
        tenant_id=tenant.id,
        agent_id=agent.id,
        origin=origin,
        environment=settings.environment,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Origin is not allowed for this Widget.",
        )

    request.state.widget_cors_origin = origin
    session_id = str(uuid4())
    try:
        token = create_widget_token(
            tenant_id=tenant.id,
            agent_id=agent.id,
            public_widget_id=widget.public_widget_id,
            origin=origin,
            session_id=session_id,
            settings=settings,
        )
    except WidgetTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Widget authentication is not configured.",
        ) from exc

    response.headers["Cache-Control"] = "no-store"
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
