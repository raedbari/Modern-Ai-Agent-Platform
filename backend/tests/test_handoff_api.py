"""Tenant-isolation and workflow tests for the handoff API."""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)

from backend.app.api.dependencies import get_core_ai_runtime
from backend.app.auth.api_keys import IssuedApiKey, issue_api_key
from backend.app.db.base import Base, get_db
from backend.app.db.models import (
    Agent,
    ApiKey,
    Conversation,
    Handoff,
    Message,
    Tenant,
)
from backend.app.main import create_app


async def _app(
    database_path: Path,
) -> tuple[FastAPI, AsyncEngine, async_sessionmaker]:
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )

    @event.listens_for(engine.sync_engine, "connect")
    def enable_foreign_keys(connection, _record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    application = create_app()

    async def override_get_db():
        async with sessions() as session:
            yield session

    application.dependency_overrides[get_db] = override_get_db
    application.dependency_overrides[get_core_ai_runtime] = AsyncMock
    return application, engine, sessions


async def _seed(
    sessions: async_sessionmaker,
    *,
    tenant_id: str,
    agent_id: str,
    handoff_id: str,
) -> IssuedApiKey:
    issued = issue_api_key()
    conversation_id = f"conversation-{tenant_id}"
    message_id = f"message-{tenant_id}"
    async with sessions() as session:
        session.add_all(
            [
                Tenant(id=tenant_id, name=tenant_id),
                Agent(
                    id=agent_id,
                    tenant_id=tenant_id,
                    name=agent_id,
                ),
                ApiKey(
                    tenant_id=tenant_id,
                    key_id=issued.key_id,
                    key_digest=issued.key_digest,
                ),
            ]
        )
        await session.flush()
        session.add(
            Conversation(
                id=conversation_id,
                tenant_id=tenant_id,
                agent_id=agent_id,
            )
        )
        await session.flush()
        session.add(
            Message(
                id=message_id,
                tenant_id=tenant_id,
                conversation_id=conversation_id,
                role="user",
                content="Need help",
            )
        )
        await session.flush()
        session.add(
            Handoff(
                id=handoff_id,
                tenant_id=tenant_id,
                agent_id=agent_id,
                conversation_id=conversation_id,
                trigger_message_id=message_id,
                reason="insufficient_knowledge",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        )
        await session.commit()
    return issued


def _headers(issued: IssuedApiKey, agent_id: str) -> dict[str, str]:
    return {
        "X-API-Key": issued.raw_key,
        "X-Agent-ID": agent_id,
    }


@pytest.mark.asyncio
async def test_handoffs_are_scoped_and_follow_valid_workflow(
    tmp_path: Path,
) -> None:
    app, engine, sessions = await _app(tmp_path / "handoffs.sqlite3")
    try:
        tenant_a_key = await _seed(
            sessions,
            tenant_id="tenant-a",
            agent_id="agent-a",
            handoff_id="handoff-a",
        )
        await _seed(
            sessions,
            tenant_id="tenant-b",
            agent_id="agent-b",
            handoff_id="handoff-b",
        )

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            listed = await client.get(
                "/api/handoffs",
                headers=_headers(tenant_a_key, "agent-a"),
            )
            foreign = await client.get(
                "/api/handoffs/handoff-b",
                headers=_headers(tenant_a_key, "agent-a"),
            )
            invalid_assignment = await client.patch(
                "/api/handoffs/handoff-a",
                json={"status": "assigned"},
                headers=_headers(tenant_a_key, "agent-a"),
            )
            assigned = await client.patch(
                "/api/handoffs/handoff-a",
                json={
                    "status": "assigned",
                    "assigned_to": "support@example.test",
                },
                headers=_headers(tenant_a_key, "agent-a"),
            )
            closed = await client.patch(
                "/api/handoffs/handoff-a",
                json={
                    "status": "closed",
                    "resolution_note": "Customer contacted.",
                },
                headers=_headers(tenant_a_key, "agent-a"),
            )
            reopen = await client.patch(
                "/api/handoffs/handoff-a",
                json={"status": "open"},
                headers=_headers(tenant_a_key, "agent-a"),
            )

        assert listed.status_code == 200
        assert [item["id"] for item in listed.json()] == ["handoff-a"]
        assert foreign.status_code == 404
        assert invalid_assignment.status_code == 422
        assert assigned.status_code == 200
        assert assigned.json()["status"] == "assigned"
        assert closed.status_code == 200
        assert closed.json()["status"] == "closed"
        assert closed.json()["resolution_note"] == "Customer contacted."
        assert reopen.status_code == 409
    finally:
        await engine.dispose()
