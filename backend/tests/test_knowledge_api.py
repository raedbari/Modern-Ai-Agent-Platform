"""Integration tests for the authenticated Knowledge API."""

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

from backend.app.ai.contracts import EmbeddingResult
from backend.app.api.dependencies import get_embedding_provider
from backend.app.auth.api_keys import IssuedApiKey, issue_api_key
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
    ApiKey,
)
from backend.app.main import create_app
from backend.app.infrastructure.database.repositories import SQLAlchemyChunkRepository


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

    async def embed(request):
        return EmbeddingResult(
            embeddings=[
                [1.0] + [0.0] * 1023
                for _ in request.texts
            ],
            model="test-embedding",
            dimension=1024,
        )

    runtime.embed.side_effect = embed
    application = create_app()

    async def override_get_db():
        async with session_factory() as session:
            yield session

    application.dependency_overrides[get_db] = override_get_db
    application.dependency_overrides[get_embedding_provider] = lambda: runtime
    return application, engine, session_factory, runtime


async def _seed_tenant(
    session_factory: async_sessionmaker,
    *,
    tenant_id: str,
    agent_ids: tuple[str, ...],
) -> IssuedApiKey:
    issued = issue_api_key()
    async with session_factory() as session:
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
            )
        )
        await session.commit()
    return issued


def _headers(issued: IssuedApiKey, agent_id: str) -> dict[str, str]:
    return {
        "X-API-Key": issued.raw_key,
        "X-Agent-ID": agent_id,
    }


