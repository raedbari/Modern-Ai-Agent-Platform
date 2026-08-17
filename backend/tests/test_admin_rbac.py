"""Tests for the RBAC permission system (T-13)."""

from __future__ import annotations

import pytest

from backend.app.api.dependencies import ROLE_PERMISSIONS, require_permission
from backend.app.auth.admin_context import AdminContext


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ctx(role: str) -> AdminContext:
    return AdminContext(admin_id="x", username="u", role=role)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Role coverage
# ---------------------------------------------------------------------------

def test_super_admin_has_all_permissions() -> None:
    perms = ROLE_PERMISSIONS["super_admin"]
    for permission in (
        "tenants:read", "tenants:write", "tenants:delete",
        "agents:read", "agents:write", "agents:delete",
        "api_keys:read", "api_keys:revoke",
        "conversations:delete",
        "admins:read", "admins:write", "admins:delete",
        "audit:read",
    ):
        assert permission in perms, f"super_admin missing: {permission}"


def test_operator_lacks_tenants_delete() -> None:
    assert "tenants:delete" not in ROLE_PERMISSIONS["operator"]


def test_operator_lacks_agents_delete() -> None:
    assert "agents:delete" not in ROLE_PERMISSIONS["operator"]


def test_operator_lacks_admins_permissions() -> None:
    op = ROLE_PERMISSIONS["operator"]
    assert "admins:read" not in op
    assert "admins:write" not in op
    assert "admins:delete" not in op


def test_auditor_lacks_all_write_permissions() -> None:
    aud = ROLE_PERMISSIONS["auditor"]
    for write_perm in (
        "tenants:write", "tenants:delete",
        "agents:write", "agents:delete",
        "api_keys:revoke",
        "conversations:delete",
        "admins:read", "admins:write", "admins:delete",
    ):
        assert write_perm not in aud, f"auditor should not have: {write_perm}"


def test_auditor_has_read_permissions() -> None:
    aud = ROLE_PERMISSIONS["auditor"]
    assert "tenants:read" in aud
    assert "agents:read" in aud
    assert "api_keys:read" in aud
    assert "audit:read" in aud


def test_operator_has_read_and_write_permissions() -> None:
    op = ROLE_PERMISSIONS["operator"]
    assert "tenants:read" in op
    assert "tenants:write" in op
    assert "agents:write" in op
    assert "api_keys:revoke" in op
    assert "conversations:delete" in op


# ---------------------------------------------------------------------------
# require_permission dependency
# ---------------------------------------------------------------------------

def test_require_permission_passes_for_sufficient_role() -> None:
    """super_admin must pass all permission checks."""
    from fastapi import HTTPException
    dependency = require_permission("tenants:delete")
    # Should not raise
    dependency(_ctx("super_admin"))


def test_require_permission_raises_403_on_insufficient_role() -> None:
    """auditor must be rejected for write permissions."""
    from fastapi import HTTPException
    dependency = require_permission("tenants:write")
    with pytest.raises(HTTPException) as exc_info:
        dependency(_ctx("auditor"))
    assert exc_info.value.status_code == 403


def test_require_permission_operator_allowed() -> None:
    dependency = require_permission("tenants:write")
    dependency(_ctx("operator"))  # should not raise


def test_require_permission_operator_blocked_on_delete() -> None:
    from fastapi import HTTPException
    dependency = require_permission("tenants:delete")
    with pytest.raises(HTTPException) as exc_info:
        dependency(_ctx("operator"))
    assert exc_info.value.status_code == 403


def test_require_permission_none_ctx_is_allowed() -> None:
    """When ctx is None (dependency override in tests) the check is skipped."""
    dependency = require_permission("admins:delete")
    dependency(None)  # must not raise


# ===========================================================================
# T-16: Admin user management endpoint integration tests
# ===========================================================================

from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)

from backend.app.auth.admin_password import hash_admin_password
from backend.app.core.config import Settings, get_settings
from backend.app.db.base import Base, get_db
from backend.app.db.models import AdminAuditLog, AdminRefreshSession, AdminUser
from backend.app.main import create_app

_JWT_SECRET_T16 = "t16-jwt-secret-key-that-is-at-least-32-chars-long!!"
_PASSWORD_T16 = "AdminPass99!"


