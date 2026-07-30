"""Integration tests for authenticated tenant-scoped chat persistence."""

from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, func, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)

from backend.app.ai.contracts import GenerationResult
from backend.app.api.dependencies import get_core_ai_runtime
from backend.app.auth.api_keys import IssuedApiKey, issue_api_key
from backend.app.db.base import Base, get_db
from backend.app.db.models import Agent, ApiKey, Conversation, Message, Tenant
from backend.app.main import create_app


async def _open_test_app(
    database_path: Path,
) -> tuple[
    FastAPI,
    AsyncEngine,
    async_sessionmaker,
    AsyncMock,
]:
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
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
    runtime = AsyncMock()
    runtime.generate.return_value = GenerationResult(
        content="Test assistant response",
        model="test-model",
        finish_reason="stop",
        prompt_tokens=7,
        completion_tokens=4,
    )

    application = create_app()

    async def override_get_db():
        async with session_factory() as session:
            yield session

    application.dependency_overrides[get_db] = override_get_db
    application.dependency_overrides[get_core_ai_runtime] = lambda: runtime
    return application, engine, session_factory, runtime


async def _seed_tenant(
    session_factory: async_sessionmaker,
    *,
    tenant_id: str,
    agent_id: str,
    system_prompt: str | None = None,
    active_key: bool = True,
) -> IssuedApiKey:
    issued = issue_api_key()
    async with session_factory() as session:
        session.add_all(
            [
                Tenant(id=tenant_id, name=tenant_id),
                Agent(
                    id=agent_id,
                    tenant_id=tenant_id,
                    name=agent_id,
                    system_prompt=system_prompt,
                ),
                ApiKey(
                    tenant_id=tenant_id,
                    key_id=issued.key_id,
                    key_digest=issued.key_digest,
                    is_active=active_key,
                ),
            ]
        )
        await session.commit()
    return issued


def _headers(issued: IssuedApiKey, agent_id: str) -> dict[str, str]:
    return {
        "X-API-Key": issued.raw_key,
        "X-Agent-ID": agent_id,
    }


