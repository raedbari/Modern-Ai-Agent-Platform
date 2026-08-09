"""Database authority tests - DB state overrides JWT claims (Task 11.2)."""

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
) -> tuple[str, str]:
    """Seed tenant, user, membership and return (JWT token, session_id)."""
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
    
    return jwt_token, session_id


def _auth_headers(jwt_token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {jwt_token}"}


@pytest.mark.asyncio
async def test_role_change_in_db_immediately_affects_permissions(
    tmp_path: Path,
) -> None:
    """Test role change in DB immediately affects permissions (no JWT refresh)."""
    app, engine, session_factory = await _open_test_app(
        tmp_path / "db-authority-role.sqlite3"
    )
    try:
        # Start as knowledge_editor
        jwt_token, _ = await _seed_tenant_with_user(
            session_factory,
            tenant_id="tenant-a",
            user_id="user-test",
            role="knowledge_editor",
        )
        
        # Seed agent
        async with session_factory() as session:
            session.add(Agent(id="agent-1", tenant_id="tenant-a", name="Agent 1"))
            await session.commit()
        
        headers = _auth_headers(jwt_token)
        
        # Can manage agents as knowledge_editor
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            before_update = await client.patch(
                "/api/customer/agents/agent-1",
                headers=headers,
                json={"name": "Updated 1"},
            )
        assert before_update.status_code == 200
        
        # Change role to conversation_viewer (read-only)
        async with session_factory() as session:
            membership = await session.get(
                TenantMembership, ("tenant-a", "user-test")
            )
            membership.role = "conversation_viewer"
            await session.commit()
        
        # SAME JWT, but now fails (DB role checked)
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            after_update = await client.patch(
                "/api/customer/agents/agent-1",
                headers=headers,
                json={"name": "Updated 2"},
            )
        assert after_update.status_code == 403
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_membership_suspension_immediately_blocks_access(
    tmp_path: Path,
) -> None:
    """Test membership suspension immediately blocks access with valid JWT."""
    app, engine, session_factory = await _open_test_app(
        tmp_path / "db-authority-suspended.sqlite3"
    )
    try:
        jwt_token, _ = await _seed_tenant_with_user(
            session_factory,
            tenant_id="tenant-a",
            user_id="user-test",
            role="tenant_owner",
        )
        
        headers = _auth_headers(jwt_token)
        
        # Works initially
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            before_resp = await client.get(
                "/api/customer/agents",
                headers=headers,
            )
        assert before_resp.status_code == 200
        
        # Suspend membership
        async with session_factory() as session:
            membership = await session.get(
                TenantMembership, ("tenant-a", "user-test")
            )
            membership.status = "suspended"
            await session.commit()
        
        # SAME JWT, now blocked
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            after_resp = await client.get(
                "/api/customer/agents",
                headers=headers,
            )
        assert after_resp.status_code == 403
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_session_revocation_immediately_blocks_access(
    tmp_path: Path,
) -> None:
    """Test session revocation immediately blocks access with valid JWT."""
    app, engine, session_factory = await _open_test_app(
        tmp_path / "db-authority-session.sqlite3"
    )
    try:
        jwt_token, session_id = await _seed_tenant_with_user(
            session_factory,
            tenant_id="tenant-a",
            user_id="user-test",
            role="tenant_owner",
        )
        
        headers = _auth_headers(jwt_token)
        
        # Works initially
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            before_resp = await client.get(
                "/api/customer/agents",
                headers=headers,
            )
        assert before_resp.status_code == 200
        
        # Revoke session
        async with session_factory() as session:
            refresh_session = await session.get(RefreshSession, session_id)
            refresh_session.is_active = False
            await session.commit()
        
        # SAME JWT, now blocked
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            after_resp = await client.get(
                "/api/customer/agents",
                headers=headers,
            )
        assert after_resp.status_code == 401
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_user_deactivation_immediately_blocks_access(
    tmp_path: Path,
) -> None:
    """Test user deactivation immediately blocks access with valid JWT."""
    app, engine, session_factory = await _open_test_app(
        tmp_path / "db-authority-user.sqlite3"
    )
    try:
        jwt_token, _ = await _seed_tenant_with_user(
            session_factory,
            tenant_id="tenant-a",
            user_id="user-test",
            role="tenant_owner",
        )
        
        headers = _auth_headers(jwt_token)
        
        # Works initially
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            before_resp = await client.get(
                "/api/customer/agents",
                headers=headers,
            )
        assert before_resp.status_code == 200
        
        # Deactivate user
        async with session_factory() as session:
            user = await session.get(TenantUser, "user-test")
            user.is_active = False
            await session.commit()
        
        # SAME JWT, now blocked
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            after_resp = await client.get(
                "/api/customer/agents",
                headers=headers,
            )
        assert after_resp.status_code == 401
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_tenant_deactivation_blocks_all_member_access(
    tmp_path: Path,
) -> None:
    """Test tenant deactivation immediately blocks all member access."""
    app, engine, session_factory = await _open_test_app(
        tmp_path / "db-authority-tenant.sqlite3"
    )
    try:
        jwt_token, _ = await _seed_tenant_with_user(
            session_factory,
            tenant_id="tenant-a",
            user_id="user-test",
            role="tenant_owner",
        )
        
        headers = _auth_headers(jwt_token)
        
        # Works initially
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            before_resp = await client.get(
                "/api/customer/agents",
                headers=headers,
            )
        assert before_resp.status_code == 200
        
        # Deactivate tenant
        async with session_factory() as session:
            tenant = await session.get(Tenant, "tenant-a")
            tenant.is_active = False
            await session.commit()
        
        # SAME JWT, now blocked
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            after_resp = await client.get(
                "/api/customer/agents",
                headers=headers,
            )
        assert after_resp.status_code == 403
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_restored_membership_immediately_grants_access(
    tmp_path: Path,
) -> None:
    """Test restored membership immediately grants access with same JWT."""
    app, engine, session_factory = await _open_test_app(
        tmp_path / "db-authority-restore.sqlite3"
    )
    try:
        jwt_token, _ = await _seed_tenant_with_user(
            session_factory,
            tenant_id="tenant-a",
            user_id="user-test",
            role="tenant_owner",
        )
        
        headers = _auth_headers(jwt_token)
        
        # Suspend membership first
        async with session_factory() as session:
            membership = await session.get(
                TenantMembership, ("tenant-a", "user-test")
            )
            membership.status = "suspended"
            await session.commit()
        
        # Blocked
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            suspended_resp = await client.get(
                "/api/customer/agents",
                headers=headers,
            )
        assert suspended_resp.status_code == 403
        
        # Restore membership
        async with session_factory() as session:
            membership = await session.get(
                TenantMembership, ("tenant-a", "user-test")
            )
            membership.status = "approved"
            await session.commit()
        
        # SAME JWT, now works again
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            restored_resp = await client.get(
                "/api/customer/agents",
                headers=headers,
            )
        assert restored_resp.status_code == 200
    finally:
        await engine.dispose()
