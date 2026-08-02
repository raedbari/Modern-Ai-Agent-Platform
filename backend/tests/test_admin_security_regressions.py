"""Regression tests for security issues found during Admin Auth review."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import func, select

from backend.app.core.config import Settings, get_settings
from backend.app.core.rate_limit import RateLimitResult, get_rate_limiter
from backend.app.db.models import AdminAuditLog, AdminRefreshSession, AdminUser
from backend.tests.test_admin_auth import (
    _PASSWORD,
    _login,
    _open_test_app,
    _seed_admin,
)
from backend.tests.test_admin_rbac import (
    _JWT_SECRET_T16,
    _login_as,
    _open_admin_mgmt_app,
    _seed_admin_t16,
)


@pytest.mark.asyncio
async def test_access_token_rejected_after_account_deactivation(
    tmp_path: Path,
) -> None:
    app, engine, sessions = await _open_admin_mgmt_app(
        tmp_path / "disabled-access.sqlite3"
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
            bob_token = await _login_as(client, username="bob")
            alice_token = await _login_as(client, username="alice")

            disabled = await client.patch(
                "/api/admin/admins/op-001/status",
                json={"is_active": False},
                headers={"Authorization": f"Bearer {alice_token}"},
            )
            after_disable = await client.get(
                "/api/admin/tenants",
                headers={"Authorization": f"Bearer {bob_token}"},
            )

        assert disabled.status_code == 200
        assert after_disable.status_code == 401
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_access_token_rejected_after_password_change(
    tmp_path: Path,
) -> None:
    app, engine, sessions = await _open_test_app(
        tmp_path / "password-access.sqlite3"
    )
    await _seed_admin(sessions)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            access_token, _ = await _login(client)
            changed = await client.post(
                "/api/admin/auth/change-password",
                json={
                    "current_password": _PASSWORD,
                    "new_password": "ChangedAdminPass99!",
                },
                headers={"Authorization": f"Bearer {access_token}"},
            )
            after_change = await client.get(
                "/api/admin/tenants",
                headers={"Authorization": f"Bearer {access_token}"},
            )

        assert changed.status_code == 200
        assert after_change.status_code == 401
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_legacy_key_can_create_admin_without_invalid_foreign_key(
    tmp_path: Path,
) -> None:
    app, engine, sessions = await _open_admin_mgmt_app(
        tmp_path / "legacy-create.sqlite3"
    )
    legacy_settings = Settings(
        admin_api_key="legacy-test-key",
        admin_legacy_key_enabled=True,
        jwt_secret_key=_JWT_SECRET_T16,
        argon2_time_cost=1,
        argon2_memory_cost=8192,
        argon2_parallelism=1,
        _env_file=None,
    )
    app.dependency_overrides[get_settings] = lambda: legacy_settings

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/admin/admins",
                json={
                    "username": "legacy-created",
                    "password": "SecureLegacyPass99!",
                    "role": "operator",
                },
                headers={"X-Admin-Key": "legacy-test-key"},
            )

        assert response.status_code == 201
        async with sessions() as session:
            created = await session.scalar(
                select(AdminUser).where(
                    AdminUser.username == "legacy-created"
                )
            )
        assert created is not None
        assert created.created_by is None
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_invalid_admin_role_returns_422(tmp_path: Path) -> None:
    app, engine, sessions = await _open_admin_mgmt_app(
        tmp_path / "invalid-role.sqlite3"
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
            access_token = await _login_as(client, username="alice")
            response = await client.post(
                "/api/admin/admins",
                json={
                    "username": "invalid-role-user",
                    "password": "SecureInvalidPass99!",
                    "role": "owner",
                },
                headers={"Authorization": f"Bearer {access_token}"},
            )

        assert response.status_code == 422
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_wrong_password_change_audit_persists(tmp_path: Path) -> None:
    app, engine, sessions = await _open_test_app(
        tmp_path / "wrong-change-audit.sqlite3"
    )
    await _seed_admin(sessions)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            access_token, _ = await _login(client)
            response = await client.post(
                "/api/admin/auth/change-password",
                json={
                    "current_password": "DefinitelyWrong99!",
                    "new_password": "ChangedAdminPass99!",
                },
                headers={"Authorization": f"Bearer {access_token}"},
            )

        assert response.status_code == 401
        async with sessions() as session:
            row = await session.scalar(
                select(AdminAuditLog)
                .where(
                    AdminAuditLog.event_type == "password_changed",
                    AdminAuditLog.outcome == "failure",
                )
                .order_by(AdminAuditLog.id.desc())
            )
        assert row is not None
        assert row.detail == {"reason": "wrong_current_password"}
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_untrusted_forwarded_for_is_not_used_for_audit(
    tmp_path: Path,
) -> None:
    app, engine, sessions = await _open_test_app(
        tmp_path / "untrusted-forwarded.sqlite3"
    )
    await _seed_admin(sessions)

    spoofed_ip = "198.51.100.23"
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/admin/auth/login",
                json={"username": "alice", "password": "wrong"},
                headers={"X-Forwarded-For": spoofed_ip},
            )

        assert response.status_code == 401
        async with sessions() as session:
            row = await session.scalar(
                select(AdminAuditLog)
                .where(AdminAuditLog.event_type == "login_failure")
                .order_by(AdminAuditLog.id.desc())
            )
        assert row is not None
        assert row.client_ip != spoofed_ip
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_admin_login_rate_limit_returns_429_and_creates_no_session(
    tmp_path: Path,
) -> None:
    app, engine, sessions = await _open_test_app(
        tmp_path / "login-rate-limit.sqlite3"
    )
    await _seed_admin(sessions)

    class DenyingLimiter:
        async def check(self, **kwargs) -> RateLimitResult:
            if kwargs["bucket"] == "admin-login-account":
                return RateLimitResult(False, 0, 37)
            return RateLimitResult(True, 10, 37)

    app.dependency_overrides[get_rate_limiter] = lambda: DenyingLimiter()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/admin/auth/login",
                json={"username": "alice", "password": _PASSWORD},
            )

        assert response.status_code == 429
        assert response.headers["Retry-After"] == "37"
        async with sessions() as session:
            session_count = await session.scalar(
                select(func.count()).select_from(AdminRefreshSession)
            )
            audit = await session.scalar(
                select(AdminAuditLog).where(
                    AdminAuditLog.event_type == "login_rate_limited"
                )
            )
        assert session_count == 0
        assert audit is not None
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_auditor_can_read_audit_log_but_operator_cannot(
    tmp_path: Path,
) -> None:
    app, engine, sessions = await _open_admin_mgmt_app(
        tmp_path / "audit-read-rbac.sqlite3"
    )
    await _seed_admin_t16(
        sessions,
        admin_id="auditor-001",
        username="auditor-user",
        role="auditor",
    )
    await _seed_admin_t16(
        sessions,
        admin_id="operator-001",
        username="operator-user",
        role="operator",
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            auditor_token = await _login_as(
                client,
                username="auditor-user",
            )
            operator_token = await _login_as(
                client,
                username="operator-user",
            )
            auditor_response = await client.get(
                "/api/admin/audit",
                headers={"Authorization": f"Bearer {auditor_token}"},
            )
            operator_response = await client.get(
                "/api/admin/audit",
                headers={"Authorization": f"Bearer {operator_token}"},
            )

        assert auditor_response.status_code == 200
        assert auditor_response.json()
        assert operator_response.status_code == 403
    finally:
        await engine.dispose()
