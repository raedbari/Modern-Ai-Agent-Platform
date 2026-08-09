"""Integration tests for customer widget settings API routes."""

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
    CustomerIdentity,
    RefreshSession,
    Tenant,
    TenantMembership,
    TenantUser,
    WidgetAllowedOrigin,
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
    role: str = "tenant_owner",
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
            role=role,
            status="approved",
        )
        session.add(membership)
        await session.commit()
        
        session_id = refresh_session.id
    
    jwt_token = generate_tenant_user_jwt(
        user_id=user_id,
        session_id=session_id,
        tenant_id=tenant_id,
        role=role,
        secret_key=settings.jwt_secret_key,
    )
    
    return jwt_token


def _auth_headers(jwt_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {jwt_token}"}


@pytest.mark.asyncio
async def test_get_widget_settings_for_own_agent(
    tmp_path: Path,
) -> None:
    """Test approved user can get widget settings for own agent."""
    app, engine, session_factory = await _open_test_app(
        tmp_path / "widget-get.sqlite3"
    )
    try:
        jwt_token = await _seed_tenant_with_user(
            session_factory,
            tenant_id="tenant-a",
            user_id="user-owner",
            role="tenant_owner",
        )
        
        # Pre-seed agent and widget settings
        async with session_factory() as session:
            session.add(Agent(id="agent-1", tenant_id="tenant-a", name="Agent 1"))
            await session.flush()
            session.add(
                AgentWidgetSettings(
                    tenant_id="tenant-a",
                    agent_id="agent-1",
                    public_widget_id="widget-public-123",
                    is_enabled=True,
                    display_name="Support Bot",
                    greeting="Hello!",
                )
            )
            await session.commit()
        
        headers = _auth_headers(jwt_token)
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/api/customer/agents/agent-1/widget-settings",
                headers=headers,
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["agent_id"] == "agent-1"
        assert data["is_enabled"] is True
        assert data["display_name"] == "Support Bot"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_update_widget_settings_for_own_agent(
    tmp_path: Path,
) -> None:
    """Test approved user can update widget settings for own agent."""
    app, engine, session_factory = await _open_test_app(
        tmp_path / "widget-update.sqlite3"
    )
    try:
        jwt_token = await _seed_tenant_with_user(
            session_factory,
            tenant_id="tenant-a",
            user_id="user-editor",
            role="knowledge_editor",
        )
        
        # Pre-seed agent and widget settings
        async with session_factory() as session:
            session.add(Agent(id="agent-1", tenant_id="tenant-a", name="Agent 1"))
            await session.flush()
            session.add(
                AgentWidgetSettings(
                    tenant_id="tenant-a",
                    agent_id="agent-1",
                    public_widget_id="widget-public-123",
                    is_enabled=False,
                    display_name="Old Name",
                )
            )
            await session.commit()
        
        headers = _auth_headers(jwt_token)
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.put(
                "/api/customer/agents/agent-1/widget-settings",
                headers=headers,
                json={
                    "is_enabled": True,
                    "display_name": "Updated Name",
                    "greeting": "Welcome!",
                    "primary_color": "#FF5733",
                },
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["is_enabled"] is True
        assert data["display_name"] == "Updated Name"
        assert data["greeting"] == "Welcome!"
        assert data["primary_color"] == "#FF5733"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_cross_tenant_widget_access_returns_404(
    tmp_path: Path,
) -> None:
    """Test user cannot access widget settings from other tenant's agent."""
    app, engine, session_factory = await _open_test_app(
        tmp_path / "widget-cross-tenant.sqlite3"
    )
    try:
        # Tenant A
        jwt_token_a = await _seed_tenant_with_user(
            session_factory,
            tenant_id="tenant-a",
            user_id="user-a",
            role="tenant_owner",
        )
        
        # Tenant B
        jwt_token_b = await _seed_tenant_with_user(
            session_factory,
            tenant_id="tenant-b",
            user_id="user-b",
            role="tenant_owner",
        )
        
        # Tenant A's agent
        async with session_factory() as session:
            session.add(Agent(id="agent-a", tenant_id="tenant-a", name="Agent A"))
            await session.flush()
            session.add(
                AgentWidgetSettings(
                    tenant_id="tenant-a",
                    agent_id="agent-a",
                    public_widget_id="widget-public-a",
                )
            )
            await session.commit()
        
        headers_b = _auth_headers(jwt_token_b)
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # Tenant B tries to access Tenant A's widget settings
            get_resp = await client.get(
                "/api/customer/agents/agent-a/widget-settings",
                headers=headers_b,
            )
            update_resp = await client.put(
                "/api/customer/agents/agent-a/widget-settings",
                headers=headers_b,
                json={"is_enabled": True},
            )
        
        assert get_resp.status_code == 404
        assert update_resp.status_code == 404
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_knowledge_editor_can_manage_widget_settings(
    tmp_path: Path,
) -> None:
    """Test knowledge_editor role can manage widget settings."""
    app, engine, session_factory = await _open_test_app(
        tmp_path / "widget-editor.sqlite3"
    )
    try:
        jwt_token = await _seed_tenant_with_user(
            session_factory,
            tenant_id="tenant-a",
            user_id="user-editor",
            role="knowledge_editor",
        )
        
        async with session_factory() as session:
            session.add(Agent(id="agent-1", tenant_id="tenant-a", name="Agent 1"))
            await session.flush()
            session.add(
                AgentWidgetSettings(
                    tenant_id="tenant-a",
                    agent_id="agent-1",
                    public_widget_id="widget-public-123",
                )
            )
            await session.commit()
        
        headers = _auth_headers(jwt_token)
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            get_resp = await client.get(
                "/api/customer/agents/agent-1/widget-settings",
                headers=headers,
            )
            update_resp = await client.put(
                "/api/customer/agents/agent-1/widget-settings",
                headers=headers,
                json={"is_enabled": True, "display_name": "Editor Updated"},
            )
        
        assert get_resp.status_code == 200
        assert update_resp.status_code == 200
        assert update_resp.json()["display_name"] == "Editor Updated"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_tenant_owner_can_update_widget_settings(
    tmp_path: Path,
) -> None:
    """Test tenant_owner role can update widget settings."""
    app, engine, session_factory = await _open_test_app(
        tmp_path / "widget-owner.sqlite3"
    )
    try:
        jwt_token = await _seed_tenant_with_user(
            session_factory,
            tenant_id="tenant-a",
            user_id="user-owner",
            role="tenant_owner",
        )
        
        async with session_factory() as session:
            session.add(Agent(id="agent-1", tenant_id="tenant-a", name="Agent 1"))
            await session.flush()
            session.add(
                AgentWidgetSettings(
                    tenant_id="tenant-a",
                    agent_id="agent-1",
                    public_widget_id="widget-public-123",
                )
            )
            await session.commit()
        
        headers = _auth_headers(jwt_token)
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.put(
                "/api/customer/agents/agent-1/widget-settings",
                headers=headers,
                json={
                    "is_enabled": True,
                    "primary_color": "#00FF00",
                    "allowed_origins": ["https://example.com"],
                },
            )
        
        assert response.status_code == 200
        assert response.json()["is_enabled"] is True
        assert response.json()["primary_color"] == "#00FF00"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_conversation_viewer_cannot_update_widget_settings(
    tmp_path: Path,
) -> None:
    """Test conversation_viewer role cannot update widget settings."""
    app, engine, session_factory = await _open_test_app(
        tmp_path / "widget-viewer.sqlite3"
    )
    try:
        # Owner creates widget
        jwt_owner = await _seed_tenant_with_user(
            session_factory,
            tenant_id="tenant-a",
            user_id="user-owner",
            role="tenant_owner",
        )
        
        # Viewer has read-only
        jwt_viewer = await _seed_tenant_with_user(
            session_factory,
            tenant_id="tenant-a",
            user_id="user-viewer",
            role="conversation_viewer",
        )
        
        async with session_factory() as session:
            session.add(Agent(id="agent-1", tenant_id="tenant-a", name="Agent 1"))
            await session.flush()
            session.add(
                AgentWidgetSettings(
                    tenant_id="tenant-a",
                    agent_id="agent-1",
                    public_widget_id="widget-public-123",
                )
            )
            await session.commit()
        
        viewer_headers = _auth_headers(jwt_viewer)
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # Can read
            get_resp = await client.get(
                "/api/customer/agents/agent-1/widget-settings",
                headers=viewer_headers,
            )
            
            # Cannot update
            update_resp = await client.put(
                "/api/customer/agents/agent-1/widget-settings",
                headers=viewer_headers,
                json={"is_enabled": True},
            )
        
        assert get_resp.status_code == 200
        assert update_resp.status_code == 403
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_widget_settings_with_allowed_origins(
    tmp_path: Path,
) -> None:
    """Test updating widget settings with allowed origins."""
    app, engine, session_factory = await _open_test_app(
        tmp_path / "widget-origins.sqlite3"
    )
    try:
        jwt_token = await _seed_tenant_with_user(
            session_factory,
            tenant_id="tenant-a",
            user_id="user-owner",
            role="tenant_owner",
        )
        
        async with session_factory() as session:
            session.add(Agent(id="agent-1", tenant_id="tenant-a", name="Agent 1"))
            await session.flush()
            session.add(
                AgentWidgetSettings(
                    tenant_id="tenant-a",
                    agent_id="agent-1",
                    public_widget_id="widget-public-123",
                )
            )
            await session.commit()
        
        headers = _auth_headers(jwt_token)
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.put(
                "/api/customer/agents/agent-1/widget-settings",
                headers=headers,
                json={
                    "allowed_origins": [
                        "https://example.com",
                        "https://app.example.com",
                    ],
                },
            )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["allowed_origins"]) == 2
        assert "https://example.com" in data["allowed_origins"]
        assert "https://app.example.com" in data["allowed_origins"]
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_get_nonexistent_widget_settings_returns_404(
    tmp_path: Path,
) -> None:
    """Test getting widget settings for agent without settings returns 404."""
    app, engine, session_factory = await _open_test_app(
        tmp_path / "widget-nonexistent.sqlite3"
    )
    try:
        jwt_token = await _seed_tenant_with_user(
            session_factory,
            tenant_id="tenant-a",
            user_id="user-owner",
            role="tenant_owner",
        )
        
        # Agent exists but no widget settings
        async with session_factory() as session:
            session.add(Agent(id="agent-1", tenant_id="tenant-a", name="Agent 1"))
            await session.commit()
        
        headers = _auth_headers(jwt_token)
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/api/customer/agents/agent-1/widget-settings",
                headers=headers,
            )
        
        assert response.status_code == 404
    finally:
        await engine.dispose()
