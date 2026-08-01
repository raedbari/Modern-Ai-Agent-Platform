"""Tests for the append-only AuditService."""

from __future__ import annotations

import asyncio

from sqlalchemy import event, func, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)

from backend.app.db.base import Base
from backend.app.db.models import AdminAuditLog
from backend.app.services.audit import AuditService


# ---------------------------------------------------------------------------
# In-process SQLite test database helpers
# ---------------------------------------------------------------------------

async def _open_test_database():
    """Return an in-memory SQLite engine + session factory."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    @event.listens_for(engine.sync_engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    return engine, session_factory


async def _dispose(engine: AsyncEngine) -> None:
    await engine.dispose()


# ---------------------------------------------------------------------------
# test_write_creates_row
# ---------------------------------------------------------------------------

def test_write_creates_row() -> None:
    """AuditService.write() must persist exactly one row."""

    async def scenario() -> None:
        engine, sessions = await _open_test_database()
        try:
            async with sessions() as session:
                row_id = await AuditService.write(
                    session,
                    event_type="login_success",
                    outcome="success",
                    admin_id="admin-001",
                    target_type="session",
                    target_id="session-abc",
                    client_ip="127.0.0.1",
                    detail={"username": "alice"},
                )
                await session.commit()

            # Verify the row is retrievable after commit.
            async with sessions() as session:
                row = await session.get(AdminAuditLog, row_id)

            assert row is not None
            assert row.event_type == "login_success"
            assert row.outcome == "success"
            assert row.admin_id == "admin-001"
            assert row.target_type == "session"
            assert row.target_id == "session-abc"
            assert row.client_ip == "127.0.0.1"
            assert row.detail == {"username": "alice"}
        finally:
            await _dispose(engine)

    asyncio.run(scenario())


# ---------------------------------------------------------------------------
# test_write_with_null_admin_id
# ---------------------------------------------------------------------------

def test_write_with_null_admin_id() -> None:
    """admin_id may be None for pre-authentication events."""

    async def scenario() -> None:
        engine, sessions = await _open_test_database()
        try:
            async with sessions() as session:
                row_id = await AuditService.write(
                    session,
                    event_type="login_failure",
                    outcome="failure",
                    admin_id=None,     # identity unknown at this point
                    client_ip="10.0.0.1",
                )
                await session.commit()

            async with sessions() as session:
                row = await session.get(AdminAuditLog, row_id)

            assert row is not None
            assert row.admin_id is None
            assert row.event_type == "login_failure"
            assert row.outcome == "failure"
        finally:
            await _dispose(engine)

    asyncio.run(scenario())


# ---------------------------------------------------------------------------
# test_audit_row_count_increments
# ---------------------------------------------------------------------------

def test_audit_row_count_increments() -> None:
    """Each call to write() must add exactly one row to the table."""

    async def scenario() -> None:
        engine, sessions = await _open_test_database()
        try:
            events = [
                ("tenant_suspended", "success", "admin-001"),
                ("tenant_deleted",   "success", "admin-001"),
                ("api_key_revoked",  "success", "admin-002"),
            ]

            async with sessions() as session:
                for event_type, outcome, admin_id in events:
                    await AuditService.write(
                        session,
                        event_type=event_type,
                        outcome=outcome,
                        admin_id=admin_id,
                    )
                await session.commit()

            async with sessions() as session:
                count = await session.scalar(
                    select(func.count()).select_from(AdminAuditLog)
                )

            assert count == len(events), (
                f"Expected {len(events)} rows, found {count}"
            )
        finally:
            await _dispose(engine)

    asyncio.run(scenario())


# ---------------------------------------------------------------------------
# test_write_returns_integer_id
# ---------------------------------------------------------------------------

def test_write_returns_integer_id() -> None:
    """write() must return an integer primary key."""

    async def scenario() -> None:
        engine, sessions = await _open_test_database()
        try:
            async with sessions() as session:
                row_id = await AuditService.write(
                    session,
                    event_type="password_changed",
                    outcome="success",
                    admin_id="admin-x",
                )
                await session.commit()

            assert isinstance(row_id, int)
            assert row_id > 0
        finally:
            await _dispose(engine)

    asyncio.run(scenario())


# ---------------------------------------------------------------------------
# test_write_ids_are_monotonically_increasing
# ---------------------------------------------------------------------------

def test_write_ids_are_monotonically_increasing() -> None:
    """Successive writes must produce strictly increasing row ids."""

    async def scenario() -> None:
        engine, sessions = await _open_test_database()
        try:
            ids: list[int] = []
            async with sessions() as session:
                for i in range(5):
                    row_id = await AuditService.write(
                        session,
                        event_type=f"event_{i}",
                        outcome="success",
                    )
                    ids.append(row_id)
                await session.commit()

            assert ids == sorted(ids), "Row ids must be in ascending order"
            assert len(set(ids)) == 5, "All row ids must be distinct"
        finally:
            await _dispose(engine)

    asyncio.run(scenario())


# ---------------------------------------------------------------------------
# test_audit_service_exposes_no_delete_method
# ---------------------------------------------------------------------------

def test_audit_service_exposes_no_delete_method() -> None:
    """AuditService must not expose a delete() or update() method."""
    service_attrs = dir(AuditService)

    assert "delete" not in service_attrs, (
        "AuditService must not expose a delete() method"
    )
    assert "update" not in service_attrs, (
        "AuditService must not expose an update() method"
    )
