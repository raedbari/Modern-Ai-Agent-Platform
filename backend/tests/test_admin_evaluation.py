"""Integration coverage for the Platform Admin Evaluation slice."""

from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)

from backend.app.api.dependencies import (
    ROLE_PERMISSIONS,
    get_core_ai_runtime,
    require_admin_access,
)
from backend.app.core.config import Settings, get_settings
from backend.app.db.base import Base, get_db
from backend.app.db.models import Agent, EvaluationRunRecord, Tenant
from backend.app.main import create_app


class UnexpectedRuntime:
    async def generate(self, _request):
        raise AssertionError("Generation is not expected without active knowledge")

    async def embed(self, _request):
        raise AssertionError("Embedding is not expected without active knowledge")


def test_evaluation_routes_and_role_boundaries_are_registered() -> None:
    assert "evaluation:write" in ROLE_PERMISSIONS["super_admin"]
    assert "evaluation:write" in ROLE_PERMISSIONS["operator"]
    assert "evaluation:read" in ROLE_PERMISSIONS["auditor"]
    assert "evaluation:write" not in ROLE_PERMISSIONS["auditor"]

    paths = create_app().openapi()["paths"]
    for path in (
        "/api/admin/evaluation/datasets",
        "/api/admin/evaluation/datasets/{name}/{version}",
        "/api/admin/evaluation/runs",
        "/api/admin/evaluation/runs/{run_id}",
    ):
        operations = paths[path]
        for operation in operations.values():
            if not isinstance(operation, dict) or "responses" not in operation:
                continue
            security = operation.get("security", [])
            assert security
            assert all("TenantApiKey" not in item for item in security)


async def _test_app(
    database_path: Path,
) -> tuple[FastAPI, AsyncEngine, async_sessionmaker]:
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{database_path.as_posix()}"
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)

    async with sessions() as session:
        session.add(Tenant(id="tenant-eval", name="Evaluation Tenant"))
        session.add(
            Agent(
                id="agent-eval",
                tenant_id="tenant-eval",
                name="Evaluation Agent",
                prompt_version="prompt-v3",
                knowledge_mode="required",
            )
        )
        await session.commit()

    app = create_app()

    async def override_db():
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[require_admin_access] = lambda: None
    app.dependency_overrides[get_core_ai_runtime] = UnexpectedRuntime
    app.dependency_overrides[get_settings] = lambda: Settings(
        environment="test",
        database_url=f"sqlite+aiosqlite:///{database_path.as_posix()}",
        deepseek_api_key="test-key",
        _env_file=None,
    )
    return app, engine, sessions


@pytest.mark.asyncio
async def test_admin_can_execute_and_reload_a_persisted_run(
    tmp_path: Path,
) -> None:
    app, engine, sessions = await _test_app(tmp_path / "evaluation.db")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            datasets = await client.get("/api/admin/evaluation/datasets")
            assert datasets.status_code == 200
            assert datasets.json()[0]["name"] == "golden-questions"

            detail = await client.get(
                "/api/admin/evaluation/datasets/golden-questions/v1"
            )
            assert detail.status_code == 200
            assert len(detail.json()["records"]) == 20

            created = await client.post(
                "/api/admin/evaluation/runs",
                json={
                    "dataset_name": "golden-questions",
                    "dataset_version": "v1",
                    "tenant_id": "tenant-eval",
                    "agent_id": "agent-eval",
                },
            )
            assert created.status_code == 202
            run_id = created.json()["run_id"]

            loaded = await client.get(
                f"/api/admin/evaluation/runs/{run_id}"
            )
            assert loaded.status_code == 200
            payload = loaded.json()
            assert payload["status"] == "completed"
            assert payload["tenant_id"] == "tenant-eval"
            assert payload["agent_id"] == "agent-eval"
            assert payload["configuration"]["prompt_version"] == "prompt-v3"
            assert payload["summary"]["total_cases"] == 20
            assert len(payload["results"]) == 20
            assert {
                item["tenant_id"] for item in payload["results"]
            } == {"tenant-eval"}

            history = await client.get("/api/admin/evaluation/runs")
            assert history.status_code == 200
            assert history.json()[0]["run_id"] == run_id

        async with sessions() as session:
            assert await session.get(EvaluationRunRecord, run_id) is not None
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_run_rejects_agent_outside_requested_tenant(
    tmp_path: Path,
) -> None:
    app, engine, _sessions = await _test_app(tmp_path / "scope.db")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/admin/evaluation/runs",
                json={
                    "dataset_name": "golden-questions",
                    "dataset_version": "v1",
                    "tenant_id": "another-tenant",
                    "agent_id": "agent-eval",
                },
            )
        assert response.status_code == 404
    finally:
        await engine.dispose()
