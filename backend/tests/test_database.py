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
from backend.app.db.models import Agent, Conversation, Message, Tenant


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
    }


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
