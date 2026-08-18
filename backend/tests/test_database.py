"""Database schema and tenant-isolation tests."""

import asyncio

import pytest
from sqlalchemy import event, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)

from backend.app.db.base import Base
from backend.app.db.models import (
    AdminAuditLog,
    AdminUser,
    AdminRefreshSession,
    Agent,
    AgentWidgetSettings,
    Conversation,
    Message,
    Tenant,
    WidgetAllowedOrigin,
)


async def _open_test_database():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
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
    return engine, session_factory


async def _dispose(engine: AsyncEngine) -> None:
    await engine.dispose()


def test_metadata_defines_expected_tables() -> None:
    assert set(Base.metadata.tables) == {
        # Existing tenant tables
        "tenants",
        "api_keys",
        "agents",
        "conversations",
        "messages",
        "ingestion_jobs",
        "knowledge_bases",
        "agent_knowledge_bases",
        "documents",
        "chunks",
        # Admin auth tables added in Wave 1
        "admin_users",
        "admin_refresh_sessions",
        "admin_audit_log",
        "evaluation_runs",
        # Browser Widget configuration tables added in Wave 2
        "agent_widget_settings",
        "widget_allowed_origins",
        "widget_connector_pairings",

        # Customer SaaS identity / onboarding tables
        "users",
        "user_refresh_sessions",
        "email_verification_tokens",
        "tenant_applications",
        "legal_acceptances",
        "tenant_memberships",
    }


def test_widget_settings_reject_agent_from_another_tenant() -> None:
    async def scenario() -> None:
        engine, session_factory = await _open_test_database()
        try:
            async with session_factory() as session:
                session.add_all(
                    [
                        Tenant(id="tenant-a", name="Tenant A"),
                        Tenant(id="tenant-b", name="Tenant B"),
                        Agent(
                            id="agent-a",
                            tenant_id="tenant-a",
                            name="Agent A",
                        ),
                    ]
                )
                await session.commit()

            async with session_factory() as session:
                session.add(
                    AgentWidgetSettings(
                        tenant_id="tenant-b",
                        agent_id="agent-a",
                        public_widget_id="wgt_cross_tenant_widget_identifier",
                    )
                )
                with pytest.raises(IntegrityError):
                    await session.flush()
                await session.rollback()
        finally:
            await _dispose(engine)

    asyncio.run(scenario())


def test_widget_origin_requires_matching_widget_tenant_and_agent() -> None:
    async def scenario() -> None:
        engine, session_factory = await _open_test_database()
        try:
            async with session_factory() as session:
                session.add_all(
                    [
                        Tenant(id="tenant-a", name="Tenant A"),
                        Tenant(id="tenant-b", name="Tenant B"),
                        Agent(
                            id="agent-a",
                            tenant_id="tenant-a",
                            name="Agent A",
                        ),
                        Agent(
                            id="agent-b",
                            tenant_id="tenant-b",
                            name="Agent B",
                        ),
                    ]
                )
                await session.commit()
                session.add(
                    AgentWidgetSettings(
                        tenant_id="tenant-a",
                        agent_id="agent-a",
                        public_widget_id="wgt_valid_widget_identifier_1234",
                    )
                )
                await session.commit()

            async with session_factory() as session:
                session.add(
                    WidgetAllowedOrigin(
                        tenant_id="tenant-b",
                        agent_id="agent-a",
                        origin="https://example.com",
                    )
                )
                with pytest.raises(IntegrityError):
                    await session.flush()
                await session.rollback()
        finally:
            await _dispose(engine)

    asyncio.run(scenario())


def test_valid_tenant_hierarchy_can_be_persisted() -> None:
    async def scenario() -> None:
        engine, session_factory = await _open_test_database()

        try:
            async with session_factory() as session:
                session.add_all(
                    [
                        Tenant(id="tenant-a", name="Tenant A"),
                        Agent(
                            id="agent-a",
                            tenant_id="tenant-a",
                            name="Agent A",
                        ),
                        Conversation(
                            id="conversation-a",
                            tenant_id="tenant-a",
                            agent_id="agent-a",
                        ),
                        Message(
                            id="message-a",
                            tenant_id="tenant-a",
                            conversation_id="conversation-a",
                            role="user",
                            content="Hello",
                        ),
                    ]
                )
                await session.commit()

            async with session_factory() as session:
                stored = await session.scalar(
                    select(Message).where(Message.id == "message-a")
                )

                assert stored is not None
                assert stored.tenant_id == "tenant-a"
                assert stored.conversation_id == "conversation-a"
        finally:
            await _dispose(engine)

    asyncio.run(scenario())


