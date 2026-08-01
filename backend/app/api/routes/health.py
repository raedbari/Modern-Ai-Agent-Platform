"""Liveness and database-readiness endpoints."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import Settings, get_settings
from backend.app.db.base import get_db

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Public health-check response."""

    status: Literal["ok"]
    service: str
    environment: str


class ReadinessResponse(BaseModel):
    """Public readiness result without infrastructure details."""

    status: Literal["ready", "unavailable"]
    database: Literal["ok", "unavailable"]


@router.get("/health", response_model=HealthResponse, status_code=200)
def read_health(
    settings: Annotated[Settings, Depends(get_settings)],
) -> HealthResponse:
    """Report that the API process is ready to receive requests."""
    return HealthResponse(
        status="ok",
        service=settings.app_name,
        environment=settings.environment,
    )


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    responses={503: {"model": ReadinessResponse}},
)
async def read_readiness(
    response: Response,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ReadinessResponse:
    """Report whether the API can execute a minimal database query."""

    try:
        await session.execute(text("SELECT 1"))
    except Exception:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return ReadinessResponse(
            status="unavailable",
            database="unavailable",
        )

    return ReadinessResponse(status="ready", database="ok")
