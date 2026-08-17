"""Phase-2 customer resource tests against the current SaaS schema."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.security import HTTPAuthorizationCredentials
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)

from backend.app.api import dependencies
from backend.app.api.dependencies import (
    require_knowledge_context,
    require_tenant_user_jwt,
)
from backend.app.auth import tenant_context
from backend.app.auth.tenant_context import TenantUserContext
from backend.app.core.config import Settings
from backend.app.db.base import Base, get_db
from backend.app.db.models import (
    Agent,
    AgentKnowledgeBase,
    AgentWidgetSettings,
    KnowledgeBaseModel,
    Tenant,
)
from backend.app.main import create_app


async def _open_app(
    database_path: Path,
):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )

    @event.listens_for(
        engine.sync_engine,
        "connect",
    )
    def _fk(connection, _record):
        cursor = connection.cursor()
        cursor.execute(
            "PRAGMA foreign_keys=ON"
        )
        cursor.close()

    async with engine.begin() as connection:
        await connection.run_sync(
            Base.metadata.create_all
        )

    sessions = async_sessionmaker(
        engine,
        expire_on_commit=False,
    )

    app = create_app()

    async def override_db():
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_db] = (
        override_db
    )

    return app, engine, sessions


def _context(
    *,
    tenant_id: str = "tenant-a",
    role: str = "tenant_owner",
) -> TenantUserContext:
    return TenantUserContext(
        user_id="user-a",
        email="owner@example.test",
        display_name="Owner",
        tenant_id=tenant_id,
        membership_id="membership-a",
        role=role,  # type: ignore[arg-type]
        auth_method="jwt",
        session_family_id="family-a",
        jti="jti-a",
    )


@pytest.mark.asyncio
async def test_customer_agent_create_persists_current_schema(
    tmp_path: Path,
) -> None:
    app, engine, sessions = await _open_app(
        tmp_path / "customer-agent.sqlite3"
    )

    try:
        async with sessions() as session:
            session.add(
                Tenant(
                    id="tenant-a",
                    name="Tenant A",
                )
            )
            await session.commit()

        app.dependency_overrides[
            require_tenant_user_jwt
        ] = lambda: _context()

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/customer/agents",
                json={
                    "name": "Travel Support",
                    "knowledge_mode": "preferred",
                },
            )

        assert response.status_code == 201, response.text
        agent_id = response.json()["id"]

        async with sessions() as session:
            agent = await session.get(
                Agent,
                agent_id,
            )

            assert agent is not None
            assert agent.tenant_id == "tenant-a"
            assert agent.name == "Travel Support"

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_customer_agent_cross_tenant_is_hidden(
    tmp_path: Path,
) -> None:
    app, engine, sessions = await _open_app(
        tmp_path / "cross-agent.sqlite3"
    )

    try:
        async with sessions() as session:
            session.add_all(
                [
                    Tenant(
                        id="tenant-a",
                        name="Tenant A",
                    ),
                    Tenant(
                        id="tenant-b",
                        name="Tenant B",
                    ),
                ]
            )
            await session.flush()

            session.add(
                Agent(
                    id="agent-b",
                    tenant_id="tenant-b",
                    name="Tenant B Agent",
                )
            )
            await session.commit()

        app.dependency_overrides[
            require_tenant_user_jwt
        ] = lambda: _context(
            tenant_id="tenant-a",
        )

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/api/customer/agents/agent-b"
            )

        assert response.status_code == 404

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_conversation_viewer_cannot_create_agent(
    tmp_path: Path,
) -> None:
    app, engine, sessions = await _open_app(
        tmp_path / "viewer-agent.sqlite3"
    )

    try:
        async with sessions() as session:
            session.add(
                Tenant(
                    id="tenant-a",
                    name="Tenant A",
                )
            )
            await session.commit()

        app.dependency_overrides[
            require_tenant_user_jwt
        ] = lambda: _context(
            role="conversation_viewer",
        )

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/customer/agents",
                json={
                    "name": "Forbidden",
                },
            )

        assert response.status_code == 403

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_widget_put_upserts_settings(
    tmp_path: Path,
) -> None:
    app, engine, sessions = await _open_app(
        tmp_path / "widget.sqlite3"
    )

    try:
        async with sessions() as session:
            session.add(
                Tenant(
                    id="tenant-a",
                    name="Tenant A",
                )
            )
            await session.flush()

            session.add(
                Agent(
                    id="agent-a",
                    tenant_id="tenant-a",
                    name="Agent A",
                )
            )
            await session.commit()

        app.dependency_overrides[
            require_tenant_user_jwt
        ] = lambda: _context()

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.put(
                "/api/customer/agents/agent-a/widget-settings",
                json={
                    "display_name": "Travel Bot",
                    "greeting": "Welcome",
                    "primary_color": "#663399",
                    "allowed_origins": [
                        "https://example.com"
                    ],
                },
            )

        assert response.status_code == 200, response.text
        data = response.json()

        assert data["display_name"] == "Travel Bot"
        assert data["public_widget_id"]
        assert data["allowed_origins"] == [
            "https://example.com"
        ]

        async with sessions() as session:
            row = await session.scalar(
                select(
                    AgentWidgetSettings
                ).where(
                    AgentWidgetSettings.agent_id
                    == "agent-a",
                    AgentWidgetSettings.tenant_id
                    == "tenant-a",
                )
            )

            assert row is not None
            assert row.display_name == "Travel Bot"

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_knowledge_accepts_live_tenant_jwt_context(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _app, engine, sessions = await _open_app(
        tmp_path / "knowledge-jwt.sqlite3"
    )

    try:
        async with sessions() as session:
            session.add(
                Tenant(
                    id="tenant-a",
                    name="Tenant A",
                )
            )
            await session.flush()

            session.add(
                Agent(
                    id="agent-a",
                    tenant_id="tenant-a",
                    name="Agent A",
                )
            )
            await session.commit()

        async def fake_validate(
            token,
            session,
            settings,
        ):
            return _context()

        monkeypatch.setattr(
            tenant_context,
            "validate_tenant_user_context",
            fake_validate,
        )

        async with sessions() as session:
            resolved = (
                await require_knowledge_context(
                    session=session,
                    raw_api_key=None,
                    settings=Settings(
                        _env_file=None
                    ),
                    credentials=(
                        HTTPAuthorizationCredentials(
                            scheme="Bearer",
                            credentials="test-token",
                        )
                    ),
                    agent_id="agent-a",
                )
            )

        assert resolved.tenant_id == "tenant-a"
        assert resolved.agent_id == "agent-a"
        assert resolved.auth_method == "tenant_jwt"

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_agent_nullable_fields_clear_and_omission_persists(tmp_path: Path) -> None:
    app, engine, sessions = await _open_app(tmp_path / "agent-null-clear.sqlite3")
    try:
        async with sessions() as session:
            session.add(Tenant(id="tenant-a", name="Tenant A"))
            await session.flush()
            session.add(Agent(id="agent-a", tenant_id="tenant-a", name="Agent A", system_prompt="Keep", contact_message="Contact"))
            await session.commit()
        app.dependency_overrides[require_tenant_user_jwt] = lambda: _context()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            omitted = await client.patch("/api/customer/agents/agent-a", json={"name": "Agent Renamed"})
            assert omitted.status_code == 200, omitted.text
            assert omitted.json()["system_prompt"] == "Keep"
            assert omitted.json()["contact_message"] == "Contact"
            cleared = await client.patch(
                "/api/customer/agents/agent-a",
                json={"system_prompt": None, "contact_message": None},
            )
            assert cleared.status_code == 200, cleared.text
            assert cleared.json()["system_prompt"] is None
            assert cleared.json()["contact_message"] is None
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_widget_nullable_fields_and_origins_clear_by_presence(tmp_path: Path) -> None:
    app, engine, sessions = await _open_app(tmp_path / "widget-null-clear.sqlite3")
    try:
        async with sessions() as session:
            session.add(Tenant(id="tenant-a", name="Tenant A"))
            await session.flush()
            session.add(Agent(id="agent-a", tenant_id="tenant-a", name="Agent A"))
            await session.commit()
        app.dependency_overrides[require_tenant_user_jwt] = lambda: _context()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            created = await client.put(
                "/api/customer/agents/agent-a/widget-settings",
                json={"display_name": "Display", "greeting": "Hello", "allowed_origins": ["https://example.com"]},
            )
            assert created.status_code == 200, created.text
            omitted = await client.put("/api/customer/agents/agent-a/widget-settings", json={"appearance": "dark"})
            assert omitted.status_code == 200, omitted.text
            assert omitted.json()["display_name"] == "Display"
            assert omitted.json()["allowed_origins"] == ["https://example.com"]
            cleared = await client.put(
                "/api/customer/agents/agent-a/widget-settings",
                json={"display_name": None, "greeting": None, "allowed_origins": []},
            )
            assert cleared.status_code == 200, cleared.text
            assert cleared.json()["display_name"] is None
            assert cleared.json()["greeting"] is None
            assert cleared.json()["allowed_origins"] == []
            rejected = await client.put(
                "/api/customer/agents/agent-a/widget-settings",
                json={"allowed_origins": None},
            )
            assert rejected.status_code == 422
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_customer_knowledge_list_assignment_is_idempotent_and_tenant_scoped(tmp_path: Path) -> None:
    app, engine, sessions = await _open_app(tmp_path / "customer-kb.sqlite3")
    try:
        async with sessions() as session:
            session.add_all([Tenant(id="tenant-a", name="Tenant A"), Tenant(id="tenant-b", name="Tenant B")])
            await session.flush()
            session.add_all([
                Agent(id="agent-a", tenant_id="tenant-a", name="Agent A"),
                Agent(id="agent-a2", tenant_id="tenant-a", name="Agent A2"),
                Agent(id="agent-b", tenant_id="tenant-b", name="Agent B"),
                KnowledgeBaseModel(id="kb-a", tenant_id="tenant-a", name="KB A", description=""),
                KnowledgeBaseModel(id="kb-b", tenant_id="tenant-b", name="KB B", description=""),
            ])
            await session.flush()
            session.add(AgentKnowledgeBase(tenant_id="tenant-a", agent_id="agent-a2", knowledge_base_id="kb-a"))
            await session.commit()
        app.dependency_overrides[require_tenant_user_jwt] = lambda: _context()
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            listed = await client.get("/api/customer/knowledge-bases")
            assert listed.status_code == 200, listed.text
            assert [item["id"] for item in listed.json()] == ["kb-a"]
            first = await client.put("/api/customer/agents/agent-a/knowledge-bases/kb-a")
            second = await client.put("/api/customer/agents/agent-a/knowledge-bases/kb-a")
            assert first.status_code == second.status_code == 200
            assert (await client.put("/api/customer/agents/agent-a/knowledge-bases/kb-b")).status_code == 404
            assert (await client.put("/api/customer/agents/agent-b/knowledge-bases/kb-a")).status_code == 404
        app.dependency_overrides[require_tenant_user_jwt] = lambda: _context(role="conversation_viewer")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            assert (await client.get("/api/customer/knowledge-bases")).status_code == 403
            assert (await client.put("/api/customer/agents/agent-a/knowledge-bases/kb-a")).status_code == 403
        async with sessions() as session:
            assignments = list((await session.scalars(select(AgentKnowledgeBase).where(AgentKnowledgeBase.tenant_id == "tenant-a"))).all())
            assert {(item.agent_id, item.knowledge_base_id) for item in assignments} == {("agent-a", "kb-a"), ("agent-a2", "kb-a")}
    finally:
        await engine.dispose()
