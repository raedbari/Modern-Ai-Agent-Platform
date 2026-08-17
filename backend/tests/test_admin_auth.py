"""Integration tests for POST /api/admin/auth/login (T-08)."""

from __future__ import annotations

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


# ---------------------------------------------------------------------------
# Test constants
# ---------------------------------------------------------------------------

_JWT_SECRET = "test-jwt-secret-key-that-is-at-least-32-chars-long!!"
_PASSWORD = "AdminPass99!"


# ---------------------------------------------------------------------------
# Test application factory
# ---------------------------------------------------------------------------

async def _open_test_app(
    db_path: Path,
) -> tuple[FastAPI, AsyncEngine, async_sessionmaker]:
    """Create an in-process FastAPI app backed by an SQLite file database."""
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
        jwt_secret_key=_JWT_SECRET,
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


async def _seed_admin(
    sessions: async_sessionmaker,
    *,
    admin_id: str = "admin-001",
    username: str = "alice",
    password: str = _PASSWORD,
    role: str = "super_admin",
    is_active: bool = True,
    settings: Settings | None = None,
) -> AdminUser:
    if settings is None:
        settings = Settings(
            argon2_time_cost=1,
            argon2_memory_cost=8192,
            argon2_parallelism=1,
            _env_file=None,
        )
    hashed = hash_admin_password(password, settings)
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


