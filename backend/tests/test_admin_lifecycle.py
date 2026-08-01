"""Integration tests for the internal administrative lifecycle API."""

from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, func, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)

from backend.app.api.dependencies import require_admin_access
from backend.app.auth.api_keys import IssuedApiKey, issue_api_key
from backend.app.core.config import Settings, get_settings
from backend.app.db.base import Base, get_db
from backend.app.db.models import (
    Agent,
    AgentKnowledgeBase,
    ApiKey,
    Conversation,
    DocumentModel,
    IngestionJob,
    KnowledgeBaseModel,
    Message,
    Tenant,
)
from backend.app.infrastructure.storage import LocalUploadStorage
from backend.app.main import create_app


async def _open_test_app(
    database_path: Path,
    storage_root: Path,
    *,
    bypass_admin_auth: bool = True,
) -> tuple[FastAPI, AsyncEngine, async_sessionmaker]:
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

    sessions = async_sessionmaker(engine, expire_on_commit=False)
    application = create_app()

    async def override_get_db():
        async with sessions() as session:
            yield session

    application.dependency_overrides[get_db] = override_get_db
    application.dependency_overrides[get_settings] = lambda: Settings(
        upload_storage_root=storage_root,
        _env_file=None,
    )
    if bypass_admin_auth:
        application.dependency_overrides[require_admin_access] = lambda: None
    return application, engine, sessions


async def _seed_customer(
    sessions: async_sessionmaker,
    *,
    tenant_id: str,
    agent_ids: tuple[str, ...],
) -> IssuedApiKey:
    issued = issue_api_key()
    async with sessions() as session:
        session.add(Tenant(id=tenant_id, name=tenant_id))
        await session.flush()
        session.add_all(
            Agent(
                id=agent_id,
                tenant_id=tenant_id,
                name=agent_id,
            )
            for agent_id in agent_ids
        )
        session.add(
            ApiKey(
                tenant_id=tenant_id,
                key_id=issued.key_id,
                key_digest=issued.key_digest,
                name="test-key",
            )
        )
        await session.commit()
    return issued


async def _seed_agent_data(
    sessions: async_sessionmaker,
    storage_root: Path,
    *,
    tenant_id: str,
    agent_id: str,
    suffix: str,
) -> tuple[str, str, str, str]:
    knowledge_base_id = f"kb-{suffix}"
    document_id = f"document-{suffix}"
    conversation_id = f"conversation-{suffix}"
    storage = LocalUploadStorage(storage_root)
    storage_key = await storage.store(
        tenant_id=tenant_id,
        document_id=document_id,
        content=f"source-{suffix}".encode(),
    )
    async with sessions() as session:
        # SQLite enforces foreign keys immediately. Flush each parent layer
        # before inserting rows that reference it. This also makes the test
        # fixture independent of ORM mapper ordering.
        session.add(
            KnowledgeBaseModel(
                id=knowledge_base_id,
                tenant_id=tenant_id,
                name=f"KB {suffix}",
                description="",
            )
        )
        await session.flush()

        session.add_all(
            [
                AgentKnowledgeBase(
                    tenant_id=tenant_id,
                    agent_id=agent_id,
                    knowledge_base_id=knowledge_base_id,
                ),
                DocumentModel(
                    id=document_id,
                    tenant_id=tenant_id,
                    knowledge_base_id=knowledge_base_id,
                    agent_id=agent_id,
                    source_name=f"source-{suffix}.txt",
                    original_filename=f"source-{suffix}.txt",
                    mime_type="text/plain",
                    file_size_bytes=10,
                    content_hash=(suffix * 64)[:64],
                    status="ready",
                ),
                Conversation(
                    id=conversation_id,
                    tenant_id=tenant_id,
                    agent_id=agent_id,
                ),
            ]
        )
        await session.flush()

        session.add_all(
            [
                IngestionJob(
                    id=f"job-{suffix}",
                    tenant_id=tenant_id,
                    agent_id=agent_id,
                    knowledge_base_id=knowledge_base_id,
                    document_id=document_id,
                    storage_key=storage_key,
                    status="succeeded",
                    attempts=1,
                    max_attempts=3,
                ),
                Message(
                    id=f"message-{suffix}",
                    tenant_id=tenant_id,
                    conversation_id=conversation_id,
                    role="user",
                    content="Hello",
                ),
            ]
        )
        await session.commit()
    return knowledge_base_id, document_id, conversation_id, storage_key


