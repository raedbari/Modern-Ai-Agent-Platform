"""Tests for the bootstrap_admin CLI command (T-17)."""

from __future__ import annotations

import asyncio

from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.app.db.base import Base
from backend.app.db.models import AdminUser


# ---------------------------------------------------------------------------
# Shared test database helper
# ---------------------------------------------------------------------------

async def _open_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    @event.listens_for(engine.sync_engine, "connect")
    def enable_fk(dbapi_conn, _):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    sessions = async_sessionmaker(engine, expire_on_commit=False)
    return engine, sessions


async def _count_super_admins(sessions) -> int:
    async with sessions() as session:
        from sqlalchemy import func
        return await session.scalar(
            select(func.count()).select_from(AdminUser)
            .where(AdminUser.role == "super_admin")
        ) or 0


# ---------------------------------------------------------------------------
# test_bootstrap_creates_super_admin
# ---------------------------------------------------------------------------

def test_bootstrap_creates_super_admin() -> None:
    from backend.app.cli.bootstrap_admin import _run
    import argparse

    async def scenario() -> None:
        engine, sessions = await _open_db()

        # Patch AsyncSessionLocal to use our in-memory DB.
        import backend.app.db.base as db_base
        original = db_base.AsyncSessionLocal

        class _FakeCtx:
            async def __aenter__(self):
                self._session = sessions()
                return await self._session.__aenter__()
            async def __aexit__(self, *a):
                return await self._session.__aexit__(*a)

        db_base.AsyncSessionLocal = _FakeCtx  # type: ignore[assignment]
        try:
            args = argparse.Namespace(
                username="admin",
                password="SecureAdminPass99!",
                force=False,
            )
            rc = await _run(args)
            assert rc == 0
            count = await _count_super_admins(sessions)
            assert count == 1
        finally:
            db_base.AsyncSessionLocal = original
            await engine.dispose()

    asyncio.run(scenario())


# ---------------------------------------------------------------------------
# test_bootstrap_fails_if_super_admin_exists_without_force
# ---------------------------------------------------------------------------

def test_bootstrap_fails_if_super_admin_exists_without_force() -> None:
    from backend.app.cli.bootstrap_admin import _run
    import argparse
    from backend.app.auth.admin_password import hash_admin_password
    from backend.app.core.config import Settings

    async def scenario() -> None:
        engine, sessions = await _open_db()

        settings = Settings(argon2_time_cost=1, argon2_memory_cost=8192, argon2_parallelism=1, _env_file=None)
        async with sessions() as session:
            session.add(AdminUser(
                id="existing-001",
                username="existing",
                hashed_password=hash_admin_password("ExistingPass99!", settings),
                role="super_admin",
                is_active=True,
            ))
            await session.commit()

        import backend.app.db.base as db_base
        original = db_base.AsyncSessionLocal

        class _FakeCtx:
            async def __aenter__(self):
                self._session = sessions()
                return await self._session.__aenter__()
            async def __aexit__(self, *a):
                return await self._session.__aexit__(*a)

        db_base.AsyncSessionLocal = _FakeCtx  # type: ignore[assignment]
        try:
            args = argparse.Namespace(
                username="admin2",
                password="SecureAdminPass99!",
                force=False,
            )
            rc = await _run(args)
            assert rc == 2
        finally:
            db_base.AsyncSessionLocal = original
            await engine.dispose()

    asyncio.run(scenario())


# ---------------------------------------------------------------------------
# test_bootstrap_succeeds_with_force_flag
# ---------------------------------------------------------------------------

def test_bootstrap_succeeds_with_force_flag() -> None:
    from backend.app.cli.bootstrap_admin import _run
    import argparse
    from backend.app.auth.admin_password import hash_admin_password
    from backend.app.core.config import Settings

    async def scenario() -> None:
        engine, sessions = await _open_db()

        settings = Settings(argon2_time_cost=1, argon2_memory_cost=8192, argon2_parallelism=1, _env_file=None)
        async with sessions() as session:
            session.add(AdminUser(
                id="existing-002",
                username="existing2",
                hashed_password=hash_admin_password("ExistingPass99!", settings),
                role="super_admin",
                is_active=True,
            ))
            await session.commit()

        import backend.app.db.base as db_base
        original = db_base.AsyncSessionLocal

        class _FakeCtx:
            async def __aenter__(self):
                self._session = sessions()
                return await self._session.__aenter__()
            async def __aexit__(self, *a):
                return await self._session.__aexit__(*a)

        db_base.AsyncSessionLocal = _FakeCtx  # type: ignore[assignment]
        try:
            args = argparse.Namespace(
                username="new-admin",
                password="SecureAdminPass99!",
                force=True,
            )
            rc = await _run(args)
            assert rc == 0
        finally:
            db_base.AsyncSessionLocal = original
            await engine.dispose()

    asyncio.run(scenario())


# ---------------------------------------------------------------------------
# test_bootstrap_rejects_weak_password
# ---------------------------------------------------------------------------

def test_bootstrap_rejects_weak_password() -> None:
    from backend.app.cli.bootstrap_admin import _run
    import argparse

    async def scenario() -> None:
        args = argparse.Namespace(
            username="admin",
            password="weak",
            force=False,
        )
        rc = await _run(args)
        assert rc == 2

    asyncio.run(scenario())


# ---------------------------------------------------------------------------
# test_bootstrap_validates_password_strength
# ---------------------------------------------------------------------------

def test_bootstrap_validates_password_strength() -> None:
    """All four strength rules must be individually enforced."""
    from backend.app.operations.admin_auth_ops import (
        WeakPasswordError,
        _validate_password_strength,
    )
    import pytest

    # Too short
    with pytest.raises(WeakPasswordError):
        _validate_password_strength("Short1!")

    # No uppercase
    with pytest.raises(WeakPasswordError):
        _validate_password_strength("alllowercase99!")

    # No digit
    with pytest.raises(WeakPasswordError):
        _validate_password_strength("NoDigitHere!!")

    # No special char
    with pytest.raises(WeakPasswordError):
        _validate_password_strength("NoSpecialChar99")

    # Valid password — should not raise
    _validate_password_strength("ValidPassword99!")