async def _open_admin_mgmt_app(
    db_path: Path,
) -> tuple[FastAPI, AsyncEngine, async_sessionmaker]:
    """Create a test FastAPI app with a real JWT-authenticated admin session."""
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path.as_posix()}"
    )

    @event.listens_for(engine.sync_engine, "connect")
    def enable_fk(dbapi_conn, _rec):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    sessions = async_sessionmaker(engine, expire_on_commit=False)
    app = create_app()

    async def _override_db():
        async with sessions() as session:
            yield session

    test_settings = Settings(
        jwt_secret_key=_JWT_SECRET_T16,
        jwt_access_token_expire_minutes=15,
        jwt_refresh_token_expire_days=7,
        argon2_time_cost=1,
        argon2_memory_cost=8192,
        argon2_parallelism=1,
        _env_file=None,
        redis_url=None,
    )

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_settings] = lambda: test_settings
    return app, engine, sessions


async def _seed_admin_t16(
    sessions: async_sessionmaker,
    *,
    admin_id: str,
    username: str,
    role: str = "super_admin",
    is_active: bool = True,
) -> AdminUser:
    settings = Settings(
        argon2_time_cost=1,
        argon2_memory_cost=8192,
        argon2_parallelism=1,
        _env_file=None,
    )
    hashed = hash_admin_password(_PASSWORD_T16, settings)
    async with sessions() as session:
        admin = AdminUser(
            id=admin_id,
            username=username,
            hashed_password=hashed,
            role=role,
            is_active=is_active,
        )
        session.add(admin)
        await session.commit()
    return admin


async def _login_as(
    client: AsyncClient,
    *,
    username: str,
    password: str = _PASSWORD_T16,
) -> str:
    """Log in and return the Bearer access token."""
    resp = await client.post(
        "/api/admin/auth/login",
        json={"username": username, "password": password},
    )
    assert resp.status_code == 200, f"Login failed: {resp.json()}"
    return resp.json()["access_token"]


