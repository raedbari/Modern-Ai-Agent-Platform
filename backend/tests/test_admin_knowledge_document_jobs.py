"""Behavioral tests for administrative document queue endpoints."""

from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, func, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)

from backend.app.api.dependencies import (
    get_embedding_provider,
    require_admin_access,
)
from backend.app.core.config import Settings, get_settings
from backend.app.db.base import Base, get_db
from backend.app.db.models import (
    AdminAuditLog,
    Agent,
    AgentKnowledgeBase,
    ChunkModel,
    DocumentModel,
    IngestionJob,
    KnowledgeBaseModel,
    Tenant,
)
from backend.app.infrastructure.storage import LocalUploadStorage
from backend.app.main import create_app


OLD_CONTENT = b"Old active knowledge."
NEW_CONTENT = b"New queued replacement knowledge."


class NoEmbeddingProvider:
    """Fail the test if an HTTP queue request invokes embeddings."""

    def __init__(self) -> None:
        self.calls = 0

    async def embed(self, request):
        self.calls += 1
        raise AssertionError(
            "Queue endpoints must not invoke embeddings."
        )


async def _open_test_app(
    database_path: Path,
    storage_root: Path,
) -> tuple[
    FastAPI,
    AsyncEngine,
    async_sessionmaker,
    NoEmbeddingProvider,
]:
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
    provider = NoEmbeddingProvider()
    settings = Settings(
        upload_storage_root=storage_root,
        embedding_dimension=1024,
        _env_file=None,
    )

    async def override_get_db():
        async with sessions() as session:
            yield session

    admin_context = SimpleNamespace(
        admin_id="admin-test",
        username="tester",
        role="super_admin",
        auth_method="legacy",
    )

    application.dependency_overrides[get_db] = override_get_db
    application.dependency_overrides[get_settings] = lambda: settings
    application.dependency_overrides[get_embedding_provider] = lambda: provider
    application.dependency_overrides[require_admin_access] = lambda: admin_context

    return application, engine, sessions, provider


async def _seed_scope(
    sessions: async_sessionmaker,
    *,
    include_ready_document: bool = False,
) -> None:
    async with sessions() as session:
        session.add_all(
            [
                Tenant(id="tenant-a", name="Tenant A"),
                Tenant(id="tenant-b", name="Tenant B"),
            ]
        )
        await session.flush()

        session.add_all(
            [
                Agent(id="agent-a", tenant_id="tenant-a", name="Agent A"),
                Agent(
                    id="agent-unassigned",
                    tenant_id="tenant-a",
                    name="Unassigned Agent",
                ),
                Agent(id="agent-b", tenant_id="tenant-b", name="Agent B"),
            ]
        )
        await session.flush()

        session.add_all(
            [
                KnowledgeBaseModel(
                    id="kb-a",
                    tenant_id="tenant-a",
                    name="Knowledge A",
                    description="",
                ),
                KnowledgeBaseModel(
                    id="kb-b",
                    tenant_id="tenant-b",
                    name="Knowledge B",
                    description="",
                ),
            ]
        )
        await session.flush()

        session.add_all(
            [
                AgentKnowledgeBase(
                    tenant_id="tenant-a",
                    agent_id="agent-a",
                    knowledge_base_id="kb-a",
                ),
                AgentKnowledgeBase(
                    tenant_id="tenant-b",
                    agent_id="agent-b",
                    knowledge_base_id="kb-b",
                ),
            ]
        )
        await session.flush()

        if include_ready_document:
            session.add(
                DocumentModel(
                    id="document-a",
                    tenant_id="tenant-a",
                    agent_id="agent-a",
                    knowledge_base_id="kb-a",
                    source_name="old-source",
                    original_filename="old.txt",
                    mime_type="text/plain",
                    file_size_bytes=len(OLD_CONTENT),
                    content_hash=hashlib.sha256(OLD_CONTENT).hexdigest(),
                    status="ready",
                    failure_reason=None,
                )
            )
            await session.flush()
            session.add(
                ChunkModel(
                    id="chunk-old",
                    tenant_id="tenant-a",
                    agent_id="agent-a",
                    knowledge_base_id="kb-a",
                    document_id="document-a",
                    source_name="old-source",
                    page_number=0,
                    chunk_index=0,
                    content=OLD_CONTENT.decode(),
                    content_hash=hashlib.sha256(OLD_CONTENT).hexdigest(),
                    embedding=[1.0] + [0.0] * 1023,
                )
            )

        await session.commit()


