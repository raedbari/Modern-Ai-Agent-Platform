"""Integration tests for customer agent API routes."""

from pathlib import Path
from unittest.mock import AsyncMock

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
    CustomerIdentity,
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
    role: str = "tenant_owner",
    status: str = "approved",
) -> str:
    """Seed tenant, user, membership and return JWT token."""
    settings = Settings(_env_file=None)
    
    async with session_factory() as session:
        # Create tenant
        session.add(Tenant(id=tenant_id, name=tenant_id))
        await session.flush()
        
        # Create customer identity
        identity = CustomerIdentity(
            id=f"identity-{user_id}",
            email=f"{user_id}@test.com",
            is_email_verified=True,
        )
        session.add(identity)
        await session.flush()
        
        # Create tenant user
        user = TenantUser(
            id=user_id,
            customer_identity_id=identity.id,
            display_name=user_id,
        )
        session.add(user)
        await session.flush()
        
        # Create refresh session
        refresh_session = RefreshSession(
            tenant_user_id=user_id,
            is_active=True,
        )
        session.add(refresh_session)
        await session.flush()
        
        # Create membership
        membership = TenantMembership(
            tenant_id=tenant_id,
            tenant_user_id=user_id,
            role=role,
            status=status,
        )
        session.add(membership)
        await session.commit()
        
        session_id = refresh_session.id
    
    # Generate JWT
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
async def test_create_agent_with_approved_user(
    tmp_path: Path,
) -> None:
    """Test approved user can create agent."""
    app, engine, session_factory = await _open_test_app(
        tmp_path / "agents-create.sqlite3"
    )
    try:
        jwt_token = await _seed_tenant_with_user(
            session_factory,
            tenant_id="tenant-a",
            user_id="user-owner",
            role="tenant_owner",
        )
        
        headers = _auth_headers(jwt_token)
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/customer/agents",
                headers=headers,
                json={
                    "name": "Support Agent",
                    "system_prompt": "You are a helpful assistant.",
                    "knowledge_mode": "preferred",
                },
            )
        
        assert response.status_code == 201, response.text
        data = response.json()
        assert data["name"] == "Support Agent"
        assert data["tenant_id"] == "tenant-a"
        assert data["is_active"] is True
        assert "id" in data
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_list_agents_for_tenant(
    tmp_path: Path,
) -> None:
    """Test user can list all agents for their tenant."""
    app, engine, session_factory = await _open_test_app(
        tmp_path / "agents-list.sqlite3"
    )
    try:
        jwt_token = await _seed_tenant_with_user(
            session_factory,
            tenant_id="tenant-a",
            user_id="user-owner",
            role="tenant_owner",
        )
        
        # Pre-seed an agent
        async with session_factory() as session:
            session.add(
                Agent(
                    id="agent-1",
                    tenant_id="tenant-a",
                    name="Existing Agent",
                )
            )
            await session.commit()
        
        headers = _auth_headers(jwt_token)
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/api/customer/agents",
                headers=headers,
            )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "agent-1"
        assert data[0]["name"] == "Existing Agent"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_get_agent_by_id(
    tmp_path: Path,
) -> None:
    """Test user can get specific agent by ID."""
    app, engine, session_factory = await _open_test_app(
        tmp_path / "agents-get.sqlite3"
    )
    try:
        jwt_token = await _seed_tenant_with_user(
            session_factory,
            tenant_id="tenant-a",
            user_id="user-owner",
            role="tenant_owner",
        )
        
        # Pre-seed an agent
        async with session_factory() as session:
            session.add(
                Agent(
                    id="agent-1",
                    tenant_id="tenant-a",
                    name="Test Agent",
                )
            )
            await session.commit()
        
        headers = _auth_headers(jwt_token)
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/api/customer/agents/agent-1",
                headers=headers,
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "agent-1"
        assert data["name"] == "Test Agent"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_update_agent(
    tmp_path: Path,
) -> None:
    """Test user can update their agent."""
    app, engine, session_factory = await _open_test_app(
        tmp_path / "agents-update.sqlite3"
    )
    try:
        jwt_token = await _seed_tenant_with_user(
            session_factory,
            tenant_id="tenant-a",
            user_id="user-editor",
            role="knowledge_editor",
        )
        
        # Pre-seed an agent
        async with session_factory() as session:
            session.add(
                Agent(
                    id="agent-1",
                    tenant_id="tenant-a",
                    name="Old Name",
                    system_prompt="Old prompt",
                )
            )
            await session.commit()
        
        headers = _auth_headers(jwt_token)
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.patch(
                "/api/customer/agents/agent-1",
                headers=headers,
                json={
                    "name": "Updated Name",
                    "system_prompt": "Updated prompt",
                },
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["system_prompt"] == "Updated prompt"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_delete_agent(
    tmp_path: Path,
) -> None:
    """Test user can delete their agent."""
    app, engine, session_factory = await _open_test_app(
        tmp_path / "agents-delete.sqlite3"
    )
    try:
        jwt_token = await _seed_tenant_with_user(
            session_factory,
            tenant_id="tenant-a",
            user_id="user-owner",
            role="tenant_owner",
        )
        
        # Pre-seed an agent
        async with session_factory() as session:
            session.add(
                Agent(
                    id="agent-1",
                    tenant_id="tenant-a",
                    name="To Delete",
                )
            )
            await session.commit()
        
        headers = _auth_headers(jwt_token)
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.delete(
                "/api/customer/agents/agent-1",
                headers=headers,
            )
        
        assert response.status_code == 204
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_cross_tenant_agent_access_returns_404(
    tmp_path: Path,
) -> None:
    """Test user cannot access other tenant's agent (returns 404)."""
    app, engine, session_factory = await _open_test_app(
        tmp_path / "agents-cross-tenant.sqlite3"
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
        
        # Tenant A creates agent
        async with session_factory() as session:
            session.add(
                Agent(
                    id="agent-a",
                    tenant_id="tenant-a",
                    name="Tenant A Agent",
                )
            )
            await session.commit()
        
        headers_b = _auth_headers(jwt_token_b)
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # Tenant B tries to access Tenant A's agent
            get_resp = await client.get(
                "/api/customer/agents/agent-a",
                headers=headers_b,
            )
            update_resp = await client.patch(
                "/api/customer/agents/agent-a",
                headers=headers_b,
                json={"name": "Hacked"},
            )
            delete_resp = await client.delete(
                "/api/customer/agents/agent-a",
                headers=headers_b,
            )
        
        assert get_resp.status_code == 404
        assert update_resp.status_code == 404
        assert delete_resp.status_code == 404
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_pending_user_cannot_access_agents(
    tmp_path: Path,
) -> None:
    """Test pending membership status returns 403."""
    app, engine, session_factory = await _open_test_app(
        tmp_path / "agents-pending.sqlite3"
    )
    try:
        jwt_token = await _seed_tenant_with_user(
            session_factory,
            tenant_id="tenant-a",
            user_id="user-pending",
            role="knowledge_editor",
            status="pending",
        )
        
        headers = _auth_headers(jwt_token)
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            list_resp = await client.get(
                "/api/customer/agents",
                headers=headers,
            )
            create_resp = await client.post(
                "/api/customer/agents",
                headers=headers,
                json={"name": "Forbidden Agent"},
            )
        
        assert list_resp.status_code == 403
        assert create_resp.status_code == 403
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_suspended_membership_immediately_blocks_access(
    tmp_path: Path,
) -> None:
    """Test suspended membership immediately blocks access with same JWT."""
    app, engine, session_factory = await _open_test_app(
        tmp_path / "agents-suspended.sqlite3"
    )
    try:
        jwt_token = await _seed_tenant_with_user(
            session_factory,
            tenant_id="tenant-a",
            user_id="user-suspended",
            role="tenant_owner",
        )
        
        headers = _auth_headers(jwt_token)
        
        # First request succeeds
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            before_resp = await client.get(
                "/api/customer/agents",
                headers=headers,
            )
        assert before_resp.status_code == 200
        
        # Suspend membership
        async with session_factory() as session:
            membership = await session.get(
                TenantMembership, ("tenant-a", "user-suspended")
            )
            membership.status = "suspended"
            await session.commit()
        
        # Second request fails with same JWT
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            after_resp = await client.get(
                "/api/customer/agents",
                headers=headers,
            )
        assert after_resp.status_code == 403
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_knowledge_editor_can_manage_agents(
    tmp_path: Path,
) -> None:
    """Test knowledge_editor role can manage agents."""
    app, engine, session_factory = await _open_test_app(
        tmp_path / "agents-editor-manage.sqlite3"
    )
    try:
        jwt_token = await _seed_tenant_with_user(
            session_factory,
            tenant_id="tenant-a",
            user_id="user-editor",
            role="knowledge_editor",
        )
        
        headers = _auth_headers(jwt_token)
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # Create
            create_resp = await client.post(
                "/api/customer/agents",
                headers=headers,
                json={"name": "Editor Agent"},
            )
            agent_id = create_resp.json()["id"]
            
            # Update
            update_resp = await client.patch(
                f"/api/customer/agents/{agent_id}",
                headers=headers,
                json={"name": "Updated by Editor"},
            )
            
            # Delete
            delete_resp = await client.delete(
                f"/api/customer/agents/{agent_id}",
                headers=headers,
            )
        
        assert create_resp.status_code == 201
        assert update_resp.status_code == 200
        assert delete_resp.status_code == 204
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_conversation_viewer_read_only(
    tmp_path: Path,
) -> None:
    """Test conversation_viewer role has read-only access."""
    app, engine, session_factory = await _open_test_app(
        tmp_path / "agents-viewer.sqlite3"
    )
    try:
        # Owner creates agent
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
            session.add(
                Agent(
                    id="agent-1",
                    tenant_id="tenant-a",
                    name="Test Agent",
                )
            )
            await session.commit()
        
        viewer_headers = _auth_headers(jwt_viewer)
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # Can read
            list_resp = await client.get(
                "/api/customer/agents",
                headers=viewer_headers,
            )
            get_resp = await client.get(
                "/api/customer/agents/agent-1",
                headers=viewer_headers,
            )
            
            # Cannot write
            create_resp = await client.post(
                "/api/customer/agents",
                headers=viewer_headers,
                json={"name": "Forbidden"},
            )
            update_resp = await client.patch(
                "/api/customer/agents/agent-1",
                headers=viewer_headers,
                json={"name": "Forbidden Update"},
            )
            delete_resp = await client.delete(
                "/api/customer/agents/agent-1",
                headers=viewer_headers,
            )
        
        assert list_resp.status_code == 200
        assert get_resp.status_code == 200
        assert create_resp.status_code == 403
        assert update_resp.status_code == 403
        assert delete_resp.status_code == 403
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_tenant_id_forced_from_context_not_request_body(
    tmp_path: Path,
) -> None:
    """Test tenant_id is forced from context, ignoring request body."""
    app, engine, session_factory = await _open_test_app(
        tmp_path / "agents-tenant-id-forge.sqlite3"
    )
    try:
        jwt_token = await _seed_tenant_with_user(
            session_factory,
            tenant_id="tenant-a",
            user_id="user-owner",
            role="tenant_owner",
        )
        
        headers = _auth_headers(jwt_token)
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # Try to create agent with forged tenant_id
            response = await client.post(
                "/api/customer/agents",
                headers=headers,
                json={
                    "name": "Agent",
                    "tenant_id": "tenant-other",  # Forged tenant_id
                },
            )
        
        # Should fail with 422 (extra field forbidden)
        assert response.status_code == 422
    finally:
        await engine.dispose()
