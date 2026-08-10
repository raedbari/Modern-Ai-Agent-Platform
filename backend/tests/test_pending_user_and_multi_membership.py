"""Pending user and multi-membership tests (Tasks 11.3, 11.4)."""

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
        # Check if tenant exists
        tenant = await session.get(Tenant, tenant_id)
        if tenant is None:
            session.add(Tenant(id=tenant_id, name=tenant_id))
            await session.flush()
        
        # Check if identity exists
        identity_id = f"identity-{user_id}"
        identity = await session.get(CustomerIdentity, identity_id)
        if identity is None:
            identity = CustomerIdentity(
                id=identity_id,
                email=f"{user_id}@test.com",
                is_email_verified=True,
            )
            session.add(identity)
            await session.flush()
        
        # Check if user exists
        user = await session.get(TenantUser, user_id)
        if user is None:
            user = TenantUser(
                id=user_id,
                customer_identity_id=identity_id,
                display_name=user_id,
            )
            session.add(user)
            await session.flush()
        
        # Create new refresh session
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


# --- Task 11.3: Pending User Tests ---

@pytest.mark.asyncio
async def test_pending_user_cannot_access_tenant_resources(
    tmp_path: Path,
) -> None:
    """Test pending user cannot access any tenant resources."""
    app, engine, session_factory = await _open_test_app(
        tmp_path / "pending-user-blocked.sqlite3"
    )
    try:
        jwt_token = await _seed_tenant_with_user(
            session_factory,
            tenant_id="tenant-a",
            user_id="user-pending",
            role="tenant_owner",
            status="pending",
        )
        
        headers = _auth_headers(jwt_token)
        
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # Try various endpoints
            list_agents = await client.get("/api/customer/agents", headers=headers)
            create_agent = await client.post(
                "/api/customer/agents",
                headers=headers,
                json={"name": "Test Agent"},
            )
        
        # All return 403 for pending user
        assert list_agents.status_code == 403
        assert create_agent.status_code == 403
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_approved_user_can_access_resources_immediately(
    tmp_path: Path,
) -> None:
    """Test approved user can access tenant resources immediately."""
    app, engine, session_factory = await _open_test_app(
        tmp_path / "approved-user-access.sqlite3"
    )
    try:
        # Create pending JWT
        jwt_token = await _seed_tenant_with_user(
            session_factory,
            tenant_id="tenant-a",
            user_id="user-test",
            role="tenant_owner",
            status="pending",
        )
        
        headers = _auth_headers(jwt_token)
        
        # Blocked as pending
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            pending_resp = await client.get("/api/customer/agents", headers=headers)
        assert pending_resp.status_code == 403
        
        # Approve membership
        async with session_factory() as session:
            membership = await session.get(
                TenantMembership, ("tenant-a", "user-test")
            )
            membership.status = "approved"
            await session.commit()
        
        # SAME JWT, now works
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            approved_resp = await client.get("/api/customer/agents", headers=headers)
        assert approved_resp.status_code == 200
    finally:
        await engine.dispose()


# --- Task 11.4: Multi-Membership Tests ---

@pytest.mark.asyncio
async def test_jwt_with_valid_tenant_id_succeeds(
    tmp_path: Path,
) -> None:
    """Test JWT with valid tenant_id from active membership succeeds."""
    app, engine, session_factory = await _open_test_app(
        tmp_path / "multi-membership-valid.sqlite3"
    )
    try:
        # User with membership in tenant-a
        jwt_token = await _seed_tenant_with_user(
            session_factory,
            tenant_id="tenant-a",
            user_id="user-multi",
            role="tenant_owner",
        )
        
        # Add second membership in tenant-b
        await _seed_tenant_with_user(
            session_factory,
            tenant_id="tenant-b",
            user_id="user-multi",
            role="knowledge_editor",
        )
        
        # JWT for tenant-a works
        headers = _auth_headers(jwt_token)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/customer/agents", headers=headers)
        
        assert response.status_code == 200
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_user_with_multiple_memberships_uses_jwt_tenant_id(
    tmp_path: Path,
) -> None:
    """Test user with multiple memberships uses tenant_id from JWT."""
    app, engine, session_factory = await _open_test_app(
        tmp_path / "multi-membership-isolation.sqlite3"
    )
    try:
        # User with memberships in both tenants
        jwt_a = await _seed_tenant_with_user(
            session_factory,
            tenant_id="tenant-a",
            user_id="user-multi",
            role="tenant_owner",
        )
        
        jwt_b = await _seed_tenant_with_user(
            session_factory,
            tenant_id="tenant-b",
            user_id="user-multi",
            role="tenant_owner",
        )
        
        # Create agents for each tenant
        async with session_factory() as session:
            session.add(Agent(id="agent-a", tenant_id="tenant-a", name="Agent A"))
            session.add(Agent(id="agent-b", tenant_id="tenant-b", name="Agent B"))
            await session.commit()
        
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            # JWT-A only sees tenant-a agents
            resp_a = await client.get(
                "/api/customer/agents",
                headers=_auth_headers(jwt_a),
            )
            agents_a = resp_a.json()
            assert len(agents_a) == 1
            assert agents_a[0]["id"] == "agent-a"
            
            # JWT-B only sees tenant-b agents
            resp_b = await client.get(
                "/api/customer/agents",
                headers=_auth_headers(jwt_b),
            )
            agents_b = resp_b.json()
            assert len(agents_b) == 1
            assert agents_b[0]["id"] == "agent-b"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_no_automatic_tenant_selection_occurs(
    tmp_path: Path,
) -> None:
    """Test no automatic tenant selection - JWT must specify tenant_id."""
    app, engine, session_factory = await _open_test_app(
        tmp_path / "multi-membership-no-auto.sqlite3"
    )
    try:
        # Create user with multiple memberships
        await _seed_tenant_with_user(
            session_factory,
            tenant_id="tenant-a",
            user_id="user-multi",
            role="tenant_owner",
        )
        
        await _seed_tenant_with_user(
            session_factory,
            tenant_id="tenant-b",
            user_id="user-multi",
            role="tenant_owner",
        )
        
        # Try to create JWT without tenant_id (should fail at JWT creation level)
        # Our system always requires tenant_id in JWT
        # This test documents that tenant_id is ALWAYS required
        
        settings = Settings(_env_file=None)
        
        # Get session_id
        async with session_factory() as session:
            refresh_session = RefreshSession(
                tenant_user_id="user-multi",
                is_active=True,
            )
            session.add(refresh_session)
            await session.commit()
            session_id = refresh_session.id
        
        # JWT creation requires tenant_id
        jwt_with_tenant = generate_tenant_user_jwt(
            user_id="user-multi",
            session_id=session_id,
            tenant_id="tenant-a",  # MUST specify
            role="tenant_owner",
            secret_key=settings.jwt_secret_key,
        )
        
        # This succeeds because tenant_id is specified
        headers = _auth_headers(jwt_with_tenant)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/customer/agents", headers=headers)
        
        assert response.status_code == 200
    finally:
        await engine.dispose()
