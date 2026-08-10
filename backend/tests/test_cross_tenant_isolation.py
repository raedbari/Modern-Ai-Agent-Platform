"""Comprehensive cross-tenant isolation tests (Task 11.1)."""

from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)

from backend.app.auth.tenant_jwt import generate_tenant_user_jwt
from backend.app.core.config import Settings
from backend.app.db.base import Base, get_db
from backend.app.db.models import (
    Agent,
    AgentWidgetSettings,
    Conversation,
    CustomerIdentity,
    KnowledgeBaseModel,
    DocumentModel,
    RefreshSession,
    Tenant,
    TenantMembership,
    TenantUser,
)
from backend.app.main import create_app


async def _open_test_app(
    database_path: Path,
) -> tuple[FastAPI, AsyncEngine, async_sessionmaker]:
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )

    @event.listens_for(engine.sync_engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine,
        expire_on_commit=False,
    )

    application = create_app()

    async def override_get_db():
        async with session_factory() as session:
            yield session

    application.dependency_overrides[get_db] = override_get_db
    return application, engine, session_factory


async def _seed_tenant_with_user(
    session_factory: async_sessionmaker,
    *,
    tenant_id: str,
    user_id: str,
) -> str:
    """Seed tenant, user, membership and return JWT token."""
    settings = Settings(_env_file=None)
    
    async with session_factory() as session:
        session.add(Tenant(id=tenant_id, name=tenant_id))
        await session.flush()
        
        identity = CustomerIdentity(
            id=f"identity-{user_id}",
            email=f"{user_id}@test.com",
            is_email_verified=True,
        )
        session.add(identity)
        await session.flush()
        
        user = TenantUser(
            id=user_id,
            customer_identity_id=identity.id,
            display_name=user_id,
        )
        session.add(user)
        await session.flush()
        
        refresh_session = RefreshSession(
            tenant_user_id=user_id,
            is_active=True,
        )
        session.add(refresh_session)
        await session.flush()
        
        membership = TenantMembership(
            tenant_id=tenant_id,
            tenant_user_id=user_id,
            role="tenant_owner",
            status="approved",
        )
        session.add(membership)
        await session.commit()
        
        session_id = refresh_session.id
    
    jwt_token = generate_tenant_user_jwt(
        user_id=user_id,
        session_id=session_id,
        tenant_id=tenant_id,
        role="tenant_owner",
        secret_key=settings.jwt_secret_key,
    )
    
    return jwt_token