def test_conversation_rejects_agent_from_another_tenant() -> None:
    async def scenario() -> None:
        engine, session_factory = await _open_test_database()

        try:
            async with session_factory() as session:
                session.add_all(
                    [
                        Tenant(id="tenant-a", name="Tenant A"),
                        Tenant(id="tenant-b", name="Tenant B"),
                        Agent(
                            id="agent-a",
                            tenant_id="tenant-a",
                            name="Agent A",
                        ),
                    ]
                )
                await session.commit()

            async with session_factory() as session:
                session.add(
                    Conversation(
                        id="cross-tenant-conversation",
                        tenant_id="tenant-b",
                        agent_id="agent-a",
                    )
                )

                with pytest.raises(IntegrityError):
                    await session.flush()

                await session.rollback()
        finally:
            await _dispose(engine)

    asyncio.run(scenario())


def test_message_rejects_conversation_from_another_tenant() -> None:
    async def scenario() -> None:
        engine, session_factory = await _open_test_database()

        try:
            async with session_factory() as session:
                session.add_all(
                    [
                        Tenant(id="tenant-a", name="Tenant A"),
                        Tenant(id="tenant-b", name="Tenant B"),
                        Agent(
                            id="agent-a",
                            tenant_id="tenant-a",
                            name="Agent A",
                        ),
                        Conversation(
                            id="conversation-a",
                            tenant_id="tenant-a",
                            agent_id="agent-a",
                        ),
                    ]
                )
                await session.commit()

            async with session_factory() as session:
                session.add(
                    Message(
                        id="cross-tenant-message",
                        tenant_id="tenant-b",
                        conversation_id="conversation-a",
                        role="user",
                        content="Invalid tenant relationship",
                    )
                )

                with pytest.raises(IntegrityError):
                    await session.flush()

                await session.rollback()
        finally:
            await _dispose(engine)

    asyncio.run(scenario())


# ---------------------------------------------------------------------------
# Admin auth model tests (T-04)
# ---------------------------------------------------------------------------

def test_admin_audit_log_has_no_delete_or_update_helper() -> None:
    """AdminAuditLog must not expose an ORM-level delete or update method.

    Rows are append-only by design.  The test verifies that no helper
    on the model class would allow callers to bypass this contract.
    """
    model_attrs = dir(AdminAuditLog)

    assert "delete" not in model_attrs, (
        "AdminAuditLog must not expose a delete() helper"
    )
    assert "update" not in model_attrs, (
        "AdminAuditLog must not expose an update() helper"
    )


def test_admin_user_role_check_constraint_values() -> None:
    """AdminUser.role must only accept the three defined role strings."""
    import asyncio
    from sqlalchemy.exc import IntegrityError

    async def scenario() -> None:
        engine, session_factory = await _open_test_database()
        try:
            async with session_factory() as session:
                session.add(
                    AdminUser(
                        id="admin-bad-role",
                        username="bad-role-user",
                        hashed_password="$argon2id$fake",
                        role="god_mode",  # invalid value
                    )
                )
                with pytest.raises((IntegrityError, Exception)):
                    await session.flush()
                await session.rollback()
        finally:
            await _dispose(engine)

    asyncio.run(scenario())


def test_admin_refresh_session_cascades_on_admin_delete() -> None:
    """Deleting an AdminUser must cascade-delete its refresh sessions."""
    import asyncio
    from sqlalchemy import func, select

    async def scenario() -> None:
        engine, session_factory = await _open_test_database()
        try:
            async with session_factory() as session:
                from datetime import datetime, timedelta, timezone
                now = datetime.now(timezone.utc)

                session.add(
                    AdminUser(
                        id="admin-cascade",
                        username="cascade-user",
                        hashed_password="$argon2id$fake",
                        role="operator",
                    )
                )
                await session.flush()

                session.add(
                    AdminRefreshSession(
                        id="session-cascade",
                        admin_id="admin-cascade",
                        token_hash="a" * 64,
                        family_id="family-001",
                        expires_at=now + timedelta(days=7),
                    )
                )
                await session.commit()

            async with session_factory() as session:
                admin = await session.get(AdminUser, "admin-cascade")
                await session.delete(admin)
                await session.commit()

            async with session_factory() as session:
                session_row = await session.get(AdminRefreshSession, "session-cascade")
                assert session_row is None, (
                    "RefreshSession must be cascade-deleted with its AdminUser"
                )
        finally:
            await _dispose(engine)

    asyncio.run(scenario())


# ---------------------------------------------------------------------------
# AdminContext dataclass tests (T-05 completion criteria)
# ---------------------------------------------------------------------------

def test_admin_context_is_frozen() -> None:
    """AdminContext must be immutable — assigning a field must raise."""
    from backend.app.auth.admin_context import AdminContext

    ctx = AdminContext(admin_id="a1", username="alice", role="operator")

    with pytest.raises((AttributeError, TypeError)):
        ctx.admin_id = "modified"  # type: ignore[misc]


def test_admin_context_role_values() -> None:
    """AdminContext accepts all three valid role literals."""
    from backend.app.auth.admin_context import AdminContext

    for role in ("super_admin", "operator", "auditor"):
        ctx = AdminContext(admin_id="x", username="u", role=role)  # type: ignore[arg-type]
        assert ctx.role == role
