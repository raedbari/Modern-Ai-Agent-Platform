"""HTTP tests for tenant-scoped administrative Agent configuration."""

from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.app.api.dependencies import require_admin_access
from backend.app.auth.admin_context import AdminContext
from backend.app.core.config import Settings, get_settings
from backend.app.db.base import Base, get_db
from backend.app.db.models import AdminAuditLog, Agent, Tenant
from backend.app.main import create_app


_JWT_SECRET = "agent-config-test-secret-that-is-long-enough-123456"


async def _open_app(
    database_path: Path,
    *,
    role: str,
) -> tuple[
    FastAPI,
    AsyncEngine,
    async_sessionmaker[AsyncSession],
]:
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{database_path.as_posix()}"
    )

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    sessions = async_sessionmaker(
        engine,
        expire_on_commit=False,
    )

    app = create_app()

    async def override_db():
        async with sessions() as session:
            yield session

    async def override_admin_access() -> AdminContext:
        return AdminContext(
            admin_id=f"admin-{role}",
            username=f"user-{role}",
            role=role,  # type: ignore[arg-type]
            auth_method="jwt",
        )

    settings = Settings(
        jwt_secret_key=_JWT_SECRET,
        _env_file=None,
    )

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[
        require_admin_access
    ] = override_admin_access

    return app, engine, sessions


async def _seed_data(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    async with sessions() as session:
        session.add_all(
            [
                Tenant(id="tenant-a", name="Tenant A"),
                Tenant(id="tenant-b", name="Tenant B"),
            ]
        )
        await session.flush()

        session.add_all(
            [
                Agent(
                    id="agent-a",
                    tenant_id="tenant-a",
                    name="Original Agent",
                    system_prompt="Original prompt",
                    knowledge_mode="preferred",
                    contact_message="Original contact",
                ),
                Agent(
                    id="agent-b",
                    tenant_id="tenant-b",
                    name="Other Agent",
                    system_prompt="Other prompt",
                    knowledge_mode="required",
                    contact_message="Other contact",
                ),
            ]
        )

        await session.commit()


@pytest.mark.asyncio
async def test_super_admin_updates_config_and_writes_safe_audit(
    tmp_path: Path,
) -> None:
    app, engine, sessions = await _open_app(
        tmp_path / "success.sqlite3",
        role="super_admin",
    )

    try:
        await _seed_data(sessions)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.patch(
                "/api/admin/tenants/tenant-a/agents/agent-a/config",
                json={
                    "name": "  Updated Agent  ",
                    "system_prompt": "Private replacement prompt",
                    "knowledge_mode": "required",
                    "contact_message": None,
                },
            )

        assert response.status_code == 200

        body = response.json()

        assert body["id"] == "agent-a"
        assert body["tenant_id"] == "tenant-a"
        assert body["name"] == "Updated Agent"
        assert body["system_prompt"] == "Private replacement prompt"
        assert body["knowledge_mode"] == "required"
        assert body["contact_message"] is None

        async with sessions() as session:
            audit = await session.scalar(
                select(AdminAuditLog).where(
                    AdminAuditLog.event_type
                    == "agent_config_updated"
                )
            )

        assert audit is not None
        assert audit.outcome == "success"
        assert audit.admin_id == "admin-super_admin"
        assert audit.target_type == "agent"
        assert audit.target_id == "agent-a"
        assert audit.detail == {
            "tenant_id": "tenant-a",
            "changed_fields": [
                "contact_message",
                "knowledge_mode",
                "name",
                "system_prompt",
            ],
        }

        audit_text = str(audit.detail)

        assert "Private replacement prompt" not in audit_text
        assert "Original prompt" not in audit_text
        assert "Original contact" not in audit_text

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_empty_patch_returns_422_without_audit(
    tmp_path: Path,
) -> None:
    app, engine, sessions = await _open_app(
        tmp_path / "empty.sqlite3",
        role="super_admin",
    )

    try:
        await _seed_data(sessions)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.patch(
                "/api/admin/tenants/tenant-a/agents/agent-a/config",
                json={},
            )

        assert response.status_code == 422

        async with sessions() as session:
            agent = await session.get(Agent, "agent-a")
            audit = await session.scalar(
                select(AdminAuditLog).where(
                    AdminAuditLog.event_type
                    == "agent_config_updated"
                )
            )

        assert agent is not None
        assert agent.name == "Original Agent"
        assert audit is None

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_cross_tenant_agent_returns_404_without_mutation(
    tmp_path: Path,
) -> None:
    app, engine, sessions = await _open_app(
        tmp_path / "cross-tenant.sqlite3",
        role="super_admin",
    )

    try:
        await _seed_data(sessions)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.patch(
                "/api/admin/tenants/tenant-b/agents/agent-a/config",
                json={"name": "Illegal cross-tenant update"},
            )

        assert response.status_code == 404

        async with sessions() as session:
            agent = await session.get(Agent, "agent-a")

        assert agent is not None
        assert agent.name == "Original Agent"

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_operator_has_agent_write_permission(
    tmp_path: Path,
) -> None:
    app, engine, sessions = await _open_app(
        tmp_path / "operator.sqlite3",
        role="operator",
    )

    try:
        await _seed_data(sessions)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.patch(
                "/api/admin/tenants/tenant-a/agents/agent-a/config",
                json={"name": "Operator Updated Agent"},
            )

        assert response.status_code == 200
        assert response.json()["name"] == "Operator Updated Agent"

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_auditor_cannot_update_agent_config(
    tmp_path: Path,
) -> None:
    app, engine, sessions = await _open_app(
        tmp_path / "auditor.sqlite3",
        role="auditor",
    )

    try:
        await _seed_data(sessions)

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.patch(
                "/api/admin/tenants/tenant-a/agents/agent-a/config",
                json={"name": "Forbidden update"},
            )

        assert response.status_code == 403

        async with sessions() as session:
            agent = await session.get(Agent, "agent-a")
            audit = await session.scalar(
                select(AdminAuditLog).where(
                    AdminAuditLog.event_type
                    == "agent_config_updated"
                )
            )

        assert agent is not None
        assert agent.name == "Original Agent"
        assert audit is None

    finally:
        await engine.dispose()
