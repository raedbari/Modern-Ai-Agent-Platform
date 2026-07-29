"""Tests for application startup and the public health endpoint."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

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