@pytest.mark.asyncio
async def test_admin_upload_queues_source_job_and_audit_without_embeddings(
    tmp_path: Path,
) -> None:
    storage_root = tmp_path / "uploads"
    app, engine, sessions, provider = await _open_test_app(
        tmp_path / "admin-upload.sqlite3",
        storage_root,
    )
    await _seed_scope(sessions)
    content = b"Verified admin upload content."

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/admin/tenants/tenant-a/knowledge-bases/kb-a/documents",
                data={"agent_id": "agent-a", "source_name": "admin-manual"},
                files={"file": ("manual.txt", content, "text/plain")},
            )

        assert response.status_code == 202, response.text
        body = response.json()
        assert body["duplicate"] is False
        assert body["document_status"] == "pending"
        assert body["job"]["status"] == "pending"
        assert provider.calls == 0

        document_id = body["document_id"]
        job_id = body["job"]["id"]
        async with sessions() as session:
            document = await session.get(DocumentModel, document_id)
            job = await session.get(IngestionJob, job_id)
            audit = await session.scalar(
                select(AdminAuditLog).where(
                    AdminAuditLog.event_type == "knowledge_document_upload_queued",
                    AdminAuditLog.target_id == document_id,
                )
            )

        assert document is not None
        assert document.tenant_id == "tenant-a"
        assert document.agent_id == "agent-a"
        assert document.knowledge_base_id == "kb-a"
        assert document.status == "pending"

        assert job is not None
        assert job.document_id == document_id
        assert job.source_filename == "manual.txt"
        assert job.source_mime_type == "text/plain"
        assert job.source_name == "admin-manual"
        assert await LocalUploadStorage(storage_root).read(job.storage_key) == content

        assert audit is not None
        assert audit.admin_id == "admin-test"
        assert audit.outcome == "success"
        assert audit.detail["tenant_id"] == "tenant-a"
        assert audit.detail["agent_id"] == "agent-a"
        assert audit.detail["knowledge_base_id"] == "kb-a"
        assert audit.detail["job_id"] == job_id
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_admin_upload_enforces_assignment_and_tenant_isolation(
    tmp_path: Path,
) -> None:
    storage_root = tmp_path / "uploads"
    app, engine, sessions, provider = await _open_test_app(
        tmp_path / "admin-upload-isolation.sqlite3",
        storage_root,
    )
    await _seed_scope(sessions)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            unassigned = await client.post(
                "/api/admin/tenants/tenant-a/knowledge-bases/kb-a/documents",
                data={"agent_id": "agent-unassigned"},
                files={"file": ("unassigned.txt", b"Unassigned.", "text/plain")},
            )
            cross_tenant_agent = await client.post(
                "/api/admin/tenants/tenant-a/knowledge-bases/kb-a/documents",
                data={"agent_id": "agent-b"},
                files={"file": ("cross.txt", b"Cross tenant.", "text/plain")},
            )
            cross_tenant_kb = await client.post(
                "/api/admin/tenants/tenant-a/knowledge-bases/kb-b/documents",
                data={"agent_id": "agent-a"},
                files={"file": ("cross-kb.txt", b"Cross KB.", "text/plain")},
            )

        assert unassigned.status_code == 404
        assert cross_tenant_agent.status_code == 404
        assert cross_tenant_kb.status_code == 404
        assert provider.calls == 0

        async with sessions() as session:
            document_count = await session.scalar(
                select(func.count()).select_from(DocumentModel)
            )
            job_count = await session.scalar(
                select(func.count()).select_from(IngestionJob)
            )
        assert document_count == 0
        assert job_count == 0
        assert list(storage_root.rglob("*.source")) == []
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_admin_replacement_preserves_active_document_and_blocks_second_job(
    tmp_path: Path,
) -> None:
    storage_root = tmp_path / "uploads"
    app, engine, sessions, provider = await _open_test_app(
        tmp_path / "admin-replacement.sqlite3",
        storage_root,
    )
    await _seed_scope(sessions, include_ready_document=True)
    replacement_url = (
        "/api/admin/tenants/tenant-a/knowledge-bases/kb-a/"
        "documents/document-a/replace"
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            queued = await client.post(
                replacement_url,
                data={"source_name": "replacement-source"},
                files={"file": ("replacement.md", NEW_CONTENT, "text/markdown")},
            )
            conflict = await client.post(
                replacement_url,
                data={"source_name": "second-source"},
                files={"file": ("second.txt", b"Second replacement.", "text/plain")},
            )
            cross_tenant = await client.post(
                "/api/admin/tenants/tenant-b/knowledge-bases/kb-b/"
                "documents/document-a/replace",
                files={"file": ("cross.txt", b"Cross replacement.", "text/plain")},
            )

        assert queued.status_code == 202, queued.text
        assert queued.json()["document_id"] == "document-a"
        assert queued.json()["document_status"] == "ready"
        assert queued.json()["job"]["status"] == "pending"
        assert conflict.status_code == 409
        assert cross_tenant.status_code == 404
        assert provider.calls == 0

        job_id = queued.json()["job"]["id"]
        async with sessions() as session:
            document = await session.get(DocumentModel, "document-a")
            old_chunk = await session.get(ChunkModel, "chunk-old")
            job = await session.get(IngestionJob, job_id)
            active_job_count = await session.scalar(
                select(func.count())
                .select_from(IngestionJob)
                .where(
                    IngestionJob.tenant_id == "tenant-a",
                    IngestionJob.document_id == "document-a",
                    IngestionJob.status.in_(("pending", "processing")),
                )
            )
            audit = await session.scalar(
                select(AdminAuditLog).where(
                    AdminAuditLog.event_type
                    == "knowledge_document_replacement_queued",
                    AdminAuditLog.target_id == "document-a",
                )
            )

        assert document is not None
        assert document.status == "ready"
        assert document.original_filename == "old.txt"
        assert document.mime_type == "text/plain"
        assert document.source_name == "old-source"
        assert document.content_hash == hashlib.sha256(OLD_CONTENT).hexdigest()
        assert old_chunk is not None
        assert old_chunk.content == OLD_CONTENT.decode()
        assert active_job_count == 1

        assert job is not None
        assert job.source_filename == "replacement.md"
        assert job.source_mime_type == "text/markdown"
        assert job.source_name == "replacement-source"
        assert await LocalUploadStorage(storage_root).read(job.storage_key) == NEW_CONTENT
        assert len(list(storage_root.rglob("*.source"))) == 1

        assert audit is not None
        assert audit.admin_id == "admin-test"
        assert audit.detail["job_id"] == job_id
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_admin_duplicate_upload_reuses_document_without_job_or_storage(
    tmp_path: Path,
) -> None:
    storage_root = tmp_path / "uploads"
    app, engine, sessions, provider = await _open_test_app(
        tmp_path / "admin-duplicate.sqlite3",
        storage_root,
    )
    await _seed_scope(sessions, include_ready_document=True)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/admin/tenants/tenant-a/knowledge-bases/kb-a/documents",
                data={"agent_id": "agent-a"},
                files={"file": ("duplicate.txt", OLD_CONTENT, "text/plain")},
            )

        assert response.status_code == 202, response.text
        assert response.json()["duplicate"] is True
        assert response.json()["document_id"] == "document-a"
        assert response.json()["document_status"] == "ready"
        assert response.json()["job"] is None
        assert provider.calls == 0

        async with sessions() as session:
            document_count = await session.scalar(
                select(func.count()).select_from(DocumentModel)
            )
            job_count = await session.scalar(
                select(func.count()).select_from(IngestionJob)
            )
            audit_count = await session.scalar(
                select(func.count())
                .select_from(AdminAuditLog)
                .where(
                    AdminAuditLog.event_type
                    == "knowledge_document_upload_queued"
                )
            )
        assert document_count == 1
        assert job_count == 0
        assert audit_count == 0
        assert list(storage_root.rglob("*.source")) == []
    finally:
        await engine.dispose()
