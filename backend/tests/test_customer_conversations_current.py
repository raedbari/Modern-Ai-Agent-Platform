from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    create_async_engine,
)

from backend.app.api.dependencies import (
    require_tenant_user_jwt,
)
from backend.app.auth.tenant_context import (
    TenantUserContext,
)
from backend.app.db.base import Base, get_db
from backend.app.db.models import (
    Agent,
    Conversation,
    Message,
    Tenant,
)
from backend.app.main import create_app


async def open_app(database_path: Path):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )

    @event.listens_for(
        engine.sync_engine,
        "connect",
    )
    def enable_foreign_keys(
        connection,
        _record,
    ):
        cursor = connection.cursor()
        cursor.execute(
            "PRAGMA foreign_keys=ON"
        )
        cursor.close()

    async with engine.begin() as connection:
        await connection.run_sync(
            Base.metadata.create_all
        )

    sessions = async_sessionmaker(
        engine,
        expire_on_commit=False,
    )

    app = create_app()

    async def override_db():
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_db] = (
        override_db
    )

    return app, engine, sessions


def context(
    tenant_id: str,
    role: str = "tenant_owner",
) -> TenantUserContext:
    return TenantUserContext(
        user_id=f"user-{tenant_id}",
        email=f"{tenant_id}@example.test",
        display_name="Test User",
        tenant_id=tenant_id,
        membership_id=f"membership-{tenant_id}",
        role=role,  # type: ignore[arg-type]
        auth_method="jwt",
        session_family_id="family",
        jti="jti",
    )


async def seed(sessions):
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
                    id="conv-a",
                    tenant_id="tenant-a",
                    agent_id="agent-a",
                ),
                Conversation(
                    id="conv-b",
                    tenant_id="tenant-b",
                    agent_id="agent-b",
                ),
            ]
        )
        await session.flush()

        session.add_all(
            [
                Message(
                    id="msg-a",
                    tenant_id="tenant-a",
                    conversation_id="conv-a",
                    role="user",
                    content="Tenant A message",
                ),
                Message(
                    id="msg-b",
                    tenant_id="tenant-b",
                    conversation_id="conv-b",
                    role="user",
                    content="Tenant B message",
                ),
            ]
        )

        await session.commit()


@pytest.mark.asyncio
async def test_tenant_lists_only_own_conversations(
    tmp_path: Path,
):
    app, engine, sessions = await open_app(
        tmp_path / "list.sqlite3"
    )

    try:
        await seed(sessions)

        app.dependency_overrides[
            require_tenant_user_jwt
        ] = lambda: context("tenant-a")

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/api/customer/conversations"
            )

        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["id"] == "conv-a"
        assert data["items"][0]["tenant_id"] == "tenant-a"

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_cross_tenant_conversation_returns_404(
    tmp_path: Path,
):
    app, engine, sessions = await open_app(
        tmp_path / "cross.sqlite3"
    )

    try:
        await seed(sessions)

        app.dependency_overrides[
            require_tenant_user_jwt
        ] = lambda: context("tenant-a")

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/api/customer/conversations/conv-b"
            )

        assert response.status_code == 404

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_cross_tenant_messages_return_404(
    tmp_path: Path,
):
    app, engine, sessions = await open_app(
        tmp_path / "messages.sqlite3"
    )

    try:
        await seed(sessions)

        app.dependency_overrides[
            require_tenant_user_jwt
        ] = lambda: context("tenant-a")

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/api/customer/conversations/conv-b/messages"
            )

        assert response.status_code == 404

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_conversation_viewer_can_read(
    tmp_path: Path,
):
    app, engine, sessions = await open_app(
        tmp_path / "viewer.sqlite3"
    )

    try:
        await seed(sessions)

        app.dependency_overrides[
            require_tenant_user_jwt
        ] = lambda: context(
            "tenant-a",
            "conversation_viewer",
        )

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/api/customer/conversations"
            )

        assert response.status_code == 200

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_billing_manager_cannot_read(
    tmp_path: Path,
):
    app, engine, sessions = await open_app(
        tmp_path / "billing.sqlite3"
    )

    try:
        await seed(sessions)

        app.dependency_overrides[
            require_tenant_user_jwt
        ] = lambda: context(
            "tenant-a",
            "billing_manager",
        )

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/api/customer/conversations"
            )

        assert response.status_code == 403

    finally:
        await engine.dispose()
