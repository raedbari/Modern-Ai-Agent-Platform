"""Tests for application startup and the public health endpoint."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
import pytest
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    create_async_engine,
)

from backend.app.db.base import get_db
from backend.app.main import app, create_app


def test_application_factory_returns_fastapi_app() -> None:
    application = create_app()

    assert isinstance(application, FastAPI)


def test_health_endpoint_returns_expected_payload() -> None:
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "Modern AI Agent Platform API",
        "environment": "development",
    }


@pytest.mark.asyncio
async def test_readiness_endpoint_checks_database() -> None:
    application = create_app()
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_db():
        async with sessions() as session:
            yield session

    application.dependency_overrides[get_db] = override_get_db
    try:
        async with AsyncClient(
            transport=ASGITransport(app=application),
            base_url="http://test",
        ) as client:
            response = await client.get("/ready")
    finally:
        application.dependency_overrides.clear()
        await engine.dispose()

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "database": "ok",
    }
