"""Tests for tenant-scoped administrative agent configuration updates."""

from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.app.api.schemas.admin import AgentConfigUpdate
from backend.app.db.base import Base
from backend.app.db.models import Agent, Tenant
from backend.app.operations.admin_lifecycle import (
    AdminLifecycleValidationError,
    AdminResourceNotFoundError,
    update_agent_config,
)


async def _open_sessions(
    database_path: Path,
) -> tuple[
    async_sessionmaker[AsyncSession],
    object,
]:
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{database_path.as_posix()}"
    )

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    return (
        async_sessionmaker(
            engine,
            expire_on_commit=False,
        ),
        engine,
    )


async def _seed_agents(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    async with sessions() as session:
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
                    name="Original Agent",
                    system_prompt="Original prompt",
                    knowledge_mode="preferred",
                    contact_message="Original contact",
                ),
                Agent(
                    id="agent-b",
                    tenant_id="tenant-b",
                    name="Other Agent",
                    system_prompt="Other prompt",
                    knowledge_mode="required",
                    contact_message="Other contact",
                ),
            ]
        )

        await session.commit()


@pytest.mark.asyncio
async def test_updates_only_supplied_fields(
    tmp_path: Path,
) -> None:
    sessions, engine = await _open_sessions(
        tmp_path / "partial-update.sqlite3"
    )

    try:
        await _seed_agents(sessions)

        async with sessions() as session:
            agent = await update_agent_config(
                session,
                tenant_id="tenant-a",
                agent_id="agent-a",
                update=AgentConfigUpdate(
                    name="Updated Agent",
                    knowledge_mode="disabled",
                ),
            )

            assert agent.name == "Updated Agent"
            assert agent.knowledge_mode == "disabled"
            assert agent.system_prompt == "Original prompt"
            assert agent.contact_message == "Original contact"

            await session.commit()

        async with sessions() as session:
            stored = await session.get(Agent, "agent-a")

            assert stored is not None
            assert stored.name == "Updated Agent"
            assert stored.knowledge_mode == "disabled"
            assert stored.system_prompt == "Original prompt"
            assert stored.contact_message == "Original contact"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_nullable_fields_can_be_cleared(
    tmp_path: Path,
) -> None:
    sessions, engine = await _open_sessions(
        tmp_path / "clear-nullable.sqlite3"
    )

    try:
        await _seed_agents(sessions)

        async with sessions() as session:
            agent = await update_agent_config(
                session,
                tenant_id="tenant-a",
                agent_id="agent-a",
                update=AgentConfigUpdate(
                    system_prompt=None,
                    contact_message=None,
                ),
            )

            assert agent.system_prompt is None
            assert agent.contact_message is None

            await session.commit()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_operation_does_not_commit_implicitly(
    tmp_path: Path,
) -> None:
    sessions, engine = await _open_sessions(
        tmp_path / "no-implicit-commit.sqlite3"
    )

    try:
        await _seed_agents(sessions)

        async with sessions() as session:
            agent = await update_agent_config(
                session,
                tenant_id="tenant-a",
                agent_id="agent-a",
                update=AgentConfigUpdate(
                    name="Temporary Name",
                ),
            )

            assert agent.name == "Temporary Name"

            await session.rollback()

        async with sessions() as session:
            stored = await session.get(Agent, "agent-a")

            assert stored is not None
            assert stored.name == "Original Agent"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_empty_update_is_rejected(
    tmp_path: Path,
) -> None:
    sessions, engine = await _open_sessions(
        tmp_path / "empty-update.sqlite3"
    )

    try:
        await _seed_agents(sessions)

        async with sessions() as session:
            with pytest.raises(
                AdminLifecycleValidationError,
                match="At least one",
            ):
                await update_agent_config(
                    session,
                    tenant_id="tenant-a",
                    agent_id="agent-a",
                    update=AgentConfigUpdate(),
                )
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_cross_tenant_agent_access_is_hidden(
    tmp_path: Path,
) -> None:
    sessions, engine = await _open_sessions(
        tmp_path / "tenant-isolation.sqlite3"
    )

    try:
        await _seed_agents(sessions)

        async with sessions() as session:
            with pytest.raises(
                AdminResourceNotFoundError,
                match="Agent not found",
            ):
                await update_agent_config(
                    session,
                    tenant_id="tenant-b",
                    agent_id="agent-a",
                    update=AgentConfigUpdate(
                        name="Cross-tenant mutation",
                    ),
                )

            await session.rollback()

        async with sessions() as session:
            tenant_a_agent = await session.get(Agent, "agent-a")
            tenant_b_agent = await session.get(Agent, "agent-b")

            assert tenant_a_agent is not None
            assert tenant_b_agent is not None
            assert tenant_a_agent.name == "Original Agent"
            assert tenant_b_agent.name == "Other Agent"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_missing_tenant_is_hidden(
    tmp_path: Path,
) -> None:
    sessions, engine = await _open_sessions(
        tmp_path / "missing-tenant.sqlite3"
    )

    try:
        await _seed_agents(sessions)

        async with sessions() as session:
            with pytest.raises(
                AdminResourceNotFoundError,
                match="Tenant not found",
            ):
                await update_agent_config(
                    session,
                    tenant_id="missing-tenant",
                    agent_id="agent-a",
                    update=AgentConfigUpdate(
                        name="Invalid mutation",
                    ),
                )
    finally:
        await engine.dispose()
