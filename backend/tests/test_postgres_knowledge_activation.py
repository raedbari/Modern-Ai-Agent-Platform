"""Real PostgreSQL and pgvector integration tests.

These tests must run only against the isolated maap_review_test database.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
import pytest_asyncio

from backend.app.ai.contracts import (
    EmbeddingRequest,
    EmbeddingResult,
)
from backend.app.core.config import Settings
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

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
from backend.app.services.knowledge.job_service import IngestionJobService
from backend.app.workers.ingestion_worker import IngestionWorker
from backend.app.infrastructure.database.repositories.sqlalchemy_repositories import (
    SQLAlchemyChunkRepository,
    SQLAlchemyKnowledgeBaseRepository,
)
from backend.app.services.knowledge.retrieval_service import RetrievalService
from backend.app.domain.ports.retrieval import RetrievalQuery
from backend.app.domain.exceptions import RetrievalValidationError


TEST_DATABASE_URL = os.getenv("MAAP_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="MAAP_TEST_DATABASE_URL is required.",
)


def _vector(
    first: float,
    second: float = 0.0,
) -> list[float]:
    return [first, second] + [0.0] * 1022


@pytest_asyncio.fixture
async def postgres_context() -> AsyncIterator[
    tuple[
        str,
        async_sessionmaker[AsyncSession],
    ]
]:
    assert TEST_DATABASE_URL is not None

    engine = create_async_engine(
        TEST_DATABASE_URL,
        pool_pre_ping=True,
    )

    sessions = async_sessionmaker(
        engine,
        expire_on_commit=False,
    )

    prefix = f"pg-review-{uuid4().hex[:12]}"

    try:
        yield prefix, sessions
    finally:
        async with sessions() as session:
            await session.execute(
                delete(AdminAuditLog).where(
                    AdminAuditLog.target_id.like(
                        f"{prefix}%"
                    )
                )
            )

            await session.execute(
                delete(Tenant).where(
                    Tenant.id.like(f"{prefix}%")
                )
            )
            await session.commit()

        await engine.dispose()


async def _seed_scope(
    session: AsyncSession,
    *,
    tenant_id: str,
    agent_ids: list[str],
    knowledge_base_ids: list[str],
    assignments: list[tuple[str, str]],
) -> None:
    session.add(
        Tenant(
            id=tenant_id,
            name=tenant_id,
        )
    )
    await session.flush()

    session.add_all(
        [
            Agent(
                id=agent_id,
                tenant_id=tenant_id,
                name=agent_id,
            )
            for agent_id in agent_ids
        ]
    )

    session.add_all(
        [
            KnowledgeBaseModel(
                id=knowledge_base_id,
                tenant_id=tenant_id,
                name=knowledge_base_id,
                status="active",
            )
            for knowledge_base_id in knowledge_base_ids
        ]
    )

    await session.flush()

    session.add_all(
        [
            AgentKnowledgeBase(
                tenant_id=tenant_id,
                agent_id=agent_id,
                knowledge_base_id=knowledge_base_id,
            )
            for agent_id, knowledge_base_id in assignments
        ]
    )

    await session.flush()


async def _add_document_and_chunk(
    session: AsyncSession,
    *,
    suffix: str,
    tenant_id: str,
    document_agent_id: str,
    chunk_agent_id: str,
    knowledge_base_id: str,
    status: str,
    embedding: list[float],
) -> tuple[str, str]:
    document_id = f"{suffix}-document"
    chunk_id = f"{suffix}-chunk"

    session.add(
        DocumentModel(
            id=document_id,
            tenant_id=tenant_id,
            agent_id=document_agent_id,
            knowledge_base_id=knowledge_base_id,
            source_name=f"{suffix}-source",
            original_filename=f"{suffix}.txt",
            mime_type="text/plain",
            file_size_bytes=100,
            content_hash=(
                suffix.encode("utf-8").hex()[:60].ljust(60, "0")
                + "abcd"
            )[:64],
            status=status,
            failure_reason=None,
        )
    )

    # PostgreSQL must see the parent document before the composite FK
    # on chunks is checked.
    await session.flush()

    session.add(
        ChunkModel(
            id=chunk_id,
            tenant_id=tenant_id,
            agent_id=chunk_agent_id,
            knowledge_base_id=knowledge_base_id,
            document_id=document_id,
            source_name=f"{suffix}-source",
            page_number=0,
            chunk_index=0,
            content=f"Content for {suffix}",
            content_hash=(
                ("chunk-" + suffix).encode("utf-8").hex()[:64]
            ).ljust(64, "0"),
            embedding=embedding,
        )
    )

    return document_id, chunk_id


@pytest.mark.asyncio
async def test_postgres_pgvector_returns_only_ready_scoped_chunks(
    postgres_context,
) -> None:
    prefix, sessions = postgres_context

    tenant_a = f"{prefix}-tenant-a"
    tenant_b = f"{prefix}-tenant-b"

    agent_a = f"{prefix}-agent-a"
    agent_a2 = f"{prefix}-agent-a2"
    agent_b = f"{prefix}-agent-b"

    kb_a = f"{prefix}-kb-a"
    kb_a2 = f"{prefix}-kb-a2"
    kb_b = f"{prefix}-kb-b"

    expected_best = f"{prefix}-ready-best-chunk"
    expected_second = f"{prefix}-ready-second-chunk"

    async with sessions() as session:
        await _seed_scope(
            session,
            tenant_id=tenant_a,
            agent_ids=[agent_a, agent_a2],
            knowledge_base_ids=[kb_a, kb_a2],
            assignments=[
                (agent_a, kb_a),
                (agent_a, kb_a2),
                (agent_a2, kb_a),
            ],
        )

        await _seed_scope(
            session,
            tenant_id=tenant_b,
            agent_ids=[agent_b],
            knowledge_base_ids=[kb_b],
            assignments=[(agent_b, kb_b)],
        )

        await _add_document_and_chunk(
            session,
            suffix=f"{prefix}-ready-best",
            tenant_id=tenant_a,
            document_agent_id=agent_a,
            chunk_agent_id=agent_a,
            knowledge_base_id=kb_a,
            status="ready",
            embedding=_vector(1.0, 0.0),
        )

        await _add_document_and_chunk(
            session,
            suffix=f"{prefix}-ready-second",
            tenant_id=tenant_a,
            document_agent_id=agent_a,
            chunk_agent_id=agent_a,
            knowledge_base_id=kb_a,
            status="ready",
            embedding=_vector(0.8, 0.6),
        )

        await _add_document_and_chunk(
            session,
            suffix=f"{prefix}-processing",
            tenant_id=tenant_a,
            document_agent_id=agent_a,
            chunk_agent_id=agent_a,
            knowledge_base_id=kb_a,
            status="processing",
            embedding=_vector(1.0, 0.0),
        )

        await _add_document_and_chunk(
            session,
            suffix=f"{prefix}-failed",
            tenant_id=tenant_a,
            document_agent_id=agent_a,
            chunk_agent_id=agent_a,
            knowledge_base_id=kb_a,
            status="failed",
            embedding=_vector(1.0, 0.0),
        )

        # Document and chunk agents intentionally disagree.
        await _add_document_and_chunk(
            session,
            suffix=f"{prefix}-mismatched-document-agent",
            tenant_id=tenant_a,
            document_agent_id=agent_a2,
            chunk_agent_id=agent_a,
            knowledge_base_id=kb_a,
            status="ready",
            embedding=_vector(1.0, 0.0),
        )

        await _add_document_and_chunk(
            session,
            suffix=f"{prefix}-wrong-agent",
            tenant_id=tenant_a,
            document_agent_id=agent_a2,
            chunk_agent_id=agent_a2,
            knowledge_base_id=kb_a,
            status="ready",
            embedding=_vector(1.0, 0.0),
        )

        await _add_document_and_chunk(
            session,
            suffix=f"{prefix}-wrong-kb",
            tenant_id=tenant_a,
            document_agent_id=agent_a,
            chunk_agent_id=agent_a,
            knowledge_base_id=kb_a2,
            status="ready",
            embedding=_vector(1.0, 0.0),
        )

        await _add_document_and_chunk(
            session,
            suffix=f"{prefix}-wrong-tenant",
            tenant_id=tenant_b,
            document_agent_id=agent_b,
            chunk_agent_id=agent_b,
            knowledge_base_id=kb_b,
            status="ready",
            embedding=_vector(1.0, 0.0),
        )

        await session.commit()

    async with sessions() as session:
        repository = SQLAlchemyChunkRepository(session)

        results = await repository.semantic_search(
            query_embedding=_vector(1.0, 0.0),
            tenant_id=tenant_a,
            agent_id=agent_a,
            knowledge_base_id=kb_a,
            top_k=10,
            min_similarity=0.5,
        )

    result_ids = [chunk.id for chunk, _ in results]

    assert set(result_ids) == {
        expected_best,
        expected_second,
        f"{prefix}-mismatched-document-agent-chunk",
        f"{prefix}-wrong-agent-chunk",
    }
    assert all(chunk.tenant_id == tenant_a and chunk.knowledge_base_id == kb_a for chunk, _ in results)


@pytest.mark.asyncio
async def test_postgres_rollback_restores_old_active_chunks(
    postgres_context,
) -> None:
    prefix, sessions = postgres_context

    tenant_id = f"{prefix}-tenant"
    agent_id = f"{prefix}-agent"
    knowledge_base_id = f"{prefix}-kb"
    document_id = f"{prefix}-document-v1"
    old_chunk_id = f"{prefix}-old-chunk"
    new_chunk_id = f"{prefix}-new-chunk"

    async with sessions() as session:
        await _seed_scope(
            session,
            tenant_id=tenant_id,
            agent_ids=[agent_id],
            knowledge_base_ids=[knowledge_base_id],
            assignments=[(agent_id, knowledge_base_id)],
        )

        session.add(
            DocumentModel(
                id=document_id,
                tenant_id=tenant_id,
                agent_id=agent_id,
                knowledge_base_id=knowledge_base_id,
                source_name="old-source",
                original_filename="old.txt",
                mime_type="text/plain",
                file_size_bytes=10,
                content_hash="a" * 64,
                status="ready",
                failure_reason=None,
            )
        )

        await session.flush()

        session.add(
            ChunkModel(
                id=old_chunk_id,
                tenant_id=tenant_id,
                agent_id=agent_id,
                knowledge_base_id=knowledge_base_id,
                document_id=document_id,
                source_name="old-source",
                page_number=0,
                chunk_index=0,
                content="Old active content",
                content_hash="b" * 64,
                embedding=_vector(1.0),
            )
        )

        await session.commit()

    with pytest.raises(
        RuntimeError,
        match="forced PostgreSQL rollback",
    ):
        async with sessions() as session:
            async with session.begin():
                repository = SQLAlchemyChunkRepository(session)

                await repository.delete_by_document(
                    document_id=document_id,
                    tenant_id=tenant_id,
                )

                session.add(
                    ChunkModel(
                        id=new_chunk_id,
                        tenant_id=tenant_id,
                        agent_id=agent_id,
                        knowledge_base_id=knowledge_base_id,
                        document_id=document_id,
                        source_name="new-source",
                        page_number=0,
                        chunk_index=0,
                        content="New replacement content",
                        content_hash="c" * 64,
                        embedding=_vector(0.8, 0.6),
                    )
                )

                document = await session.get(
                    DocumentModel,
                    document_id,
                )

                assert document is not None

                document.source_name = "new-source"
                document.original_filename = "new.txt"
                document.content_hash = "d" * 64
                document.status = "ready"

                await session.flush()

                raise RuntimeError(
                    "forced PostgreSQL rollback"
                )

    async with sessions() as session:
        document = await session.get(
            DocumentModel,
            document_id,
        )

        chunks = list(
            (
                await session.scalars(
                    select(ChunkModel)
                    .where(
                        ChunkModel.tenant_id == tenant_id,
                        ChunkModel.document_id == document_id,
                    )
                    .order_by(ChunkModel.id)
                )
            ).all()
        )

    assert document is not None
    assert document.original_filename == "old.txt"
    assert document.source_name == "old-source"
    assert document.content_hash == "a" * 64
    assert document.status == "ready"

    assert [chunk.id for chunk in chunks] == [
        old_chunk_id
    ]


@pytest.mark.asyncio
async def test_postgres_successful_swap_exposes_only_new_chunks(
    postgres_context,
) -> None:
    prefix, sessions = postgres_context

    tenant_id = f"{prefix}-tenant"
    agent_id = f"{prefix}-agent"
    knowledge_base_id = f"{prefix}-kb"
    document_id = f"{prefix}-document"
    old_chunk_id = f"{prefix}-old-chunk"
    new_chunk_id = f"{prefix}-new-chunk"

    async with sessions() as session:
        await _seed_scope(
            session,
            tenant_id=tenant_id,
            agent_ids=[agent_id],
            knowledge_base_ids=[knowledge_base_id],
            assignments=[(agent_id, knowledge_base_id)],
        )

        session.add(
            DocumentModel(
                id=document_id,
                tenant_id=tenant_id,
                agent_id=agent_id,
                knowledge_base_id=knowledge_base_id,
                source_name="old-source",
                original_filename="old.txt",
                mime_type="text/plain",
                file_size_bytes=10,
                content_hash="e" * 64,
                status="ready",
                failure_reason=None,
            )
        )

        await session.flush()

        session.add(
            ChunkModel(
                id=old_chunk_id,
                tenant_id=tenant_id,
                agent_id=agent_id,
                knowledge_base_id=knowledge_base_id,
                document_id=document_id,
                source_name="old-source",
                page_number=0,
                chunk_index=0,
                content="Old active content",
                content_hash="f" * 64,
                embedding=_vector(1.0),
            )
        )

        await session.commit()

    async with sessions() as session:
        async with session.begin():
            repository = SQLAlchemyChunkRepository(session)

            await repository.delete_by_document(
                document_id=document_id,
                tenant_id=tenant_id,
            )

            session.add(
                ChunkModel(
                    id=new_chunk_id,
                    tenant_id=tenant_id,
                    agent_id=agent_id,
                    knowledge_base_id=knowledge_base_id,
                    document_id=document_id,
                    source_name="new-source",
                    page_number=0,
                    chunk_index=0,
                    content="New active content",
                    content_hash="1" * 64,
                    embedding=_vector(1.0),
                )
            )

            document = await session.get(
                DocumentModel,
                document_id,
            )

            assert document is not None

            document.source_name = "new-source"
            document.original_filename = "new.txt"
            document.content_hash = "2" * 64
            document.status = "ready"

    async with sessions() as session:
        chunks = list(
            (
                await session.scalars(
                    select(ChunkModel).where(
                        ChunkModel.tenant_id == tenant_id,
                        ChunkModel.document_id == document_id,
                    )
                )
            ).all()
        )

        document = await session.get(
            DocumentModel,
            document_id,
        )

    assert document is not None
    assert document.original_filename == "new.txt"
    assert document.status == "ready"

    assert [chunk.id for chunk in chunks] == [
        new_chunk_id
    ]


class TransactionObservingEmbeddingProvider:
    """Inspect PostgreSQL while the external embedding call is running."""

    def __init__(
        self,
        *,
        observer_sessions: async_sessionmaker[AsyncSession],
        worker_application_name: str,
    ) -> None:
        self._observer_sessions = observer_sessions
        self._worker_application_name = worker_application_name
        self.calls = 0
        self.observations: list[tuple[str, bool]] = []

    async def embed(
        self,
        request: EmbeddingRequest,
    ) -> EmbeddingResult:
        self.calls += 1

        async with self._observer_sessions() as session:
            rows = (
                await session.execute(
                    text(
                        """
                        SELECT
                            state,
                            xact_start IS NOT NULL AS has_transaction
                        FROM pg_stat_activity
                        WHERE datname = current_database()
                          AND application_name = :application_name
                        ORDER BY pid
                        """
                    ),
                    {
                        "application_name":
                            self._worker_application_name,
                    },
                )
            ).all()

            await session.rollback()

        self.observations.extend(
            (str(state), bool(has_transaction))
            for state, has_transaction in rows
        )

        return EmbeddingResult(
            embeddings=[
                [1.0] + [0.0] * 1023
                for _ in request.texts
            ],
            model="transaction-observer",
            dimension=1024,
        )


@pytest.mark.asyncio
async def test_postgres_worker_has_no_transaction_during_embeddings(
    postgres_context,
    tmp_path: Path,
) -> None:
    assert TEST_DATABASE_URL is not None

    prefix, observer_sessions = postgres_context

    worker_application_name = (
        f"maap-ingestion-test-{uuid4().hex[:10]}"
    )

    worker_engine = create_async_engine(
        TEST_DATABASE_URL,
        pool_pre_ping=True,
        connect_args={
            "server_settings": {
                "application_name": worker_application_name,
            }
        },
    )

    worker_sessions = async_sessionmaker(
        worker_engine,
        expire_on_commit=False,
    )

    tenant_id = f"{prefix}-tenant"
    agent_id = f"{prefix}-agent"
    knowledge_base_id = f"{prefix}-kb"
    document_id = f"{prefix}-document"

    content = (
        b"PostgreSQL transaction boundary verification content. "
        * 10
    )

    settings = Settings(
        upload_storage_root=tmp_path / "uploads",
        embedding_dimension=1024,
        _env_file=None,
    )

    storage = LocalUploadStorage(
        settings.upload_storage_root
    )

    storage_key = await storage.store(
        tenant_id=tenant_id,
        document_id=document_id,
        content=content,
    )

    provider = TransactionObservingEmbeddingProvider(
        observer_sessions=observer_sessions,
        worker_application_name=worker_application_name,
    )

    try:
        async with worker_sessions() as session:
            await _seed_scope(
                session,
                tenant_id=tenant_id,
                agent_ids=[agent_id],
                knowledge_base_ids=[knowledge_base_id],
                assignments=[
                    (agent_id, knowledge_base_id),
                ],
            )

            session.add(
                DocumentModel(
                    id=document_id,
                    tenant_id=tenant_id,
                    agent_id=agent_id,
                    knowledge_base_id=knowledge_base_id,
                    source_name="transaction-test",
                    original_filename="transaction-test.txt",
                    mime_type="text/plain",
                    file_size_bytes=len(content),
                    content_hash="9" * 64,
                    status="pending",
                    failure_reason=None,
                )
            )

            await session.flush()

            job = await IngestionJobService.enqueue(
                session,
                tenant_id=tenant_id,
                agent_id=agent_id,
                knowledge_base_id=knowledge_base_id,
                document_id=document_id,
                storage_key=storage_key,
                max_attempts=1,
            )

            job_id = job.id
            await session.commit()

        worker = IngestionWorker(
            settings=settings,
            worker_id="postgres-transaction-worker",
            session_factory=worker_sessions,
            embedding_provider=provider,
            storage=storage,
        )

        assert await worker.process_one() is True

        assert provider.calls >= 1

        unsafe_observations = [
            (state, has_transaction)
            for state, has_transaction in provider.observations
            if (
                state == "idle in transaction"
                or has_transaction
            )
        ]

        assert unsafe_observations == []

        async with worker_sessions() as session:
            stored_job = await session.get(
                IngestionJob,
                job_id,
            )
            stored_document = await session.get(
                DocumentModel,
                document_id,
            )

        assert stored_job is not None
        assert stored_job.status == "succeeded"

        assert stored_document is not None
        assert stored_document.status == "ready"

    finally:
        await worker_engine.dispose()


class FailOnceEmbeddingProvider:
    def __init__(self) -> None:
        self.calls = 0

    async def embed(
        self,
        request: EmbeddingRequest,
    ) -> EmbeddingResult:
        self.calls += 1

        if self.calls == 1:
            raise RuntimeError(
                "temporary embedding provider failure"
            )

        return EmbeddingResult(
            embeddings=[
                [1.0] + [0.0] * 1023
                for _ in request.texts
            ],
            model="retry-test-model",
            dimension=1024,
        )


class AlwaysFailEmbeddingProvider:
    async def embed(
        self,
        request: EmbeddingRequest,
    ) -> EmbeddingResult:
        raise RuntimeError(
            "permanent embedding provider failure"
        )


@pytest.mark.asyncio
async def test_postgres_retry_is_idempotent_and_audits_activation(
    postgres_context,
    tmp_path: Path,
) -> None:
    prefix, sessions = postgres_context

    tenant_id = f"{prefix}-tenant"
    agent_id = f"{prefix}-agent"
    knowledge_base_id = f"{prefix}-kb"
    document_id = f"{prefix}-document"

    content = b"Retried knowledge must create one active chunk."

    settings = Settings(
        upload_storage_root=tmp_path / "uploads",
        embedding_dimension=1024,
        _env_file=None,
    )

    storage = LocalUploadStorage(
        settings.upload_storage_root
    )

    storage_key = await storage.store(
        tenant_id=tenant_id,
        document_id=document_id,
        content=content,
    )

    provider = FailOnceEmbeddingProvider()

    async with sessions() as session:
        await _seed_scope(
            session,
            tenant_id=tenant_id,
            agent_ids=[agent_id],
            knowledge_base_ids=[knowledge_base_id],
            assignments=[
                (agent_id, knowledge_base_id),
            ],
        )

        session.add(
            DocumentModel(
                id=document_id,
                tenant_id=tenant_id,
                agent_id=agent_id,
                knowledge_base_id=knowledge_base_id,
                source_name="retry-source",
                original_filename="retry.txt",
                mime_type="text/plain",
                file_size_bytes=len(content),
                content_hash="7" * 64,
                status="pending",
                failure_reason=None,
                version_family_id=document_id,
            )
        )

        await session.flush()

        job = await IngestionJobService.enqueue(
            session,
            tenant_id=tenant_id,
            agent_id=agent_id,
            knowledge_base_id=knowledge_base_id,
            document_id=document_id,
            storage_key=storage_key,
            max_attempts=3,
        )

        job_id = job.id
        await session.commit()

    worker = IngestionWorker(
        settings=settings,
        worker_id="postgres-retry-worker",
        session_factory=sessions,
        embedding_provider=provider,
        storage=storage,
    )

    assert await worker.process_one() is True

    async with sessions() as session:
        first_job = await session.get(
            IngestionJob,
            job_id,
        )
        first_document = await session.get(
            DocumentModel,
            document_id,
        )

        first_chunks = list(
            (
                await session.scalars(
                    select(ChunkModel).where(
                        ChunkModel.document_id == document_id
                    )
                )
            ).all()
        )

        first_audits = list(
            (
                await session.scalars(
                    select(AdminAuditLog).where(
                        AdminAuditLog.target_id == document_id
                    )
                )
            ).all()
        )

        assert first_job is not None
        assert first_job.status == "pending"
        assert first_job.attempts == 1

        assert first_document is not None
        assert first_document.status == "pending"

        assert first_chunks == []
        assert first_audits == []

        first_job.available_at = (
            datetime.now(timezone.utc)
            - timedelta(seconds=1)
        )

        await session.commit()

    assert await worker.process_one() is True
    assert provider.calls == 2

    async with sessions() as session:
        stored_job = await session.get(
            IngestionJob,
            job_id,
        )
        stored_document = await session.get(DocumentModel, document_id)

        chunks = list(
            (
                await session.scalars(
                    select(ChunkModel)
                    .where(
                        ChunkModel.document_id == document_id
                    )
                    .order_by(ChunkModel.chunk_index)
                )
            ).all()
        )

        audits = list(
            (
                await session.scalars(
                    select(AdminAuditLog)
                    .where(
                        AdminAuditLog.target_id == document_id
                    )
                    .order_by(AdminAuditLog.id)
                )
            ).all()
        )

    assert stored_job is not None
    assert stored_job.status == "succeeded"
    assert stored_job.attempts == 2

    assert stored_document is not None
    assert stored_document.status == "ready"
    assert stored_document.failure_reason is None

    assert len(chunks) == 1
    assert len({chunk.id for chunk in chunks}) == 1
    assert chunks[0].content == content.decode()

    assert len(audits) == 1

    audit = audits[0]

    assert audit.event_type == (
        "knowledge_document_activated"
    )
    assert audit.outcome == "success"
    assert audit.target_type == "knowledge_document"
    assert audit.admin_id is None
    assert audit.detail == {
        "tenant_id": tenant_id,
        "agent_id": agent_id,
        "knowledge_base_id": knowledge_base_id,
        "job_id": job_id,
        "chunks_persisted": 1,
    }


@pytest.mark.asyncio
async def test_postgres_terminal_failure_is_safely_audited(
    postgres_context,
    tmp_path: Path,
) -> None:
    prefix, sessions = postgres_context

    tenant_id = f"{prefix}-tenant"
    agent_id = f"{prefix}-agent"
    knowledge_base_id = f"{prefix}-kb"
    document_id = f"{prefix}-document"
    predecessor_id = f"{prefix}-document-v1"

    content = b"This document cannot be embedded."

    settings = Settings(
        upload_storage_root=tmp_path / "uploads",
        embedding_dimension=1024,
        _env_file=None,
    )

    storage = LocalUploadStorage(
        settings.upload_storage_root
    )

    storage_key = await storage.store(
        tenant_id=tenant_id,
        document_id=document_id,
        content=content,
    )

    async with sessions() as session:
        await _seed_scope(
            session,
            tenant_id=tenant_id,
            agent_ids=[agent_id],
            knowledge_base_ids=[knowledge_base_id],
            assignments=[
                (agent_id, knowledge_base_id),
            ],
        )

        session.add_all(
            [
                DocumentModel(
                    id=predecessor_id,
                    tenant_id=tenant_id,
                    agent_id=None,
                    knowledge_base_id=knowledge_base_id,
                    source_name="active-source",
                    original_filename="active.txt",
                    mime_type="text/plain",
                    file_size_bytes=16,
                    content_hash="7" * 64,
                    status="ready",
                    failure_reason=None,
                    version_number=1,
                    version_family_id=predecessor_id,
                ),
                DocumentModel(
                    id=document_id,
                    tenant_id=tenant_id,
                    agent_id=None,
                    knowledge_base_id=knowledge_base_id,
                    source_name="failed-source",
                    original_filename="failed.txt",
                    mime_type="text/plain",
                    file_size_bytes=len(content),
                    content_hash="8" * 64,
                    status="pending",
                    failure_reason=None,
                    version_number=2,
                    version_family_id=predecessor_id,
                    predecessor_id=predecessor_id,
                ),
            ]
        )

        await session.flush()
        session.add(
            ChunkModel(
                id=f"{prefix}-active-chunk",
                tenant_id=tenant_id,
                agent_id=None,
                knowledge_base_id=knowledge_base_id,
                document_id=predecessor_id,
                source_name="active-source",
                page_number=1,
                chunk_index=0,
                content="Active version remains retrievable",
                content_hash="6" * 64,
                embedding=_vector(1.0),
            )
        )
        await session.flush()

        job = await IngestionJobService.enqueue(
            session,
            tenant_id=tenant_id,
            agent_id=agent_id,
            knowledge_base_id=knowledge_base_id,
            document_id=document_id,
            storage_key=storage_key,
            max_attempts=1,
        )

        job_id = job.id
        await session.commit()

    worker = IngestionWorker(
        settings=settings,
        worker_id="postgres-failure-worker",
        session_factory=sessions,
        embedding_provider=AlwaysFailEmbeddingProvider(),
        storage=storage,
    )

    assert await worker.process_one() is True

    async with sessions() as session:
        stored_job = await session.get(
            IngestionJob,
            job_id,
        )
        stored_document = await session.get(
            DocumentModel,
            document_id,
        )
        predecessor = await session.get(DocumentModel, predecessor_id)

        chunks = list(
            (
                await session.scalars(
                    select(ChunkModel).where(
                        ChunkModel.document_id == document_id
                    )
                )
            ).all()
        )
        active_chunks = list(
            (await session.scalars(
                select(ChunkModel).where(ChunkModel.document_id == predecessor_id)
            )).all()
        )

        audits = list(
            (
                await session.scalars(
                    select(AdminAuditLog).where(
                        AdminAuditLog.target_id == document_id
                    )
                )
            ).all()
        )

    assert stored_job is not None
    assert stored_job.status == "failed"
    assert stored_job.attempts == 1
    assert stored_job.last_error == (
        "Document processing failed."
    )

    assert stored_document is not None
    assert stored_document.status == "failed"
    assert stored_document.failure_reason == (
        "Document processing failed."
    )

    assert chunks == []
    assert predecessor is not None
    assert predecessor.status == "ready"
    assert predecessor.superseded_by_id is None
    assert len(active_chunks) == 1
    assert len(audits) == 1

    audit = audits[0]

    assert audit.event_type == (
        "knowledge_document_processing_failed"
    )
    assert audit.outcome == "failure"
    assert audit.target_type == "knowledge_document"
    assert audit.admin_id is None
    assert audit.detail == {
        "tenant_id": tenant_id,
        "agent_id": agent_id,
        "knowledge_base_id": knowledge_base_id,
        "job_id": job_id,
        "attempts": 1,
        "max_attempts": 1,
    }

    serialized_detail = str(audit.detail).lower()

    assert "content" not in serialized_detail
    assert "token" not in serialized_detail
    assert "password" not in serialized_detail


@pytest.mark.asyncio
async def test_postgres_shared_kb_assignment_controls_access_not_ownership(
    postgres_context,
) -> None:
    prefix, sessions = postgres_context
    tenant_id, kb_id = f"{prefix}-tenant", f"{prefix}-kb"
    agent_a, agent_b = f"{prefix}-agent-a", f"{prefix}-agent-b"
    async with sessions() as session:
        await _seed_scope(
            session, tenant_id=tenant_id, agent_ids=[agent_a, agent_b],
            knowledge_base_ids=[kb_id], assignments=[(agent_a, kb_id)],
        )
        _, chunk_id = await _add_document_and_chunk(
            session, suffix=f"{prefix}-shared", tenant_id=tenant_id,
            document_agent_id=agent_a, chunk_agent_id=agent_a,
            knowledge_base_id=kb_id, status="ready", embedding=_vector(1.0),
        )
        await session.commit()

    provider = ReplacementEmbeddingProvider()
    query = RetrievalQuery(
        tenant_id=tenant_id, agent_id=agent_b, query="shared",
        top_k=5, min_similarity=0.0,
    )
    async with sessions() as session:
        service = RetrievalService(
            provider, SQLAlchemyChunkRepository(session),
            SQLAlchemyKnowledgeBaseRepository(session), rerank_provider=None,
        )
        with pytest.raises(RetrievalValidationError):
            await service.retrieve(query)
        session.add(AgentKnowledgeBase(
            tenant_id=tenant_id, agent_id=agent_b, knowledge_base_id=kb_id,
        ))
        await session.commit()

    async with sessions() as session:
        service = RetrievalService(
            provider, SQLAlchemyChunkRepository(session),
            SQLAlchemyKnowledgeBaseRepository(session), rerank_provider=None,
        )
        assert [item.chunk.id for item in await service.retrieve(query)] == [chunk_id]
        await session.execute(delete(AgentKnowledgeBase).where(
            AgentKnowledgeBase.tenant_id == tenant_id,
            AgentKnowledgeBase.agent_id == agent_b,
            AgentKnowledgeBase.knowledge_base_id == kb_id,
        ))
        await session.commit()

    async with sessions() as session:
        service = RetrievalService(
            provider, SQLAlchemyChunkRepository(session),
            SQLAlchemyKnowledgeBaseRepository(session), rerank_provider=None,
        )
        with pytest.raises(RetrievalValidationError):
            await service.retrieve(query)
        assert await session.get(ChunkModel, chunk_id) is not None


class ReplacementEmbeddingProvider:
    async def embed(
        self,
        request: EmbeddingRequest,
    ) -> EmbeddingResult:
        return EmbeddingResult(
            embeddings=[
                [1.0] + [0.0] * 1023
                for _ in request.texts
            ],
            model="replacement-test-model",
            dimension=1024,
        )


@pytest.mark.asyncio
async def test_postgres_active_document_replacement_is_atomic_and_audited(
    postgres_context,
    tmp_path: Path,
) -> None:
    prefix, sessions = postgres_context

    tenant_id = f"{prefix}-tenant"
    agent_id = f"{prefix}-agent"
    knowledge_base_id = f"{prefix}-kb"
    document_id = f"{prefix}-document-v1"
    replacement_id = f"{prefix}-document-v2"
    old_chunk_id = f"{prefix}-old-chunk"

    replacement_content = (
        b"Replacement knowledge is now the only active content."
    )

    settings = Settings(
        upload_storage_root=tmp_path / "uploads",
        embedding_dimension=1024,
        _env_file=None,
    )

    storage = LocalUploadStorage(
        settings.upload_storage_root
    )

    storage_key = await storage.store(
        tenant_id=tenant_id,
        document_id=replacement_id,
        content=replacement_content,
    )

    async with sessions() as session:
        await _seed_scope(
            session,
            tenant_id=tenant_id,
            agent_ids=[agent_id],
            knowledge_base_ids=[knowledge_base_id],
            assignments=[
                (agent_id, knowledge_base_id),
            ],
        )

        session.add(
            DocumentModel(
                id=document_id,
                tenant_id=tenant_id,
                agent_id=agent_id,
                knowledge_base_id=knowledge_base_id,
                source_name="active-source",
                original_filename="active.txt",
                mime_type="text/plain",
                file_size_bytes=25,
                content_hash="3" * 64,
                status="ready",
                failure_reason=None,
                version_family_id=document_id,
            )
        )

        await session.flush()

        session.add(
            DocumentModel(
                id=replacement_id,
                tenant_id=tenant_id,
                agent_id=None,
                knowledge_base_id=knowledge_base_id,
                source_name="replacement-source",
                original_filename="active.txt",
                mime_type="text/plain",
                file_size_bytes=len(replacement_content),
                content_hash="5" * 64,
                status="pending",
                version_number=2,
                version_family_id=document_id,
                predecessor_id=document_id,
            )
        )
        await session.flush()

        session.add(
            ChunkModel(
                id=old_chunk_id,
                tenant_id=tenant_id,
                agent_id=agent_id,
                knowledge_base_id=knowledge_base_id,
                document_id=document_id,
                source_name="active-source",
                page_number=0,
                chunk_index=0,
                content="Old active knowledge.",
                content_hash="4" * 64,
                embedding=[1.0] + [0.0] * 1023,
            )
        )

        await session.flush()

        job = await IngestionJobService.enqueue(
            session,
            tenant_id=tenant_id,
            agent_id=agent_id,
            knowledge_base_id=knowledge_base_id,
            document_id=replacement_id,
            storage_key=storage_key,
            max_attempts=1,
        )

        job_id = job.id

        await session.commit()

    worker = IngestionWorker(
        settings=settings,
        worker_id="postgres-replacement-worker",
        session_factory=sessions,
        embedding_provider=ReplacementEmbeddingProvider(),
        storage=storage,
    )

    assert await worker.process_one() is True

    async with sessions() as session:
        stored_job = await session.get(
            IngestionJob,
            job_id,
        )

        stored_v1 = await session.get(DocumentModel, document_id)
        stored_document = await session.get(DocumentModel, replacement_id)

        chunks = list(
            (
                await session.scalars(
                    select(ChunkModel)
                    .where(
                        ChunkModel.tenant_id == tenant_id,
                        ChunkModel.knowledge_base_id
                        == knowledge_base_id,
                        ChunkModel.document_id == replacement_id,
                    )
                    .order_by(ChunkModel.chunk_index)
                )
            ).all()
        )

        audits = list(
            (
                await session.scalars(
                    select(AdminAuditLog)
                    .where(
                        AdminAuditLog.target_id == replacement_id
                    )
                    .order_by(AdminAuditLog.created_at)
                )
            ).all()
        )

        rag_results = await SQLAlchemyChunkRepository(
            session
        ).semantic_search(
            query_embedding=[1.0] + [0.0] * 1023,
            tenant_id=tenant_id,
            agent_id=agent_id,
            knowledge_base_id=knowledge_base_id,
            top_k=10,
            min_similarity=0.0,
        )

    assert stored_job is not None
    assert stored_job.status == "succeeded"
    assert stored_job.attempts == 1

    assert stored_document is not None
    assert stored_document.status == "ready"
    assert stored_document.failure_reason is None
    assert stored_document.content_hash != "3" * 64
    assert stored_document.predecessor_id == document_id
    assert stored_document.version_number == 2
    assert stored_v1 is not None
    assert stored_v1.status == "superseded"
    assert stored_v1.superseded_by_id == replacement_id

    assert len(chunks) == 1
    assert chunks[0].id != old_chunk_id
    assert chunks[0].content == replacement_content.decode()

    assert [
        chunk.id
        for chunk, _ in rag_results
    ] == [
        chunks[0].id
    ]

    assert len(audits) == 1

    audit = audits[0]

    assert audit.event_type == (
        "knowledge_document_replaced"
    )
    assert audit.outcome == "success"
    assert audit.target_type == "knowledge_document"
    assert audit.target_id == replacement_id
    assert audit.admin_id is None
    assert audit.detail == {
        "tenant_id": tenant_id,
        "agent_id": agent_id,
        "knowledge_base_id": knowledge_base_id,
        "job_id": job_id,
        "chunks_persisted": 1,
    }

    assert all(
        item.event_type
        != "knowledge_document_activated"
        for item in audits
    )


@pytest.mark.asyncio
async def test_voyage_embeddings_produce_1024_dimensions(
    postgres_context,
    tmp_path: Path,
) -> None:
    """Voyage embeddings are persisted with exactly 1024 dimensions."""
    from backend.app.ai.providers.voyage import (
        VoyageEmbeddingProvider,
        VOYAGE_EMBEDDING_DIMENSION,
    )
    from backend.app.operations.ingestion_runtime import build_ingestion_service
    from backend.app.services.knowledge.ingestion_service import IngestionRequest
    from unittest.mock import AsyncMock
    import httpx
    import json

    # Mock Voyage HTTP transport
    transport = AsyncMock(spec=httpx.AsyncBaseTransport)

    def make_voyage_response(num_texts: int) -> bytes:
        return json.dumps({
            "data": [
                {"embedding": [0.1 * (i + 1)] * VOYAGE_EMBEDDING_DIMENSION}
                for i in range(num_texts)
            ],
            "model": "voyage-4-large",
            "usage": {"total_tokens": num_texts * 10}
        }).encode()

    async def mock_handle(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        num_texts = len(payload["input"])
        return httpx.Response(
            status_code=200,
            content=make_voyage_response(num_texts),
            headers={"content-type": "application/json"},
        )

    transport.handle_async_request = mock_handle

    prefix, sessions = postgres_context

    tenant_id = f"{prefix}-tenant"
    agent_id = f"{prefix}-agent"
    knowledge_base_id = f"{prefix}-kb"

    settings = Settings(
        voyage_api_key="test_key",
        embedding_dimension=1024,
        _env_file=None,
    )

    voyage_provider = VoyageEmbeddingProvider(
        settings,
        transport=transport,
    )

    content = b"Test document for Voyage embeddings. " * 50

    async with sessions() as session:
        await _seed_scope(
            session,
            tenant_id=tenant_id,
            agent_ids=[agent_id],
            knowledge_base_ids=[knowledge_base_id],
            assignments=[(agent_id, knowledge_base_id)],
        )

        await session.commit()

        service = build_ingestion_service(
            session=session,
            runtime=voyage_provider,
            settings=settings,
        )

        request = IngestionRequest(
            content=content,
            filename="test.txt",
            mime_type="text/plain",
            tenant_id=tenant_id,
            agent_id=agent_id,
            knowledge_base_id=knowledge_base_id,
            source_name="upload",
        )

        result = await service.ingest(request)
        await session.commit()

        # Verify chunks were persisted
        assert result.chunks_persisted > 0

        # Verify embeddings have exactly 1024 dimensions
        chunks = list(
            (
                await session.scalars(
                    select(ChunkModel).where(
                        ChunkModel.document_id == result.document.id
                    )
                )
            ).all()
        )

        assert len(chunks) == result.chunks_persisted

        for chunk in chunks:
            assert len(chunk.embedding) == VOYAGE_EMBEDDING_DIMENSION
            # Verify embedding values are non-zero (from Voyage mock)
            assert chunk.embedding[0] > 0
