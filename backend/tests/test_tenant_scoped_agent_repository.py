"""Integration tests for the tenant-scoped agent repository."""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.app.db.base import Base
from backend.app.db.models import Agent, Tenant
from backend.app.infrastructure.database.tenant_repositories import (
    TenantScopedAgentRepository,
)


@pytest_asyncio.fixture
async def database() -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """Create an in-memory SQLite database for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    @event.listens_for(engine.sync_engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield engine, session_factory
    finally:
        await engine.dispose()


async def _seed_tenant(session: AsyncSession, tenant_id: str) -> None:
    """Create a tenant for testing."""
    session.add(Tenant(id=tenant_id, name=f"Tenant {tenant_id}"))
    await session.flush()


@pytest.mark.asyncio
async def test_list_by_tenant_returns_only_tenant_agents(
    database: tuple[AsyncEngine, async_sessionmaker[AsyncSession]],
) -> None:
    """Test that list_by_tenant returns only agents belonging to the tenant."""
    _, session_factory = database

    async with session_factory() as session:
        # Seed two tenants
        await _seed_tenant(session, "tenant-a")
        await _seed_tenant(session, "tenant-b")

        # Create agents for each tenant
        session.add_all(
            [
                Agent(id="agent-a1", tenant_id="tenant-a", name="Agent A1"),
                Agent(id="agent-a2", tenant_id="tenant-a", name="Agent A2"),
                Agent(id="agent-b1", tenant_id="tenant-b", name="Agent B1"),
            ]
        )
        await session.commit()

    async with session_factory() as session:
        repo = TenantScopedAgentRepository(session)
        agents = await repo.list_by_tenant("tenant-a")

        assert len(agents) == 2
        assert all(agent.tenant_id == "tenant-a" for agent in agents)
        agent_ids = {agent.id for agent in agents}
        assert agent_ids == {"agent-a1", "agent-a2"}


@pytest.mark.asyncio
async def test_list_by_tenant_returns_empty_for_nonexistent_tenant(
    database: tuple[AsyncEngine, async_sessionmaker[AsyncSession]],
) -> None:
    """Test that list_by_tenant returns empty list for nonexistent tenant."""
    _, session_factory = database

    async with session_factory() as session:
        await _seed_tenant(session, "tenant-a")
        session.add(Agent(id="agent-a1", tenant_id="tenant-a", name="Agent A1"))
        await session.commit()

    async with session_factory() as session:
        repo = TenantScopedAgentRepository(session)
        agents = await repo.list_by_tenant("tenant-nonexistent")

        assert len(agents) == 0


@pytest.mark.asyncio
async def test_get_by_id_returns_agent_when_owned_by_tenant(
    database: tuple[AsyncEngine, async_sessionmaker[AsyncSession]],
) -> None:
    """Test that get_by_id returns agent only if it belongs to the tenant."""
    _, session_factory = database

    async with session_factory() as session:
        await _seed_tenant(session, "tenant-a")
        session.add(Agent(id="agent-a1", tenant_id="tenant-a", name="Agent A1"))
        await session.commit()

    async with session_factory() as session:
        repo = TenantScopedAgentRepository(session)
        agent = await repo.get_by_id("agent-a1", "tenant-a")

        assert agent is not None
        assert agent.id == "agent-a1"
        assert agent.tenant_id == "tenant-a"
        assert agent.name == "Agent A1"


@pytest.mark.asyncio
async def test_get_by_id_returns_none_for_cross_tenant_access(
    database: tuple[AsyncEngine, async_sessionmaker[AsyncSession]],
) -> None:
    """Test that get_by_id returns None when agent belongs to different tenant."""
    _, session_factory = database

    async with session_factory() as session:
        await _seed_tenant(session, "tenant-a")
        await _seed_tenant(session, "tenant-b")
        session.add(Agent(id="agent-a1", tenant_id="tenant-a", name="Agent A1"))
        await session.commit()

    async with session_factory() as session:
        repo = TenantScopedAgentRepository(session)
        agent = await repo.get_by_id("agent-a1", "tenant-b")

        assert agent is None


@pytest.mark.asyncio
async def test_get_by_id_returns_none_for_nonexistent_agent(
    database: tuple[AsyncEngine, async_sessionmaker[AsyncSession]],
) -> None:
    """Test that get_by_id returns None for nonexistent agent."""
    _, session_factory = database

    async with session_factory() as session:
        await _seed_tenant(session, "tenant-a")
        await session.commit()

    async with session_factory() as session:
        repo = TenantScopedAgentRepository(session)
        agent = await repo.get_by_id("agent-nonexistent", "tenant-a")

        assert agent is None


@pytest.mark.asyncio
async def test_create_forces_tenant_id_from_context(
    database: tuple[AsyncEngine, async_sessionmaker[AsyncSession]],
) -> None:
    """Test that create forces tenant_id from context parameter."""
    _, session_factory = database

    async with session_factory() as session:
        await _seed_tenant(session, "tenant-a")
        await session.commit()

    async with session_factory() as session:
        repo = TenantScopedAgentRepository(session)
        agent = await repo.create(
            agent_id="agent-new",
            tenant_id="tenant-a",
            name="New Agent",
            system_prompt="Test prompt",
            knowledge_mode="required",
        )
        await session.commit()

        assert agent.id == "agent-new"
        assert agent.tenant_id == "tenant-a"
        assert agent.name == "New Agent"
        assert agent.system_prompt == "Test prompt"
        assert agent.knowledge_mode == "required"

    # Verify agent was persisted
    async with session_factory() as session:
        result = await session.scalar(
            select(Agent).where(Agent.id == "agent-new")
        )
        assert result is not None
        assert result.tenant_id == "tenant-a"


@pytest.mark.asyncio
async def test_update_succeeds_when_agent_owned_by_tenant(
    database: tuple[AsyncEngine, async_sessionmaker[AsyncSession]],
) -> None:
    """Test that update succeeds when agent belongs to tenant."""
    _, session_factory = database

    async with session_factory() as session:
        await _seed_tenant(session, "tenant-a")
        session.add(
            Agent(
                id="agent-a1",
                tenant_id="tenant-a",
                name="Original Name",
                system_prompt="Original Prompt",
            )
        )
        await session.commit()

    async with session_factory() as session:
        repo = TenantScopedAgentRepository(session)
        agent = await repo.update(
            agent_id="agent-a1",
            tenant_id="tenant-a",
            updates={
                "name": "Updated Name",
                "system_prompt": "Updated Prompt",
            },
        )
        await session.commit()

        assert agent is not None
        assert agent.name == "Updated Name"
        assert agent.system_prompt == "Updated Prompt"

    # Verify changes were persisted
    async with session_factory() as session:
        result = await session.scalar(
            select(Agent).where(Agent.id == "agent-a1")
        )
        assert result.name == "Updated Name"
        assert result.system_prompt == "Updated Prompt"


@pytest.mark.asyncio
async def test_update_returns_none_for_cross_tenant_access(
    database: tuple[AsyncEngine, async_sessionmaker[AsyncSession]],
) -> None:
    """Test that update returns None when agent belongs to different tenant."""
    _, session_factory = database

    async with session_factory() as session:
        await _seed_tenant(session, "tenant-a")
        await _seed_tenant(session, "tenant-b")
        session.add(
            Agent(
                id="agent-a1",
                tenant_id="tenant-a",
                name="Original Name",
            )
        )
        await session.commit()

    async with session_factory() as session:
        repo = TenantScopedAgentRepository(session)
        agent = await repo.update(
            agent_id="agent-a1",
            tenant_id="tenant-b",
            updates={"name": "Hacked Name"},
        )
        await session.commit()

        assert agent is None

    # Verify agent was not modified
    async with session_factory() as session:
        result = await session.scalar(
            select(Agent).where(Agent.id == "agent-a1")
        )
        assert result.name == "Original Name"


@pytest.mark.asyncio
async def test_delete_succeeds_when_agent_owned_by_tenant(
    database: tuple[AsyncEngine, async_sessionmaker[AsyncSession]],
) -> None:
    """Test that delete succeeds when agent belongs to tenant."""
    _, session_factory = database

    async with session_factory() as session:
        await _seed_tenant(session, "tenant-a")
        session.add(Agent(id="agent-a1", tenant_id="tenant-a", name="Agent A1"))
        await session.commit()

    async with session_factory() as session:
        repo = TenantScopedAgentRepository(session)
        deleted = await repo.delete("agent-a1", "tenant-a")
        await session.commit()

        assert deleted is True

    # Verify agent was deleted
    async with session_factory() as session:
        result = await session.scalar(
            select(Agent).where(Agent.id == "agent-a1")
        )
        assert result is None


@pytest.mark.asyncio
async def test_delete_returns_false_for_cross_tenant_access(
    database: tuple[AsyncEngine, async_sessionmaker[AsyncSession]],
) -> None:
    """Test that delete returns False when agent belongs to different tenant."""
    _, session_factory = database

    async with session_factory() as session:
        await _seed_tenant(session, "tenant-a")
        await _seed_tenant(session, "tenant-b")
        session.add(Agent(id="agent-a1", tenant_id="tenant-a", name="Agent A1"))
        await session.commit()

    async with session_factory() as session:
        repo = TenantScopedAgentRepository(session)
        deleted = await repo.delete("agent-a1", "tenant-b")
        await session.commit()

        assert deleted is False

    # Verify agent still exists
    async with session_factory() as session:
        result = await session.scalar(
            select(Agent).where(Agent.id == "agent-a1")
        )
        assert result is not None


@pytest.mark.asyncio
async def test_delete_returns_false_for_nonexistent_agent(
    database: tuple[AsyncEngine, async_sessionmaker[AsyncSession]],
) -> None:
    """Test that delete returns False for nonexistent agent."""
    _, session_factory = database

    async with session_factory() as session:
        await _seed_tenant(session, "tenant-a")
        await session.commit()

    async with session_factory() as session:
        repo = TenantScopedAgentRepository(session)
        deleted = await repo.delete("agent-nonexistent", "tenant-a")
        await session.commit()

        assert deleted is False


@pytest.mark.asyncio
async def test_list_by_tenant_orders_by_name(
    database: tuple[AsyncEngine, async_sessionmaker[AsyncSession]],
) -> None:
    """Test that list_by_tenant returns agents ordered by name."""
    _, session_factory = database

    async with session_factory() as session:
        await _seed_tenant(session, "tenant-a")
        session.add_all(
            [
                Agent(id="agent-1", tenant_id="tenant-a", name="Zebra Agent"),
                Agent(id="agent-2", tenant_id="tenant-a", name="Alpha Agent"),
                Agent(id="agent-3", tenant_id="tenant-a", name="Beta Agent"),
            ]
        )
        await session.commit()

    async with session_factory() as session:
        repo = TenantScopedAgentRepository(session)
        agents = await repo.list_by_tenant("tenant-a")

        assert len(agents) == 3
        assert agents[0].name == "Alpha Agent"
        assert agents[1].name == "Beta Agent"
        assert agents[2].name == "Zebra Agent"