@pytest.mark.asyncio
async def test_admin_header_is_required_and_compared(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("MAAP_ADMIN_API_KEY", "test-admin-secret")
    get_settings.cache_clear()
    app, engine, _ = await _open_test_app(
        tmp_path / "admin-auth.sqlite3",
        tmp_path / "uploads",
        bypass_admin_auth=False,
    )
    app.dependency_overrides.pop(get_settings, None)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            missing = await client.get("/api/admin/tenants")
            wrong = await client.get(
                "/api/admin/tenants",
                headers={"X-Admin-Key": "wrong"},
            )
            accepted = await client.get(
                "/api/admin/tenants",
                headers={"X-Admin-Key": "test-admin-secret"},
            )

        assert missing.status_code == 401
        assert wrong.status_code == 401
        assert accepted.status_code == 200
        assert accepted.json() == []
    finally:
        get_settings.cache_clear()
        await engine.dispose()


@pytest.mark.asyncio
async def test_tenant_must_be_suspended_before_hard_delete(
    tmp_path: Path,
) -> None:
    storage_root = tmp_path / "uploads"
    app, engine, sessions = await _open_test_app(
        tmp_path / "tenant-delete.sqlite3",
        storage_root,
    )
    try:
        issued = await _seed_customer(
            sessions,
            tenant_id="tenant-a",
            agent_ids=("agent-a",),
        )
        _, _, _, storage_key = await _seed_agent_data(
            sessions,
            storage_root,
            tenant_id="tenant-a",
            agent_id="agent-a",
            suffix="a",
        )
        storage = LocalUploadStorage(storage_root)
        assert await storage.read(storage_key) == b"source-a"

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            active_delete = await client.delete(
                "/api/admin/tenants/tenant-a?confirm=tenant-a"
            )
            wrong_confirmation = await client.delete(
                "/api/admin/tenants/tenant-a?confirm=wrong"
            )
            suspended = await client.patch(
                "/api/admin/tenants/tenant-a/status",
                json={"is_active": False},
            )
            regular_access = await client.get(
                "/api/knowledge-bases",
                headers={
                    "X-API-Key": issued.raw_key,
                    "X-Agent-ID": "agent-a",
                },
            )
            deleted = await client.delete(
                "/api/admin/tenants/tenant-a?confirm=tenant-a"
            )

        assert active_delete.status_code == 409
        assert wrong_confirmation.status_code == 422
        assert suspended.status_code == 200
        assert suspended.json()["is_active"] is False
        assert regular_access.status_code == 401
        assert deleted.status_code == 204

        async with sessions() as session:
            tenant_count = await session.scalar(
                select(func.count()).select_from(Tenant)
            )
            message_count = await session.scalar(
                select(func.count()).select_from(Message)
            )
        assert tenant_count == 0
        assert message_count == 0
        with pytest.raises(FileNotFoundError):
            await storage.read(storage_key)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_agent_delete_requires_knowledge_cleanup_first(
    tmp_path: Path,
) -> None:
    storage_root = tmp_path / "uploads"
    app, engine, sessions = await _open_test_app(
        tmp_path / "agent-delete.sqlite3",
        storage_root,
    )
    try:
        issued = await _seed_customer(
            sessions,
            tenant_id="tenant-a",
            agent_ids=("agent-a", "agent-b"),
        )
        kb_a, document_a, conversation_a, storage_a = (
            await _seed_agent_data(
                sessions,
                storage_root,
                tenant_id="tenant-a",
                agent_id="agent-a",
                suffix="a",
            )
        )
        kb_b, document_b, _, storage_b = await _seed_agent_data(
            sessions,
            storage_root,
            tenant_id="tenant-a",
            agent_id="agent-b",
            suffix="b",
        )

        regular_headers = {
            "X-API-Key": issued.raw_key,
            "X-Agent-ID": "agent-a",
        }
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            active_delete = await client.delete(
                "/api/admin/tenants/tenant-a/agents/agent-a"
                "?confirm=agent-a"
            )
            suspended = await client.patch(
                "/api/admin/tenants/tenant-a/agents/agent-a/status",
                json={"is_active": False},
            )
            dependency_conflict = await client.delete(
                "/api/admin/tenants/tenant-a/agents/agent-a"
                "?confirm=agent-a"
            )
            reactivated = await client.patch(
                "/api/admin/tenants/tenant-a/agents/agent-a/status",
                json={"is_active": True},
            )
            document_deleted = await client.delete(
                f"/api/knowledge-bases/{kb_a}/documents/{document_a}",
                headers=regular_headers,
            )
            suspended_again = await client.patch(
                "/api/admin/tenants/tenant-a/agents/agent-a/status",
                json={"is_active": False},
            )
            deleted = await client.delete(
                "/api/admin/tenants/tenant-a/agents/agent-a"
                "?confirm=agent-a"
            )

        assert active_delete.status_code == 409
        assert suspended.status_code == 200
        assert dependency_conflict.status_code == 409
        assert "documents" in dependency_conflict.json()["detail"]
        assert reactivated.status_code == 200
        assert document_deleted.status_code == 204
        assert suspended_again.status_code == 200
        assert deleted.status_code == 204

        async with sessions() as session:
            assert await session.get(Agent, "agent-a") is None
            assert await session.get(Agent, "agent-b") is not None
            assert await session.get(DocumentModel, document_a) is None
            assert await session.get(DocumentModel, document_b) is not None
            assert await session.get(Conversation, conversation_a) is None
            assert await session.get(KnowledgeBaseModel, kb_a) is not None
            assert await session.get(KnowledgeBaseModel, kb_b) is not None

        storage = LocalUploadStorage(storage_root)
        with pytest.raises(FileNotFoundError):
            await storage.read(storage_a)
        assert await storage.read(storage_b) == b"source-b"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_key_revocation_and_scoped_conversation_deletion(
    tmp_path: Path,
) -> None:
    app, engine, sessions = await _open_test_app(
        tmp_path / "revoke-conversation.sqlite3",
        tmp_path / "uploads",
    )
    try:
        key_a = await _seed_customer(
            sessions,
            tenant_id="tenant-a",
            agent_ids=("agent-a",),
        )
        await _seed_customer(
            sessions,
            tenant_id="tenant-b",
            agent_ids=("agent-b",),
        )
        _, _, conversation_a, _ = await _seed_agent_data(
            sessions,
            tmp_path / "uploads",
            tenant_id="tenant-a",
            agent_id="agent-a",
            suffix="a",
        )

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            listed = await client.get(
                "/api/admin/tenants/tenant-a/api-keys"
            )
            cross_tenant_delete = await client.delete(
                f"/api/admin/tenants/tenant-b/conversations/"
                f"{conversation_a}"
            )
            revoked = await client.post(
                f"/api/admin/tenants/tenant-a/api-keys/"
                f"{key_a.key_id}/revoke"
            )
            regular_access = await client.get(
                "/api/knowledge-bases",
                headers={
                    "X-API-Key": key_a.raw_key,
                    "X-Agent-ID": "agent-a",
                },
            )
            deleted = await client.delete(
                f"/api/admin/tenants/tenant-a/conversations/"
                f"{conversation_a}"
            )

        assert listed.status_code == 200
        assert listed.json()[0]["key_id"] == key_a.key_id
        assert "key_digest" not in listed.json()[0]
        assert cross_tenant_delete.status_code == 404
        assert revoked.status_code == 200
        assert revoked.json()["is_active"] is False
        assert revoked.json()["revoked_at"] is not None
        assert regular_access.status_code == 401
        assert deleted.status_code == 204

        async with sessions() as session:
            assert await session.get(Conversation, conversation_a) is None
    finally:
        await engine.dispose()