def _auth_headers(jwt_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {jwt_token}"}


@pytest.mark.asyncio
async def test_tenant_a_cannot_read_tenant_b_agent(
    tmp_path: Path,
) -> None:
    """Test Tenant A cannot read Tenant B agent (returns 404)."""
    app, engine, session_factory = await _open_test_app(
        tmp_path / "cross-tenant-agent-read.sqlite3"
    )
    try:
        jwt_a = await _seed_tenant_with_user(
            session_factory, tenant_id="tenant-a", user_id="user-a"
        )
        jwt_b = await _seed_tenant_with_user(
            session_factory, tenant_id="tenant-b", user_id="user-b"
        )
        
        # Tenant B creates agent
        async with session_factory() as session:
            session.add(Agent(id="agent-b", tenant_id="tenant-b", name="Agent B"))
            await session.commit()
        
        # Tenant A tries to read
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/customer/agents/agent-b",
                headers=_auth_headers(jwt_a),
            )
        
        assert response.status_code == 404
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_tenant_a_cannot_update_tenant_b_agent(
    tmp_path: Path,
) -> None:
    """Test Tenant A cannot update Tenant B agent (returns 404)."""
    app, engine, session_factory = await _open_test_app(
        tmp_path / "cross-tenant-agent-update.sqlite3"
    )
    try:
        jwt_a = await _seed_tenant_with_user(
            session_factory, tenant_id="tenant-a", user_id="user-a"
        )
        jwt_b = await _seed_tenant_with_user(
            session_factory, tenant_id="tenant-b", user_id="user-b"
        )
        
        async with session_factory() as session:
            session.add(Agent(id="agent-b", tenant_id="tenant-b", name="Agent B"))
            await session.commit()
        
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.patch(
                "/api/customer/agents/agent-b",
                headers=_auth_headers(jwt_a),
                json={"name": "Hacked"},
            )
        
        assert response.status_code == 404
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_tenant_a_cannot_delete_tenant_b_agent(
    tmp_path: Path,
) -> None:
    """Test Tenant A cannot delete Tenant B agent (returns 404)."""
    app, engine, session_factory = await _open_test_app(
        tmp_path / "cross-tenant-agent-delete.sqlite3"
    )
    try:
        jwt_a = await _seed_tenant_with_user(
            session_factory, tenant_id="tenant-a", user_id="user-a"
        )
        jwt_b = await _seed_tenant_with_user(
            session_factory, tenant_id="tenant-b", user_id="user-b"
        )
        
        async with session_factory() as session:
            session.add(Agent(id="agent-b", tenant_id="tenant-b", name="Agent B"))
            await session.commit()
        
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.delete(
                "/api/customer/agents/agent-b",
                headers=_auth_headers(jwt_a),
            )
        
        assert response.status_code == 404
        
        # Verify agent still exists
        async with session_factory() as session:
            agent = await session.get(Agent, "agent-b")
            assert agent is not None
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_tenant_a_cannot_access_tenant_b_knowledge_base(
    tmp_path: Path,
) -> None:
    """Test Tenant A cannot access Tenant B knowledge base (returns 404)."""
    app, engine, session_factory = await _open_test_app(
        tmp_path / "cross-tenant-kb.sqlite3"
    )
    try:
        jwt_a = await _seed_tenant_with_user(
            session_factory, tenant_id="tenant-a", user_id="user-a"
        )
        jwt_b = await _seed_tenant_with_user(
            session_factory, tenant_id="tenant-b", user_id="user-b"
        )
        
        # Tenant B creates KB
        async with session_factory() as session:
            session.add(Agent(id="agent-b", tenant_id="tenant-b", name="Agent B"))
            await session.flush()
            session.add(
                KnowledgeBaseModel(
                    id="kb-b",
                    tenant_id="tenant-b",
                    name="KB B",
                )
            )
            await session.commit()
        
        # Tenant A tries to access (using JWT Bearer)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/knowledge-bases/kb-b",
                headers=_auth_headers(jwt_a),
            )
        
        assert response.status_code == 404
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_tenant_a_cannot_access_tenant_b_documents(
    tmp_path: Path,
) -> None:
    """Test Tenant A cannot access Tenant B documents (returns 404)."""
    app, engine, session_factory = await _open_test_app(
        tmp_path / "cross-tenant-docs.sqlite3"
    )
    try:
        jwt_a = await _seed_tenant_with_user(
            session_factory, tenant_id="tenant-a", user_id="user-a"
        )
        jwt_b = await _seed_tenant_with_user(
            session_factory, tenant_id="tenant-b", user_id="user-b"
        )
        
        # Tenant B creates KB and document
        async with session_factory() as session:
            session.add(Agent(id="agent-b", tenant_id="tenant-b", name="Agent B"))
            await session.flush()
            session.add(
                KnowledgeBaseModel(id="kb-b", tenant_id="tenant-b", name="KB B")
            )
            await session.flush()
            session.add(
                DocumentModel(
                    id="doc-b",
                    knowledge_base_id="kb-b",
                    agent_id="agent-b",
                    original_filename="doc.txt",
                    status="ready",
                )
            )
            await session.commit()
        
        # Tenant A tries to access
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/knowledge-bases/kb-b/documents/doc-b",
                headers=_auth_headers(jwt_a),
            )
        
        assert response.status_code == 404
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_tenant_a_cannot_access_tenant_b_widget_settings(
    tmp_path: Path,
) -> None:
    """Test Tenant A cannot access Tenant B widget settings (returns 404)."""
    app, engine, session_factory = await _open_test_app(
        tmp_path / "cross-tenant-widget.sqlite3"
    )
    try:
        jwt_a = await _seed_tenant_with_user(
            session_factory, tenant_id="tenant-a", user_id="user-a"
        )
        jwt_b = await _seed_tenant_with_user(
            session_factory, tenant_id="tenant-b", user_id="user-b"
        )
        
        # Tenant B creates widget
        async with session_factory() as session:
            session.add(Agent(id="agent-b", tenant_id="tenant-b", name="Agent B"))
            await session.flush()
            session.add(
                AgentWidgetSettings(
                    tenant_id="tenant-b",
                    agent_id="agent-b",
                    public_widget_id="widget-b",
                )
            )
            await session.commit()
        
        # Tenant A tries to access
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get(
                "/api/customer/agents/agent-b/widget-settings",
                headers=_auth_headers(jwt_a),
            )
        
        assert response.status_code == 404
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_cross_tenant_isolation_comprehensive(
    tmp_path: Path,
) -> None:
    """Comprehensive test: Tenant A cannot access any Tenant B resources."""
    app, engine, session_factory = await _open_test_app(
        tmp_path / "cross-tenant-comprehensive.sqlite3"
    )
    try:
        jwt_a = await _seed_tenant_with_user(
            session_factory, tenant_id="tenant-a", user_id="user-a"
        )
        jwt_b = await _seed_tenant_with_user(
            session_factory, tenant_id="tenant-b", user_id="user-b"
        )
        
        # Seed all Tenant B resources
        async with session_factory() as session:
            session.add(Agent(id="agent-b", tenant_id="tenant-b", name="Agent B"))
            await session.flush()
            session.add(
                KnowledgeBaseModel(id="kb-b", tenant_id="tenant-b", name="KB B")
            )
            await session.flush()
            session.add(
                DocumentModel(
                    id="doc-b",
                    knowledge_base_id="kb-b",
                    agent_id="agent-b",
                    original_filename="doc.txt",
                    status="ready",
                )
            )
            session.add(Conversation(id="conv-b", agent_id="agent-b"))
            session.add(
                AgentWidgetSettings(
                    tenant_id="tenant-b",
                    agent_id="agent-b",
                    public_widget_id="widget-b",
                )
            )
            await session.commit()
        
        headers_a = _auth_headers(jwt_a)
        
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Test all endpoints return 404
            responses = await asyncio.gather(
                client.get("/api/customer/agents/agent-b", headers=headers_a),
                client.get("/api/knowledge-bases/kb-b", headers=headers_a),
                client.get("/api/knowledge-bases/kb-b/documents/doc-b", headers=headers_a),
                client.get("/api/customer/agents/agent-b/widget-settings", headers=headers_a),
            )
        
        for response in responses:
            assert response.status_code == 404, f"Expected 404, got {response.status_code}"
    finally:
        await engine.dispose()


import asyncio
