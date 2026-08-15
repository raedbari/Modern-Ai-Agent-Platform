"""Security boundary tests for the Knowledge API."""

from __future__ import annotations

from typing import Annotated
from unittest.mock import AsyncMock

from fastapi import Depends, FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import (
    require_chat_context,
    require_knowledge_context,
)
from backend.app.auth.context import ChatExecutionContext
from backend.app.db.base import get_db
from backend.app.main import create_app


def test_knowledge_routes_use_dual_auth_dependency() -> None:
    """Every public knowledge operation must expose API-key OR tenant-JWT auth."""

    from backend.app.main import create_app

    paths = create_app().openapi()["paths"]

    expected_security = [
        {"TenantApiKey": []},
        {"TenantUserJWT": []},
    ]

    checked: list[tuple[str, str]] = []

    for path, path_item in paths.items():
        if not path.startswith("/api/knowledge-bases"):
            continue

        for method in (
            "get",
            "post",
            "put",
            "patch",
            "delete",
        ):
            operation = path_item.get(method)

            if operation is None:
                continue

            checked.append((method.upper(), path))

            assert operation.get("security") == expected_security, (
                f"{method.upper()} {path} must allow "
                "TenantApiKey OR TenantUserJWT."
            )

    assert checked, "No public knowledge routes were found."



def test_knowledge_openapi_allows_api_key_or_tenant_jwt() -> None:
    schema = create_app().openapi()

    operations = {
        "get",
        "post",
        "put",
        "patch",
        "delete",
        "options",
        "head",
    }

    found = 0

    for path, path_item in schema["paths"].items():
        if not path.startswith("/api/knowledge-bases"):
            continue

        for method, operation in path_item.items():
            if method not in operations:
                continue

            found += 1
            assert operation["security"] == [
                {"TenantApiKey": []},
                {"TenantUserJWT": []},
            ]

    assert found > 0


def test_chat_openapi_retains_both_authentication_methods() -> None:
    schema = create_app().openapi()

    assert schema["paths"]["/api/chat"]["post"]["security"] == [
        {"TenantApiKey": []},
        {"WidgetToken": []},
    ]


def test_bearer_only_request_cannot_use_tenant_key_dependency() -> None:
    app = FastAPI()

    async def override_db():
        yield AsyncMock(spec=AsyncSession)

    app.dependency_overrides[get_db] = override_db

    @app.get("/probe")
    async def probe(
        context: Annotated[
            ChatExecutionContext,
            Depends(require_knowledge_context),
        ],
    ) -> dict[str, str]:
        return {"auth_method": context.auth_method}

    with TestClient(app) as client:
        response = client.get(
            "/probe",
            headers={
                "Authorization": "Bearer widget-token",
                "X-Agent-ID": "agent-1",
            },
        )

    assert response.status_code == 401