# ---------------------------------------------------------------------------
# test_login_success_returns_tokens
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_success_returns_tokens(tmp_path: Path) -> None:
    app, engine, sessions = await _open_test_app(tmp_path / "login.sqlite3")
    await _seed_admin(sessions)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.post(
                "/api/admin/auth/login",
                json={"username": "alice", "password": _PASSWORD},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "Bearer"
        assert body["expires_in"] == 15 * 60
        assert body["admin_id"] == "admin-001"
        assert body["role"] == "super_admin"
        assert body["access_token"].startswith("eyJ")
        assert body["refresh_token"].startswith("maap_adm_")
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# test_login_wrong_password_returns_401
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(tmp_path: Path) -> None:
    app, engine, sessions = await _open_test_app(tmp_path / "wrong-pw.sqlite3")
    await _seed_admin(sessions)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.post(
                "/api/admin/auth/login",
                json={"username": "alice", "password": "WrongPassword!"},
            )

        assert resp.status_code == 401
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# test_login_unknown_username_returns_401
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_unknown_username_returns_401(tmp_path: Path) -> None:
    app, engine, sessions = await _open_test_app(tmp_path / "unknown.sqlite3")
    await _seed_admin(sessions)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.post(
                "/api/admin/auth/login",
                json={"username": "nobody", "password": _PASSWORD},
            )

        assert resp.status_code == 401
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# test_login_inactive_account_returns_401
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_inactive_account_returns_401(tmp_path: Path) -> None:
    app, engine, sessions = await _open_test_app(tmp_path / "inactive.sqlite3")
    await _seed_admin(sessions, is_active=False)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.post(
                "/api/admin/auth/login",
                json={"username": "alice", "password": _PASSWORD},
            )

        assert resp.status_code == 401
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# test_login_creates_refresh_session_row
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_creates_refresh_session_row(tmp_path: Path) -> None:
    app, engine, sessions = await _open_test_app(tmp_path / "session.sqlite3")
    await _seed_admin(sessions)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            await client.post(
                "/api/admin/auth/login",
                json={"username": "alice", "password": _PASSWORD},
            )

        async with sessions() as session:
            row = await session.scalar(
                select(AdminRefreshSession).where(
                    AdminRefreshSession.admin_id == "admin-001"
                )
            )

        assert row is not None
        assert row.token_hash is not None
        assert row.family_id is not None
        assert row.expires_at is not None
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# test_login_writes_audit_log
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_writes_audit_log(tmp_path: Path) -> None:
    app, engine, sessions = await _open_test_app(tmp_path / "audit.sqlite3")
    await _seed_admin(sessions)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            await client.post(
                "/api/admin/auth/login",
                json={"username": "alice", "password": _PASSWORD},
            )

        async with sessions() as session:
            row = await session.scalar(
                select(AdminAuditLog).where(
                    AdminAuditLog.event_type == "login_success"
                )
            )

        assert row is not None
        assert row.outcome == "success"
        assert row.admin_id == "admin-001"
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# test_login_error_message_is_generic
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_error_message_is_generic(tmp_path: Path) -> None:
    """Wrong password and unknown username must return identical error bodies."""
    app, engine, sessions = await _open_test_app(tmp_path / "generic.sqlite3")
    await _seed_admin(sessions)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            wrong_pw = await client.post(
                "/api/admin/auth/login",
                json={"username": "alice", "password": "WrongPW!"},
            )
            unknown = await client.post(
                "/api/admin/auth/login",
                json={"username": "nobody", "password": "anything"},
            )

        assert wrong_pw.status_code == 401
        assert unknown.status_code == 401
        # Both responses must carry the same detail to prevent user enumeration.
        assert wrong_pw.json()["detail"] == unknown.json()["detail"]
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# test_login_updates_last_login_at
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_updates_last_login_at(tmp_path: Path) -> None:
    app, engine, sessions = await _open_test_app(tmp_path / "loginat.sqlite3")
    await _seed_admin(sessions)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            await client.post(
                "/api/admin/auth/login",
                json={"username": "alice", "password": _PASSWORD},
            )

        async with sessions() as session:
            admin = await session.get(AdminUser, "admin-001")

        assert admin is not None
        assert admin.last_login_at is not None
    finally:
        await engine.dispose()


# ---------------------------------------------------------------------------
# test_login_failure_writes_audit_log
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_login_failure_writes_audit_log(tmp_path: Path) -> None:
    app, engine, sessions = await _open_test_app(tmp_path / "failaudit.sqlite3")
    await _seed_admin(sessions)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            await client.post(
                "/api/admin/auth/login",
                json={"username": "alice", "password": "BadPass!"},
            )

        async with sessions() as session:
            row = await session.scalar(
                select(AdminAuditLog).where(
                    AdminAuditLog.event_type == "login_failure"
                )
            )

        assert row is not None
        assert row.outcome == "failure"
    finally:
        await engine.dispose()


# ===========================================================================
# T-09: Refresh token rotation and replay detection
# ===========================================================================

async def _login(client: AsyncClient) -> tuple[str, str]:
    """Helper: perform login and return (access_token, refresh_token)."""
    resp = await client.post(
        "/api/admin/auth/login",
        json={"username": "alice", "password": _PASSWORD},
    )
    assert resp.status_code == 200
    body = resp.json()
    return body["access_token"], body["refresh_token"]


@pytest.mark.asyncio
async def test_refresh_returns_new_tokens(tmp_path: Path) -> None:
    """A valid refresh token must yield a new access + refresh token pair."""
    app, engine, sessions = await _open_test_app(tmp_path / "refresh.sqlite3")
    await _seed_admin(sessions)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            _, refresh_token = await _login(client)

            resp = await client.post(
                "/api/admin/auth/refresh",
                json={"refresh_token": refresh_token},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["refresh_token"] != refresh_token   # must be a new token
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_old_token_unusable_after_refresh(tmp_path: Path) -> None:
    """After rotation the presented token must be rejected."""
    app, engine, sessions = await _open_test_app(tmp_path / "old-unusable.sqlite3")
    await _seed_admin(sessions)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            _, refresh_token = await _login(client)

            # Rotate once.
            await client.post(
                "/api/admin/auth/refresh",
                json={"refresh_token": refresh_token},
            )

            # Re-present the old token — must be rejected with replay detection.
            replay = await client.post(
                "/api/admin/auth/refresh",
                json={"refresh_token": refresh_token},
            )

        assert replay.status_code == 401
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_refresh_with_unknown_token_returns_401(tmp_path: Path) -> None:
    """An unknown refresh token must return 401."""
    app, engine, sessions = await _open_test_app(tmp_path / "unknown-rt.sqlite3")
    await _seed_admin(sessions)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.post(
                "/api/admin/auth/refresh",
                json={"refresh_token": "maap_adm_notarealtoken"},
            )

        assert resp.status_code == 401
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_replay_detection_revokes_all_family_sessions(
    tmp_path: Path,
) -> None:
    """Re-presenting a rotated token must revoke the whole session family."""
    app, engine, sessions = await _open_test_app(tmp_path / "replay.sqlite3")
    await _seed_admin(sessions)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            _, token_t1 = await _login(client)

            # Rotate T1 → T2.
            resp2 = await client.post(
                "/api/admin/auth/refresh",
                json={"refresh_token": token_t1},
            )
            token_t2 = resp2.json()["refresh_token"]

            # Replay T1 — must revoke entire family.
            await client.post(
                "/api/admin/auth/refresh",
                json={"refresh_token": token_t1},
            )

            # T2 should also be unusable now.
            resp_t2 = await client.post(
                "/api/admin/auth/refresh",
                json={"refresh_token": token_t2},
            )

        assert resp_t2.status_code == 401

        # Verify all sessions for the admin are revoked in the DB.
        async with sessions() as session:
            active = await session.scalar(
                select(AdminRefreshSession).where(
                    AdminRefreshSession.admin_id == "admin-001",
                    AdminRefreshSession.revoked_at.is_(None),
                )
            )
        assert active is None, "All family sessions must be revoked after replay"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_replay_detection_writes_audit_log(tmp_path: Path) -> None:
    """A replay event must produce a token_replay_detected audit entry."""
    app, engine, sessions = await _open_test_app(tmp_path / "replay-audit.sqlite3")
    await _seed_admin(sessions)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            _, token_t1 = await _login(client)

            # Rotate once.
            await client.post(
                "/api/admin/auth/refresh",
                json={"refresh_token": token_t1},
            )

            # Replay T1.
            await client.post(
                "/api/admin/auth/refresh",
                json={"refresh_token": token_t1},
            )

        async with sessions() as session:
            row = await session.scalar(
                select(AdminAuditLog).where(
                    AdminAuditLog.event_type == "token_replay_detected"
                )
            )

        assert row is not None
        assert row.outcome == "failure"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_refresh_for_inactive_admin_returns_401(tmp_path: Path) -> None:
    """If the admin is deactivated between login and refresh, return 401."""
    app, engine, sessions = await _open_test_app(tmp_path / "inactive-refresh.sqlite3")
    await _seed_admin(sessions)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            _, refresh_token = await _login(client)

        # Deactivate the admin directly in the DB.
        async with sessions() as session:
            admin = await session.get(AdminUser, "admin-001")
            admin.is_active = False
            await session.commit()

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.post(
                "/api/admin/auth/refresh",
                json={"refresh_token": refresh_token},
            )

        assert resp.status_code == 401
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_refresh_writes_token_refreshed_audit_log(tmp_path: Path) -> None:
    """A successful refresh must write a token_refreshed audit entry."""
    app, engine, sessions = await _open_test_app(tmp_path / "refresh-audit.sqlite3")
    await _seed_admin(sessions)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            _, refresh_token = await _login(client)
            await client.post(
                "/api/admin/auth/refresh",
                json={"refresh_token": refresh_token},
            )

        async with sessions() as session:
            row = await session.scalar(
                select(AdminAuditLog).where(
                    AdminAuditLog.event_type == "token_refreshed"
                )
            )

        assert row is not None
        assert row.outcome == "success"
        assert row.admin_id == "admin-001"
    finally:
        await engine.dispose()


# ===========================================================================
# T-10: Logout (session revocation)
# ===========================================================================

@pytest.mark.asyncio
async def test_logout_revokes_session(tmp_path: Path) -> None:
    """After logout the refresh token must be unusable."""
    app, engine, sessions = await _open_test_app(tmp_path / "logout-revoke.sqlite3")
    await _seed_admin(sessions)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            access_token, refresh_token = await _login(client)

            logout_resp = await client.post(
                "/api/admin/auth/logout",
                json={"refresh_token": refresh_token},
                headers={"Authorization": f"Bearer {access_token}"},
            )

            # The revoked token must now be rejected on refresh.
            refresh_resp = await client.post(
                "/api/admin/auth/refresh",
                json={"refresh_token": refresh_token},
            )

        assert logout_resp.status_code == 200
        assert logout_resp.json()["detail"] == "Logged out successfully."
        assert refresh_resp.status_code == 401
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_logout_is_idempotent(tmp_path: Path) -> None:
    """Calling logout twice on the same token must return 200 both times."""
    app, engine, sessions = await _open_test_app(tmp_path / "logout-idem.sqlite3")
    await _seed_admin(sessions)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            access_token, refresh_token = await _login(client)

            first = await client.post(
                "/api/admin/auth/logout",
                json={"refresh_token": refresh_token},
                headers={"Authorization": f"Bearer {access_token}"},
            )
            second = await client.post(
                "/api/admin/auth/logout",
                json={"refresh_token": refresh_token},
                headers={"Authorization": f"Bearer {access_token}"},
            )

        assert first.status_code == 200
        assert second.status_code == 200
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_logout_writes_audit_log(tmp_path: Path) -> None:
    """A successful logout must write a 'logout' audit entry."""
    app, engine, sessions = await _open_test_app(tmp_path / "logout-audit.sqlite3")
    await _seed_admin(sessions)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            access_token, refresh_token = await _login(client)
            await client.post(
                "/api/admin/auth/logout",
                json={"refresh_token": refresh_token},
                headers={"Authorization": f"Bearer {access_token}"},
            )

        async with sessions() as session:
            row = await session.scalar(
                select(AdminAuditLog).where(
                    AdminAuditLog.event_type == "logout"
                )
            )

        assert row is not None
        assert row.outcome == "success"
        assert row.admin_id == "admin-001"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_logout_requires_valid_access_token(tmp_path: Path) -> None:
    """Logout without a valid Bearer token must return 401."""
    app, engine, sessions = await _open_test_app(tmp_path / "logout-noauth.sqlite3")
    await _seed_admin(sessions)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            _, refresh_token = await _login(client)

            # No Authorization header.
            resp = await client.post(
                "/api/admin/auth/logout",
                json={"refresh_token": refresh_token},
            )

        assert resp.status_code == 401
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_logout_with_invalid_bearer_returns_401(tmp_path: Path) -> None:
    """Logout with a malformed Bearer token must return 401."""
    app, engine, sessions = await _open_test_app(tmp_path / "logout-badbearer.sqlite3")
    await _seed_admin(sessions)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            _, refresh_token = await _login(client)

            resp = await client.post(
                "/api/admin/auth/logout",
                json={"refresh_token": refresh_token},
                headers={"Authorization": "Bearer this.is.not.valid"},
            )

        assert resp.status_code == 401
    finally:
        await engine.dispose()


# ===========================================================================
# T-11: GET /me
# ===========================================================================

@pytest.mark.asyncio
async def test_me_returns_admin_profile(tmp_path: Path) -> None:
    """GET /me must return the authenticated admin's profile."""
    app, engine, sessions = await _open_test_app(tmp_path / "me.sqlite3")
    await _seed_admin(sessions)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            access_token, _ = await _login(client)
            resp = await client.get(
                "/api/admin/auth/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["admin_id"] == "admin-001"
        assert body["username"] == "alice"
        assert body["role"] == "super_admin"
        assert body["is_active"] is True
        assert "created_at" in body
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_me_requires_valid_token(tmp_path: Path) -> None:
    """GET /me without a valid token must return 401."""
    app, engine, sessions = await _open_test_app(tmp_path / "me-noauth.sqlite3")
    await _seed_admin(sessions)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            resp = await client.get("/api/admin/auth/me")

        assert resp.status_code == 401
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_me_returns_correct_role(tmp_path: Path) -> None:
    """GET /me must reflect the role stored in the database."""
    app, engine, sessions = await _open_test_app(tmp_path / "me-role.sqlite3")
    await _seed_admin(sessions, role="auditor")
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            access_token, _ = await _login(client)
            resp = await client.get(
                "/api/admin/auth/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )

        assert resp.status_code == 200
        assert resp.json()["role"] == "auditor"
    finally:
        await engine.dispose()


# ===========================================================================
# T-12: POST /change-password
# ===========================================================================

@pytest.mark.asyncio
async def test_change_password_success(tmp_path: Path) -> None:
    """A valid change-password request must return 200."""
    app, engine, sessions = await _open_test_app(tmp_path / "changepw.sqlite3")
    await _seed_admin(sessions)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            access_token, _ = await _login(client)
            resp = await client.post(
                "/api/admin/auth/change-password",
                json={
                    "current_password": _PASSWORD,
                    "new_password": "NewSecurePass99!",
                },
                headers={"Authorization": f"Bearer {access_token}"},
            )

        assert resp.status_code == 200
        assert "revoked" in resp.json()["detail"].lower()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_change_password_wrong_current_returns_401(tmp_path: Path) -> None:
    """Wrong current password must return 401."""
    app, engine, sessions = await _open_test_app(tmp_path / "changepw-wrong.sqlite3")
    await _seed_admin(sessions)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            access_token, _ = await _login(client)
            resp = await client.post(
                "/api/admin/auth/change-password",
                json={
                    "current_password": "WrongPassword!",
                    "new_password": "NewSecurePass99!",
                },
                headers={"Authorization": f"Bearer {access_token}"},
            )

        assert resp.status_code == 401
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_change_password_revokes_all_sessions(tmp_path: Path) -> None:
    """After a password change all refresh sessions must be revoked."""
    app, engine, sessions = await _open_test_app(tmp_path / "changepw-revoke.sqlite3")
    await _seed_admin(sessions)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            access_token, refresh_token = await _login(client)

            await client.post(
                "/api/admin/auth/change-password",
                json={
                    "current_password": _PASSWORD,
                    "new_password": "NewSecurePass99!",
                },
                headers={"Authorization": f"Bearer {access_token}"},
            )

            # The old refresh token must now be unusable.
            refresh_resp = await client.post(
                "/api/admin/auth/refresh",
                json={"refresh_token": refresh_token},
            )

        assert refresh_resp.status_code == 401

        async with sessions() as session:
            active = await session.scalar(
                select(AdminRefreshSession).where(
                    AdminRefreshSession.admin_id == "admin-001",
                    AdminRefreshSession.revoked_at.is_(None),
                )
            )
        assert active is None
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_change_password_weak_new_password_returns_422(
    tmp_path: Path,
) -> None:
    """A password that fails strength requirements must return 422."""
    app, engine, sessions = await _open_test_app(tmp_path / "changepw-weak.sqlite3")
    await _seed_admin(sessions)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            access_token, _ = await _login(client)
            resp = await client.post(
                "/api/admin/auth/change-password",
                json={
                    "current_password": _PASSWORD,
                    "new_password": "short",   # too short, no uppercase, no digit, no special
                },
                headers={"Authorization": f"Bearer {access_token}"},
            )

        assert resp.status_code in (422, 401)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_change_password_writes_audit_log(tmp_path: Path) -> None:
    """A successful password change must write a password_changed audit entry."""
    app, engine, sessions = await _open_test_app(tmp_path / "changepw-audit.sqlite3")
    await _seed_admin(sessions)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            access_token, _ = await _login(client)
            await client.post(
                "/api/admin/auth/change-password",
                json={
                    "current_password": _PASSWORD,
                    "new_password": "NewSecurePass99!",
                },
                headers={"Authorization": f"Bearer {access_token}"},
            )

        async with sessions() as session:
            row = await session.scalar(
                select(AdminAuditLog).where(
                    AdminAuditLog.event_type == "password_changed",
                    AdminAuditLog.outcome == "success",
                )
            )

        assert row is not None
        assert row.admin_id == "admin-001"
    finally:
        await engine.dispose()


# ===========================================================================
# T-18: Auth Integration Test Suite Finalization
# ===========================================================================

@pytest.mark.asyncio
async def test_full_auth_lifecycle(tmp_path: Path) -> None:
    """Full end-to-end auth flow: login -> access /me -> refresh token -> logout -> token invalid."""
    app, engine, sessions = await _open_test_app(tmp_path / "full-auth-lifecycle.sqlite3")
    await _seed_admin(sessions)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # 1. Login
            access_token, refresh_token = await _login(client)
            assert access_token and refresh_token

            # 2. Use access token to fetch profile
            me_resp = await client.get(
                "/api/admin/auth/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert me_resp.status_code == 200
            assert me_resp.json()["admin_id"] == "admin-001"

            # 3. Refresh token pair
            refresh_resp = await client.post(
                "/api/admin/auth/refresh",
                json={"refresh_token": refresh_token},
            )
            assert refresh_resp.status_code == 200
            new_access_token = refresh_resp.json()["access_token"]
            new_refresh_token = refresh_resp.json()["refresh_token"]
            assert new_refresh_token != refresh_token

            # 4. Logout with new refresh token
            logout_resp = await client.post(
                "/api/admin/auth/logout",
                json={"refresh_token": new_refresh_token},
                headers={"Authorization": f"Bearer {new_access_token}"},
            )
            assert logout_resp.status_code == 200

            # 5. Verify refresh with revoked token is rejected
            failed_refresh = await client.post(
                "/api/admin/auth/refresh",
                json={"refresh_token": new_refresh_token},
            )
            assert failed_refresh.status_code == 401
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_password_change_full_flow(tmp_path: Path) -> None:
    """Full password change lifecycle: login -> change password -> old session invalidated -> old pw login fails -> new pw login succeeds."""
    app, engine, sessions = await _open_test_app(tmp_path / "pw-change-flow.sqlite3")
    await _seed_admin(sessions)
    new_pw = "NewSuperSecret99!"
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # 1. Login with initial password
            access_token, refresh_token = await _login(client)

            # 2. Change password
            ch_resp = await client.post(
                "/api/admin/auth/change-password",
                json={
                    "current_password": _PASSWORD,
                    "new_password": new_pw,
                },
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert ch_resp.status_code == 200

            # 3. Old refresh token is revoked
            ref_resp = await client.post(
                "/api/admin/auth/refresh",
                json={"refresh_token": refresh_token},
            )
            assert ref_resp.status_code == 401

            # 4. Login with old password fails
            old_login = await client.post(
                "/api/admin/auth/login",
                json={"username": "alice", "password": _PASSWORD},
            )
            assert old_login.status_code == 401

            # 5. Login with new password succeeds
            new_login = await client.post(
                "/api/admin/auth/login",
                json={"username": "alice", "password": new_pw},
            )
            assert new_login.status_code == 200
            assert "access_token" in new_login.json()
    finally:
        await engine.dispose()
