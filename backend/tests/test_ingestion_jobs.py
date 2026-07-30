"""Durable source storage and background ingestion tests."""

from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.app.ai.contracts import (
    EmbeddingRequest,
    EmbeddingResult,
)
from backend.app.core.config import Settings
from backend.app.db.base import Base
from backend.app.db.models import (
    Agent,
    AgentKnowledgeBase,
    ChunkModel,
    DocumentModel,
    IngestionJob,
    KnowledgeBaseModel,
    Tenant,
)
from backend.app.infrastructure.storage import LocalUploadStorage
from backend.app.operations.ingestion_runtime import build_ingestion_service
from backend.app.services.knowledge.ingestion_service import IngestionRequest
from backend.app.services.knowledge.job_service import IngestionJobService
from backend.app.workers.ingestion_worker import IngestionWorker


class FixedEmbeddingProvider:
    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        return EmbeddingResult(
            embeddings=[
                [1.0] + [0.0] * 1023 for _ in request.texts
            ],
            model="test-embedding",
            dimension=1024,
        )


async def _database(path: Path):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{path.as_posix()}",
    )

    @event.listens_for(engine.sync_engine, "connect")
    def enable_foreign_keys(connection, _record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


async def _seed_scope(sessions: async_sessionmaker) -> None:
    async with sessions() as session:
        session.add(Tenant(id="tenant-a", name="Tenant A"))
        await session.flush()
        session.add(
            Agent(
                id="agent-a",
                tenant_id="tenant-a",
                name="Agent A",
            )
        )
        session.add(
            KnowledgeBaseModel(
                id="kb-a",
                tenant_id="tenant-a",
                name="Knowledge",
            )
        )
        await session.flush()
        session.add(
            AgentKnowledgeBase(
                tenant_id="tenant-a",
                agent_id="agent-a",
                knowledge_base_id="kb-a",
            )
        )
        await session.commit()


def _settings(storage_root: Path) -> Settings:
    return Settings(
        upload_storage_root=storage_root,
        embedding_dimension=1024,
        _env_file=None,
    )


@pytest.mark.asyncio
async def test_local_upload_storage_is_atomic_and_traversal_safe(
    tmp_path: Path,
) -> None:
    storage = LocalUploadStorage(tmp_path / "uploads")
    key = await storage.store(
        tenant_id="../tenant",
        document_id="../../document",
        content=b"retained source",
    )

    assert ".." not in key
    assert await storage.read(key) == b"retained source"
    with pytest.raises(ValueError, match="Invalid storage key"):
        await storage.read("../outside")
    await storage.delete(key)
    await storage.delete(key)


@pytest.mark.asyncio
async def test_worker_processes_retained_document_end_to_end(
    tmp_path: Path,
) -> None:
    engine, sessions = await _database(tmp_path / "worker.sqlite3")
    await _seed_scope(sessions)
    settings = _settings(tmp_path / "uploads")
    storage = LocalUploadStorage(settings.upload_storage_root)
    request = IngestionRequest(
        content=b"Verified asynchronous support information.",
        filename="support.txt",
        mime_type="text/plain",
        tenant_id="tenant-a",
        agent_id="agent-a",
        knowledge_base_id="kb-a",
        source_name="support-manual",
    )
    try:
        async with sessions() as session:
            service = build_ingestion_service(
                session=session,
                runtime=FixedEmbeddingProvider(),
                settings=settings,
            )
            prepared = await service.prepare(request)
            storage_key = await storage.store(
                tenant_id="tenant-a",
                document_id=prepared.document.id,
                content=request.content,
            )
            job = await IngestionJobService.enqueue(
                session,
                tenant_id="tenant-a",
                agent_id="agent-a",
                knowledge_base_id="kb-a",
                document_id=prepared.document.id,
                storage_key=storage_key,
                max_attempts=3,
            )
            job_id = job.id
            document_id = prepared.document.id
            await session.commit()

        worker = IngestionWorker(
            settings=settings,
            worker_id="worker-test",
            session_factory=sessions,
            embedding_provider=FixedEmbeddingProvider(),
            storage=storage,
        )
        assert await worker.process_one() is True
        assert await worker.process_one() is False

        async with sessions() as session:
            stored_job = await session.get(IngestionJob, job_id)
            document = await session.get(DocumentModel, document_id)
            chunks = list(
                (
                    await session.scalars(
                        select(ChunkModel).where(
                            ChunkModel.document_id == document_id
                        )
                    )
                ).all()
            )

        assert stored_job is not None
        assert stored_job.status == "succeeded"
        assert stored_job.attempts == 1
        assert stored_job.completed_at is not None
        assert document is not None
        assert document.status == "ready"
        assert len(chunks) == 1
        assert chunks[0].content == request.content.decode()
        assert await storage.read(storage_key) == request.content
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_failed_job_retries_then_becomes_terminal(
    tmp_path: Path,
) -> None:
    engine, sessions = await _database(tmp_path / "retry.sqlite3")
    await _seed_scope(sessions)
    settings = _settings(tmp_path / "uploads")
    request = IngestionRequest(
        content=b"Retry source",
        filename="retry.txt",
        mime_type="text/plain",
        tenant_id="tenant-a",
        agent_id="agent-a",
        knowledge_base_id="kb-a",
    )
    try:
        async with sessions() as session:
            prepared = await build_ingestion_service(
                session=session,
                runtime=FixedEmbeddingProvider(),
                settings=settings,
            ).prepare(request)
            job = await IngestionJobService.enqueue(
                session,
                tenant_id="tenant-a",
                agent_id="agent-a",
                knowledge_base_id="kb-a",
                document_id=prepared.document.id,
                storage_key="missing.source",
                max_attempts=2,
            )
            await IngestionJobService.claim_next(
                session,
                worker_id="worker-a",
            )
            await IngestionJobService.mark_failed_or_retry(
                session,
                job,
                safe_error="Safe failure.",
            )
            assert job.status == "pending"
            job.available_at = datetime.now(timezone.utc)
            await session.commit()

        async with sessions() as session:
            claimed = await IngestionJobService.claim_next(
                session,
                worker_id="worker-b",
            )
            assert claimed is not None
            await IngestionJobService.mark_failed_or_retry(
                session,
                claimed,
                safe_error="Safe failure.",
            )
            await session.commit()
            assert claimed.status == "failed"
            assert claimed.attempts == 2
            assert claimed.completed_at is not None
    finally:
        await engine.dispose()