async def _create_knowledge_base(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    name: str = "Support",
) -> str:
    response = await client.post(
        "/api/knowledge-bases",
        headers=headers,
        json={"name": name, "description": "Tenant knowledge"},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


@pytest.mark.asyncio
async def test_knowledge_api_requires_authenticated_agent(
    tmp_path: Path,
) -> None:
    app, engine, _, _ = await _open_test_app(
        tmp_path / "knowledge-auth.sqlite3"
    )
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/api/knowledge-bases")
        assert response.status_code == 401
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_create_list_and_update_knowledge_base(
    tmp_path: Path,
) -> None:
    app, engine, session_factory, _ = await _open_test_app(
        tmp_path / "knowledge-crud.sqlite3"
    )
    try:
        issued = await _seed_tenant(
            session_factory,
            tenant_id="tenant-a",
            agent_ids=("agent-a",),
        )
        headers = _headers(issued, "agent-a")
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            knowledge_base_id = await _create_knowledge_base(
                client,
                headers,
            )
            listed = await client.get(
                "/api/knowledge-bases",
                headers=headers,
            )
            updated = await client.patch(
                f"/api/knowledge-bases/{knowledge_base_id}",
                headers=headers,
                json={
                    "name": "Updated Support",
                    "status": "inactive",
                },
            )
            forged_identity = await client.post(
                "/api/knowledge-bases",
                headers=headers,
                json={
                    "name": "Forbidden",
                    "tenant_id": "tenant-b",
                    "agent_id": "agent-b",
                },
            )

        assert listed.status_code == 200
        assert [item["id"] for item in listed.json()] == [
            knowledge_base_id
        ]
        assert updated.status_code == 200
        assert updated.json()["name"] == "Updated Support"
        assert updated.json()["status"] == "inactive"
        assert forged_identity.status_code == 422
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_knowledge_base_is_hidden_from_unassigned_agent_and_tenant(
    tmp_path: Path,
) -> None:
    app, engine, session_factory, _ = await _open_test_app(
        tmp_path / "knowledge-isolation.sqlite3"
    )
    try:
        tenant_a_key = await _seed_tenant(
            session_factory,
            tenant_id="tenant-a",
            agent_ids=("agent-a", "agent-other"),
        )
        tenant_b_key = await _seed_tenant(
            session_factory,
            tenant_id="tenant-b",
            agent_ids=("agent-b",),
        )
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            knowledge_base_id = await _create_knowledge_base(
                client,
                _headers(tenant_a_key, "agent-a"),
            )
            same_tenant = await client.get(
                f"/api/knowledge-bases/{knowledge_base_id}",
                headers=_headers(tenant_a_key, "agent-other"),
            )
            other_tenant = await client.get(
                f"/api/knowledge-bases/{knowledge_base_id}",
                headers=_headers(tenant_b_key, "agent-b"),
            )

        assert same_tenant.status_code == 404
        assert other_tenant.status_code == 404
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_upload_lists_status_and_deduplicates_document(
    tmp_path: Path,
) -> None:
    app, engine, session_factory, runtime = await _open_test_app(
        tmp_path / "knowledge-upload.sqlite3"
    )
    try:
        issued = await _seed_tenant(
            session_factory,
            tenant_id="tenant-a",
            agent_ids=("agent-a",),
        )
        headers = _headers(issued, "agent-a")
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            knowledge_base_id = await _create_knowledge_base(
                client,
                headers,
            )
            first = await client.post(
                f"/api/knowledge-bases/{knowledge_base_id}/documents",
                headers=headers,
                files={
                    "file": (
                        "guide.txt",
                        b"Verified support information.",
                        "text/plain",
                    )
                },
            )
            duplicate = await client.post(
                f"/api/knowledge-bases/{knowledge_base_id}/documents",
                headers=headers,
                files={
                    "file": (
                        "guide.txt",
                        b"Verified support information.",
                        "text/plain",
                    )
                },
            )
            listed = await client.get(
                f"/api/knowledge-bases/{knowledge_base_id}/documents",
                headers=headers,
            )

        assert first.status_code == 201, first.text
        assert first.json()["status"] == "ready"
        assert first.json()["chunks_persisted"] == 1
        assert first.json()["duplicate"] is False
        assert duplicate.status_code == 201
        assert duplicate.json()["id"] == first.json()["id"]
        assert duplicate.json()["duplicate"] is True
        assert len(listed.json()) == 1
        assert runtime.embed.await_count == 1
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_document_job_retains_file_without_blocking_for_embeddings(
    tmp_path: Path,
) -> None:
    app, engine, session_factory, runtime = await _open_test_app(
        tmp_path / "knowledge-job.sqlite3"
    )
    storage_root = tmp_path / "retained"
    settings = Settings(
        upload_storage_root=storage_root,
        _env_file=None,
    )
    app.dependency_overrides[get_settings] = lambda: settings
    content = b"Queued verified support information."
    try:
        issued = await _seed_tenant(
            session_factory,
            tenant_id="tenant-a",
            agent_ids=("agent-a",),
        )
        headers = _headers(issued, "agent-a")
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            knowledge_base_id = await _create_knowledge_base(
                client,
                headers,
            )
            queued = await client.post(
                f"/api/knowledge-bases/{knowledge_base_id}/document-jobs",
                headers=headers,
                files={
                    "file": (
                        "queued.txt",
                        content,
                        "text/plain",
                    )
                },
            )
            job_id = queued.json()["job_id"]
            polled = await client.get(
                (
                    f"/api/knowledge-bases/{knowledge_base_id}/"
                    f"document-jobs/{job_id}"
                ),
                headers=headers,
            )
            duplicate = await client.post(
                f"/api/knowledge-bases/{knowledge_base_id}/document-jobs",
                headers=headers,
                files={
                    "file": (
                        "queued.txt",
                        content,
                        "text/plain",
                    )
                },
            )

        assert queued.status_code == 202, queued.text
        assert queued.json()["status"] == "pending"
        assert queued.json()["document"]["status"] == "pending"
        assert polled.status_code == 200
        assert polled.json()["job_id"] == job_id
        assert duplicate.status_code == 202
        assert duplicate.json()["duplicate"] is True
        assert duplicate.json()["job_id"] is None
        runtime.embed.assert_not_awaited()

        async with session_factory() as session:
            job = await session.get(IngestionJob, job_id)
        assert job is not None
        assert job.source_filename == "queued.txt"
        assert job.source_mime_type == "text/plain"
        assert job.source_name == "upload"
        assert (storage_root / job.storage_key).read_bytes() == content
    finally:
        app.dependency_overrides.pop(get_settings, None)
        await engine.dispose()


@pytest.mark.asyncio
async def test_upload_rejects_extension_mime_mismatch(
    tmp_path: Path,
) -> None:
    app, engine, session_factory, runtime = await _open_test_app(
        tmp_path / "knowledge-file-validation.sqlite3"
    )
    try:
        issued = await _seed_tenant(
            session_factory,
            tenant_id="tenant-a",
            agent_ids=("agent-a",),
        )
        headers = _headers(issued, "agent-a")
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            knowledge_base_id = await _create_knowledge_base(
                client,
                headers,
            )
            response = await client.post(
                f"/api/knowledge-bases/{knowledge_base_id}/documents",
                headers=headers,
                files={
                    "file": (
                        "renamed.pdf",
                        b"not a pdf",
                        "text/plain",
                    )
                },
            )

        assert response.status_code == 422
        runtime.embed.assert_not_awaited()
        async with session_factory() as session:
            count = await session.scalar(
                select(func.count()).select_from(DocumentModel)
            )
        assert count == 0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_embedding_failure_persists_safe_failed_status(
    tmp_path: Path,
) -> None:
    app, engine, session_factory, runtime = await _open_test_app(
        tmp_path / "knowledge-embedding-failure.sqlite3"
    )
    try:
        issued = await _seed_tenant(
            session_factory,
            tenant_id="tenant-a",
            agent_ids=("agent-a",),
        )
        runtime.embed.side_effect = RuntimeError("internal provider detail")
        headers = _headers(issued, "agent-a")
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            knowledge_base_id = await _create_knowledge_base(
                client,
                headers,
            )
            response = await client.post(
                f"/api/knowledge-bases/{knowledge_base_id}/documents",
                headers=headers,
                files={
                    "file": (
                        "guide.txt",
                        b"Verified support information.",
                        "text/plain",
                    )
                },
            )

        assert response.status_code == 502
        assert "internal provider detail" not in response.text
        async with session_factory() as session:
            document = await session.scalar(select(DocumentModel))
        assert document is not None
        assert document.status == "failed"
        assert document.failure_reason == "Document processing failed."
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_reindex_replaces_chunks_and_keeps_document_identity(
    tmp_path: Path,
) -> None:
    app, engine, session_factory, runtime = await _open_test_app(
        tmp_path / "knowledge-reindex.sqlite3"
    )
    try:
        issued = await _seed_tenant(
            session_factory,
            tenant_id="tenant-a",
            agent_ids=("agent-a",),
        )
        headers = _headers(issued, "agent-a")
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            knowledge_base_id = await _create_knowledge_base(
                client,
                headers,
            )
            uploaded = await client.post(
                f"/api/knowledge-bases/{knowledge_base_id}/documents",
                headers=headers,
                files={
                    "file": (
                        "guide.txt",
                        b"Old verified text.",
                        "text/plain",
                    )
                },
            )
            document_id = uploaded.json()["id"]
            reindexed = await client.post(
                (
                    f"/api/knowledge-bases/{knowledge_base_id}/documents/"
                    f"{document_id}/reindex"
                ),
                headers=headers,
                files={
                    "file": (
                        "guide-v2.txt",
                        b"New verified replacement text.",
                        "text/plain",
                    )
                },
            )

        assert reindexed.status_code == 200, reindexed.text
        assert reindexed.json()["id"] == document_id
        assert reindexed.json()["original_filename"] == "guide-v2.txt"
        assert reindexed.json()["status"] == "ready"
        assert runtime.embed.await_count == 2

        async with session_factory() as session:
            chunks = list(
                (
                    await session.scalars(
                        select(ChunkModel).where(
                            ChunkModel.document_id == document_id
                        )
                    )
                ).all()
            )
        assert len(chunks) == 1
        assert chunks[0].content == "New verified replacement text."
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_delete_document_and_knowledge_base_are_cascaded(
    tmp_path: Path,
) -> None:
    app, engine, session_factory, _ = await _open_test_app(
        tmp_path / "knowledge-delete.sqlite3"
    )
    try:
        issued = await _seed_tenant(
            session_factory,
            tenant_id="tenant-a",
            agent_ids=("agent-a",),
        )
        headers = _headers(issued, "agent-a")
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            knowledge_base_id = await _create_knowledge_base(
                client,
                headers,
            )
            uploaded = await client.post(
                f"/api/knowledge-bases/{knowledge_base_id}/documents",
                headers=headers,
                files={
                    "file": (
                        "guide.txt",
                        b"Temporary verified text.",
                        "text/plain",
                    )
                },
            )
            document_id = uploaded.json()["id"]
            deleted_document = await client.delete(
                (
                    f"/api/knowledge-bases/{knowledge_base_id}/documents/"
                    f"{document_id}"
                ),
                headers=headers,
            )
            deleted_knowledge_base = await client.delete(
                f"/api/knowledge-bases/{knowledge_base_id}",
                headers=headers,
            )

        assert deleted_document.status_code == 204
        assert deleted_knowledge_base.status_code == 204
        async with session_factory() as session:
            assert await session.scalar(
                select(func.count()).select_from(DocumentModel)
            ) == 0
            assert await session.scalar(
                select(func.count()).select_from(ChunkModel)
            ) == 0
            assert await session.scalar(
                select(func.count()).select_from(KnowledgeBaseModel)
            ) == 0
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_delete_document_enforces_agent_scope_audits_and_removes_from_rag(
    tmp_path: Path,
) -> None:
    app, engine, session_factory, _ = await _open_test_app(
        tmp_path / "knowledge-delete-scope.sqlite3"
    )

    try:
        issued = await _seed_tenant(
            session_factory,
            tenant_id="tenant-delete",
            agent_ids=("agent-owner", "agent-other"),
        )

        owner_headers = _headers(
            issued,
            "agent-owner",
        )

        other_headers = _headers(
            issued,
            "agent-other",
        )

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            knowledge_base_id = await _create_knowledge_base(
                client,
                owner_headers,
                name="Deletion scope",
            )

            uploaded = await client.post(
                (
                    f"/api/knowledge-bases/{knowledge_base_id}"
                    "/documents"
                ),
                headers=owner_headers,
                files={
                    "file": (
                        "delete-me.txt",
                        b"Active content that must disappear.",
                        "text/plain",
                    )
                },
            )

        assert uploaded.status_code == 201, uploaded.text
        document_id = uploaded.json()["id"]

        # Assign the same KB to another agent. The document itself still
        # belongs only to agent-owner.
        async with session_factory() as session:
            session.add(
                AgentKnowledgeBase(
                    tenant_id="tenant-delete",
                    agent_id="agent-other",
                    knowledge_base_id=knowledge_base_id,
                )
            )
            await session.commit()

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            forbidden = await client.delete(
                (
                    f"/api/knowledge-bases/{knowledge_base_id}"
                    f"/documents/{document_id}"
                ),
                headers=other_headers,
            )

        assert forbidden.status_code == 404

        async with session_factory() as session:
            assert await session.get(
                DocumentModel,
                document_id,
            ) is not None

            forbidden_audits = await session.scalar(
                select(func.count())
                .select_from(AdminAuditLog)
                .where(
                    AdminAuditLog.event_type
                    == "knowledge_document_deleted",
                    AdminAuditLog.target_id == document_id,
                )
            )

        assert forbidden_audits == 0

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            deleted = await client.delete(
                (
                    f"/api/knowledge-bases/{knowledge_base_id}"
                    f"/documents/{document_id}"
                ),
                headers=owner_headers,
            )

        assert deleted.status_code == 204

        async with session_factory() as session:
            assert await session.get(
                DocumentModel,
                document_id,
            ) is None

            chunk_count = await session.scalar(
                select(func.count())
                .select_from(ChunkModel)
                .where(
                    ChunkModel.document_id == document_id
                )
            )

            audit = await session.scalar(
                select(AdminAuditLog).where(
                    AdminAuditLog.event_type
                    == "knowledge_document_deleted",
                    AdminAuditLog.target_id == document_id,
                )
            )

            search_results = await SQLAlchemyChunkRepository(
                session
            ).semantic_search(
                query_embedding=[1.0] + [0.0] * 1023,
                tenant_id="tenant-delete",
                agent_id="agent-owner",
                knowledge_base_id=knowledge_base_id,
                top_k=5,
                min_similarity=0.0,
            )

        assert chunk_count == 0
        assert search_results == []

        assert audit is not None
        assert audit.admin_id is None
        assert audit.target_type == "knowledge_document"
        assert audit.outcome == "success"
        assert audit.detail == {
            "tenant_id": "tenant-delete",
            "agent_id": "agent-owner",
            "knowledge_base_id": knowledge_base_id,
        }

        serialized_detail = str(audit.detail).lower()

        assert "content" not in serialized_detail
        assert "token" not in serialized_detail
        assert "api_key" not in serialized_detail

    finally:
        await engine.dispose()