# ---------------------------------------------------------------------------
# test_super_admin_can_create_admin
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_super_admin_can_create_admin(tmp_path: Path) -> None:
    """A super_admin can create a new admin account via POST /api/admin/admins."""
    app, engine, sessions = await _open_admin_mgmt_app(
        tmp_path / "create-admin.sqlite3"
    )
    await _seed_admin_t16(
        sessions,
        admin_id="super-001",
        username="alice",
        role="super_admin",
    )
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            token = await _login_as(client, username="alice")
            resp = await client.post(
                "/api/admin/admins",
                json={
                    "username": "newoperator",
                    "password": "Secure@Pass99!",
                    "role": "operator",
                },
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 201
        body = resp.json()
        assert body["username"] == "newoperator"
        assert body["role"] == "operator"
        assert body["is_active"] is True
        assert "hashed_password" not in body
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# test_operator_cannot_create_admin_returns_403
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_operator_cannot_create_admin_returns_403(tmp_path: Path) -> None:
    """An operator role must receive 403 when attempting to create an admin."""
    app, engine, sessions = await _open_admin_mgmt_app(
        tmp_path / "operator-create-403.sqlite3"
    )
    await _seed_admin_t16(
        sessions,
        admin_id="op-001",
        username="bob",
        role="operator",
    )
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            token = await _login_as(client, username="bob")
            resp = await client.post(
                "/api/admin/admins",
                json={
                    "username": "newadmin",
                    "password": "Secure@Pass99!",
                    "role": "operator",
                },
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 403
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# test_duplicate_username_returns_409
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_duplicate_username_returns_409(tmp_path: Path) -> None:
    """Creating an admin with an existing username must return HTTP 409."""
    app, engine, sessions = await _open_admin_mgmt_app(
        tmp_path / "duplicate-409.sqlite3"
    )
    await _seed_admin_t16(
        sessions,
        admin_id="super-001",
        username="alice",
        role="super_admin",
    )
    # Seed a second admin with the username we'll try to duplicate.
    await _seed_admin_t16(
        sessions,
        admin_id="existing-001",
        username="existinguser",
        role="operator",
    )
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            token = await _login_as(client, username="alice")
            resp = await client.post(
                "/api/admin/admins",
                json={
                    "username": "existinguser",
                    "password": "Secure@Pass99!",
                    "role": "operator",
                },
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 409
        assert "existinguser" in resp.json()["detail"]
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# test_deactivate_admin_revokes_their_sessions
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_deactivate_admin_revokes_their_sessions(tmp_path: Path) -> None:
    """Deactivating an admin must revoke all their active refresh sessions."""
    app, engine, sessions = await _open_admin_mgmt_app(
        tmp_path / "deactivate-revoke.sqlite3"
    )
    await _seed_admin_t16(
        sessions,
        admin_id="super-001",
        username="alice",
        role="super_admin",
    )
    await _seed_admin_t16(
        sessions,
        admin_id="op-001",
        username="bob",
        role="operator",
    )
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # Bob logs in to create an active session.
            await _login_as(client, username="bob")

            # Alice (super_admin) deactivates Bob.
            alice_token = await _login_as(client, username="alice")
            resp = await client.patch(
                "/api/admin/admins/op-001/status",
                json={"is_active": False},
                headers={"Authorization": f"Bearer {alice_token}"},
            )

        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

        # All of Bob's refresh sessions must now be revoked.
        async with sessions() as session:
            active = await session.scalar(
                select(AdminRefreshSession).where(
                    AdminRefreshSession.admin_id == "op-001",
                    AdminRefreshSession.revoked_at.is_(None),
                )
            )
        assert active is None, "All sessions must be revoked on deactivation"
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# test_cannot_deactivate_own_account_returns_422
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cannot_deactivate_own_account_returns_422(tmp_path: Path) -> None:
    """An admin must receive HTTP 422 when trying to deactivate their own account."""
    app, engine, sessions = await _open_admin_mgmt_app(
        tmp_path / "self-deactivate-422.sqlite3"
    )
    await _seed_admin_t16(
        sessions,
        admin_id="super-001",
        username="alice",
        role="super_admin",
    )
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            token = await _login_as(client, username="alice")
            resp = await client.patch(
                "/api/admin/admins/super-001/status",
                json={"is_active": False},
                headers={"Authorization": f"Bearer {token}"},
            )

        assert resp.status_code == 422
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# test_force_revoke_sessions_returns_count
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_force_revoke_sessions_returns_count(tmp_path: Path) -> None:
    """DELETE /api/admin/admins/{id}/sessions must return the revoked session count."""
    app, engine, sessions = await _open_admin_mgmt_app(
        tmp_path / "force-revoke-count.sqlite3"
    )
    await _seed_admin_t16(
        sessions,
        admin_id="super-001",
        username="alice",
        role="super_admin",
    )
    await _seed_admin_t16(
        sessions,
        admin_id="op-001",
        username="bob",
        role="operator",
    )
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # Bob logs in twice to create two sessions.
            await _login_as(client, username="bob")
            await _login_as(client, username="bob")

            alice_token = await _login_as(client, username="alice")
            resp = await client.delete(
                "/api/admin/admins/op-001/sessions",
                headers={"Authorization": f"Bearer {alice_token}"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert "revoked_count" in body
        assert body["revoked_count"] == 2
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# test_admin_creation_writes_audit_log
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_admin_creation_writes_audit_log(tmp_path: Path) -> None:
    """Creating a new admin must write an 'admin_created' audit log entry."""
    app, engine, sessions = await _open_admin_mgmt_app(
        tmp_path / "create-audit.sqlite3"
    )
    await _seed_admin_t16(
        sessions,
        admin_id="super-001",
        username="alice",
        role="super_admin",
    )
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            token = await _login_as(client, username="alice")
            await client.post(
                "/api/admin/admins",
                json={
                    "username": "newoperator",
                    "password": "Secure@Pass99!",
                    "role": "operator",
                },
                headers={"Authorization": f"Bearer {token}"},
            )

        async with sessions() as session:
            row = await session.scalar(
                select(AdminAuditLog).where(
                    AdminAuditLog.event_type == "admin_created"
                )
            )

        assert row is not None
        assert row.outcome == "success"
        assert row.target_type == "admin"
        assert row.admin_id == "super-001"
    finally:
        await engine.dispose()


# ===========================================================================
# T-19: RBAC Integration Test Suite Finalization (Matrix Coverage)
# ===========================================================================

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role,method,path,payload,expected_status",
    [
        # tenants:read
        ("super_admin", "GET", "/api/admin/tenants", None, 200),
        ("operator", "GET", "/api/admin/tenants", None, 200),
        ("auditor", "GET", "/api/admin/tenants", None, 200),
        # tenants:write
        ("super_admin", "PATCH", "/api/admin/tenants/nonexistent/status", {"is_active": False}, 404),
        ("operator", "PATCH", "/api/admin/tenants/nonexistent/status", {"is_active": False}, 404),
        ("auditor", "PATCH", "/api/admin/tenants/nonexistent/status", {"is_active": False}, 403),
        # tenants:delete
        ("super_admin", "DELETE", "/api/admin/tenants/nonexistent?confirm=nonexistent", None, 404),
        ("operator", "DELETE", "/api/admin/tenants/nonexistent?confirm=nonexistent", None, 403),
        ("auditor", "DELETE", "/api/admin/tenants/nonexistent?confirm=nonexistent", None, 403),
        # admins:read
        ("super_admin", "GET", "/api/admin/admins", None, 200),
        ("operator", "GET", "/api/admin/admins", None, 403),
        ("auditor", "GET", "/api/admin/admins", None, 403),
        # admins:write
        ("super_admin", "POST", "/api/admin/admins", {"username": "new_matrix_user", "password": "Secure@Password99!", "role": "operator"}, 201),
        ("operator", "POST", "/api/admin/admins", {"username": "new_matrix_user2", "password": "Secure@Password99!", "role": "operator"}, 403),
        ("auditor", "POST", "/api/admin/admins", {"username": "new_matrix_user3", "password": "Secure@Password99!", "role": "operator"}, 403),
        # admins:delete
        ("super_admin", "DELETE", "/api/admin/admins/nobody/sessions", None, 404),
        ("operator", "DELETE", "/api/admin/admins/nobody/sessions", None, 403),
        ("auditor", "DELETE", "/api/admin/admins/nobody/sessions", None, 403),
        # api_keys:revoke
        ("super_admin", "POST", "/api/admin/tenants/t1/api-keys/k1/revoke", None, 404),
        ("operator", "POST", "/api/admin/tenants/t1/api-keys/k1/revoke", None, 404),
        ("auditor", "POST", "/api/admin/tenants/t1/api-keys/k1/revoke", None, 403),
        # conversations:delete
        ("super_admin", "DELETE", "/api/admin/tenants/t1/conversations/c1", None, 404),
        ("operator", "DELETE", "/api/admin/tenants/t1/conversations/c1", None, 404),
        ("auditor", "DELETE", "/api/admin/tenants/t1/conversations/c1", None, 403),
    ],
)
async def test_rbac_matrix_parameterized(
    tmp_path: Path,
    role: str,
    method: str,
    path: str,
    payload: dict | None,
    expected_status: int,
) -> None:
    """Parameterized test verifying all role x endpoint combinations in the RBAC matrix."""
    app, engine, sessions = await _open_admin_mgmt_app(
        tmp_path / f"rbac-matrix-{role}-{method}-{expected_status}.sqlite3"
    )
    username = f"user_{role}"
    await _seed_admin_t16(
        sessions,
        admin_id=f"id_{role}",
        username=username,
        role=role,
    )
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            token = await _login_as(client, username=username)
            headers = {"Authorization": f"Bearer {token}"}

            if method == "GET":
                resp = await client.get(path, headers=headers)
            elif method == "POST":
                resp = await client.post(path, json=payload, headers=headers)
            elif method == "PATCH":
                resp = await client.patch(path, json=payload, headers=headers)
            elif method == "DELETE":
                resp = await client.delete(path, headers=headers)
            else:
                pytest.fail(f"Unsupported HTTP method: {method}")

        assert resp.status_code == expected_status, (
            f"Role '{role}' on {method} {path} expected HTTP {expected_status}, "
            f"got HTTP {resp.status_code}: {resp.json()}"
        )
    finally:
        await engine.dispose()
