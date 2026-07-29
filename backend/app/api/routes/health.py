"""Service health endpoint."""

from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.app.core.config import Settings, get_settings

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    """Public health-check response."""

    status: Literal["ok"]
    service: str
    environment: str


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