@pytest.mark.asyncio
async def test_chat_requires_an_active_api_key(tmp_path: Path) -> None:
    app, engine, _, runtime = await _open_test_app(
        tmp_path / "missing-key.sqlite3"
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/chat",
                json={"message": "Hello"},
                headers={"X-Agent-ID": "agent-a"},
            )

        assert response.status_code == 401
        runtime.generate.assert_not_awaited()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_api_key_cannot_select_another_tenants_agent(
    tmp_path: Path,
) -> None:
    app, engine, session_factory, runtime = await _open_test_app(
        tmp_path / "agent-isolation.sqlite3"
    )

    try:
        tenant_a_key = await _seed_tenant(
            session_factory,
            tenant_id="tenant-a",
            agent_id="agent-a",
        )
        await _seed_tenant(
            session_factory,
            tenant_id="tenant-b",
            agent_id="agent-b",
        )

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/chat",
                json={"message": "Hello"},
                headers=_headers(tenant_a_key, "agent-b"),
            )

        assert response.status_code == 403
        runtime.generate.assert_not_awaited()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_chat_persists_messages_with_trusted_runtime_context(
    tmp_path: Path,
) -> None:
    app, engine, session_factory, runtime = await _open_test_app(
        tmp_path / "persistence.sqlite3"
    )

    try:
        issued = await _seed_tenant(
            session_factory,
            tenant_id="tenant-a",
            agent_id="agent-a",
            system_prompt="Answer from verified knowledge.",
        )

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/chat",
                json={"message": "Hello"},
                headers=_headers(issued, "agent-a"),
            )

        assert response.status_code == 200
        payload = response.json()
        assert payload["reply"] == "Test assistant response"
        assert payload["model"] == "test-model"
        assert payload["usage"] == {"prompt": 7, "completion": 4}
        assert payload["answer_status"] == "generated"
        assert payload["sources"] == []
        assert payload["handoff_required"] is False
        assert payload["handoff_id"] is None

        request = runtime.generate.await_args.args[0]
        assert request.context.tenant_id == "tenant-a"
        assert request.context.agent_id == "agent-a"
        assert [message.role for message in request.messages] == [
            "system",
            "user",
        ]

        async with session_factory() as session:
            conversation = await session.scalar(
                select(Conversation).where(
                    Conversation.id == payload["conversation_id"],
                    Conversation.tenant_id == "tenant-a",
                    Conversation.agent_id == "agent-a",
                )
            )
            messages = list(
                (
                    await session.scalars(
                        select(Message)
                        .where(
                            Message.tenant_id == "tenant-a",
                            Message.conversation_id
                            == payload["conversation_id"],
                        )
                        .order_by(Message.created_at, Message.id)
                    )
                ).all()
            )

        assert conversation is not None
        assert [(item.role, item.content) for item in messages] == [
            ("user", "Hello"),
            ("assistant", "Test assistant response"),
        ]
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_request_body_rejects_tenant_and_agent_identity(
    tmp_path: Path,
) -> None:
    app, engine, session_factory, runtime = await _open_test_app(
        tmp_path / "forbidden-body-identity.sqlite3"
    )

    try:
        issued = await _seed_tenant(
            session_factory,
            tenant_id="tenant-a",
            agent_id="agent-a",
        )

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/chat",
                json={
                    "message": "Hello",
                    "tenant_id": "tenant-b",
                    "agent_id": "agent-b",
                },
                headers=_headers(issued, "agent-a"),
            )

        assert response.status_code == 422
        runtime.generate.assert_not_awaited()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_conversation_id_is_scoped_to_tenant_and_agent(
    tmp_path: Path,
) -> None:
    app, engine, session_factory, runtime = await _open_test_app(
        tmp_path / "conversation-isolation.sqlite3"
    )

    try:
        await _seed_tenant(
            session_factory,
            tenant_id="tenant-a",
            agent_id="agent-a",
        )
        tenant_b_key = await _seed_tenant(
            session_factory,
            tenant_id="tenant-b",
            agent_id="agent-b",
        )
        async with session_factory() as session:
            session.add(
                Conversation(
                    id="tenant-a-conversation",
                    tenant_id="tenant-a",
                    agent_id="agent-a",
                )
            )
            await session.commit()

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/chat",
                json={
                    "message": "Try another tenant",
                    "conversation_id": "tenant-a-conversation",
                },
                headers=_headers(tenant_b_key, "agent-b"),
            )

        assert response.status_code == 404
        runtime.generate.assert_not_awaited()

        async with session_factory() as session:
            message_count = await session.scalar(
                select(func.count()).select_from(Message)
            )
        assert message_count == 0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_follow_up_uses_only_authorized_persisted_history(
    tmp_path: Path,
) -> None:
    app, engine, session_factory, runtime = await _open_test_app(
        tmp_path / "history.sqlite3"
    )

    try:
        issued = await _seed_tenant(
            session_factory,
            tenant_id="tenant-a",
            agent_id="agent-a",
        )
        runtime.generate.side_effect = [
            GenerationResult(
                content="First answer",
                model="test-model",
            ),
            GenerationResult(
                content="Second answer",
                model="test-model",
            ),
        ]

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            first = await client.post(
                "/api/chat",
                json={"message": "First question"},
                headers=_headers(issued, "agent-a"),
            )
            second = await client.post(
                "/api/chat",
                json={
                    "message": "Second question",
                    "conversation_id": first.json()["conversation_id"],
                },
                headers=_headers(issued, "agent-a"),
            )

        assert first.status_code == 200
        assert second.status_code == 200

        second_request = runtime.generate.await_args_list[1].args[0]
        assert [
            (message.role, message.content)
            for message in second_request.messages
        ] == [
            ("user", "First question"),
            ("assistant", "First answer"),
            ("user", "Second question"),
        ]
    finally:
        await engine.dispose()
