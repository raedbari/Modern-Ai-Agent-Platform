"""Current-schema tests for tenant-scoped conversations."""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.app.db.base import Base
from backend.app.db.models import (
    Agent,
    Conversation,
    Tenant,
)
from backend.app.infrastructure.database.tenant_repositories import (
    TenantScopedConversationRepository,
)


@pytest_asyncio.fixture
async def database():
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:"
    )

    @event.listens_for(
        engine.sync_engine,
        "connect",
    )
    def enable_foreign_keys(
        dbapi_connection,
        _connection_record,
    ):
        cursor = dbapi_connection.cursor()
        cursor.execute(
            "PRAGMA foreign_keys=ON"
        )
        cursor.close()

    async with engine.begin() as connection:
        await connection.run_sync(
            Base.metadata.create_all
        )

    session_factory = async_sessionmaker(
        engine,
        expire_on_commit=False,
    )

    try:
        yield engine, session_factory
    finally:
        await engine.dispose()


async def seed(
    session_factory,
):
    async with session_factory() as session:
        session.add_all(
            [
                Tenant(
                    id="tenant-a",
                    name="Tenant A",
                ),
                Tenant(
                    id="tenant-b",
                    name="Tenant B",
                ),
            ]
        )
        await session.flush()

        session.add_all(
            [
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
        await session.flush()

        session.add_all(
            [
                Conversation(
                    id="conv-a1",
                    tenant_id="tenant-a",
                    agent_id="agent-a",
                ),
                Conversation(
                    id="conv-a2",
                    tenant_id="tenant-a",
                    agent_id="agent-a",
                ),
                Conversation(
                    id="conv-b1",
                    tenant_id="tenant-b",
                    agent_id="agent-b",
                ),
            ]
        )

        await session.commit()


@pytest.mark.asyncio
async def test_list_is_tenant_scoped(
    database,
):
    _, session_factory = database
    await seed(session_factory)

    async with session_factory() as session:
        repo = TenantScopedConversationRepository(
            session
        )

        items = await repo.list_by_agent(
            "agent-a",
            "tenant-a",
        )

        assert {
            item.id for item in items
        } == {
            "conv-a1",
            "conv-a2",
        }


@pytest.mark.asyncio
async def test_cross_tenant_list_is_empty(
    database,
):
    _, session_factory = database
    await seed(session_factory)

    async with session_factory() as session:
        repo = TenantScopedConversationRepository(
            session
        )

        items = await repo.list_by_agent(
            "agent-b",
            "tenant-a",
        )

        assert items == []


@pytest.mark.asyncio
async def test_get_own_conversation(
    database,
):
    _, session_factory = database
    await seed(session_factory)

    async with session_factory() as session:
        repo = TenantScopedConversationRepository(
            session
        )

        item = await repo.get_by_id(
            "conv-a1",
            "tenant-a",
        )

        assert item is not None
        assert item.id == "conv-a1"
        assert item.tenant_id == "tenant-a"


@pytest.mark.asyncio
async def test_cross_tenant_get_is_hidden(
    database,
):
    _, session_factory = database
    await seed(session_factory)

    async with session_factory() as session:
        repo = TenantScopedConversationRepository(
            session
        )

        item = await repo.get_by_id(
            "conv-b1",
            "tenant-a",
        )

        assert item is None


@pytest.mark.asyncio
async def test_cross_tenant_delete_is_blocked(
    database,
):
    _, session_factory = database
    await seed(session_factory)

    async with session_factory() as session:
        repo = TenantScopedConversationRepository(
            session
        )

        deleted = await repo.delete(
            "conv-b1",
            "tenant-a",
        )

        assert deleted is False

        existing = await session.get(
            Conversation,
            "conv-b1",
        )

        assert existing is not None


@pytest.mark.asyncio
async def test_delete_own_conversation(
    database,
):
    _, session_factory = database
    await seed(session_factory)

    async with session_factory() as session:
        repo = TenantScopedConversationRepository(
            session
        )

        deleted = await repo.delete(
            "conv-a1",
            "tenant-a",
        )

        assert deleted is True

        await session.commit()

    async with session_factory() as session:
        existing = await session.get(
            Conversation,
            "conv-a1",
        )

        assert existing is None
