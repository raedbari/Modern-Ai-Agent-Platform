"""Integration tests for the tenant-scoped document repository."""

from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.app.db.base import Base
from backend.app.db.models import (
    Agent,
    DocumentModel,
    IngestionJob,
    KnowledgeBaseModel,
    Tenant,
)
from backend.app.infrastructure.database.tenant_repositories import (
    TenantScopedDocumentRepository,
)


@pytest_asyncio.fixture
async def database() -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]]:
    """Create an in-memory SQLite database for testing."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    @event.listens_for(engine.sync_engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield engine, session_factory
    finally:
        await engine.dispose()


async def _seed_tenant(session: AsyncSession, tenant_id: str) -> None:
    """Create a tenant for testing."""
    session.add(Tenant(id=tenant_id, name=f"Tenant {tenant_id}"))
    await session.flush()


async def _seed_knowledge_base(
    session: AsyncSession, kb_id: str, tenant_id: str
) -> None:
    """Create a knowledge base for testing."""
    session.add(
        KnowledgeBaseModel(
            id=kb_id,
            tenant_id=tenant_id,
            name=f"KB {kb_id}",
        )
    )
    await session.flush()


async def _seed_agent(
    session: AsyncSession, agent_id: str, tenant_id: str
) -> None:
    """Create an agent for testing."""
    session.add(
        Agent(
            id=agent_id,
            tenant_id=tenant_id,
            name=f"Agent {agent_id}",
        )
    )
    await session.flush()


@pytest.mark.asyncio
async def test_list_by_knowledge_base_returns_documents_when_kb_owned(
    database: tuple[AsyncEngine, async_sessionmaker[AsyncSession]],
) -> None:
    """Test that list_by_knowledge_base returns documents when KB is owned by tenant."""
    _, session_factory = database

    async with session_factory() as session:
        await _seed_tenant(session, "tenant-a")
        await _seed_knowledge_base(session, "kb-a1", "tenant-a")
        
        session.add_all(
            [
                DocumentModel(
                    id="doc-1",
                    tenant_id="tenant-a",
                    knowledge_base_id="kb-a1",
                    source_name="Source 1",
                    original_filename="file1.pdf",
                    mime_type="application/pdf",
                    file_size_bytes=1024,
                    content_hash="hash1",
                ),
                DocumentModel(
                    id="doc-2",
                    tenant_id="tenant-a",
                    knowledge_base_id="kb-a1",
                    source_name="Source 2",
                    original_filename="file2.pdf",
                    mime_type="application/pdf",
                    file_size_bytes=2048,
                    content_hash="hash2",
                ),
            ]
        )
        await session.commit()

    async with session_factory() as session:
        repo = TenantScopedDocumentRepository(session)
        docs = await repo.list_by_knowledge_base("kb-a1", "tenant-a")

        assert len(docs) == 2
        assert all(doc.tenant_id == "tenant-a" for doc in docs)
        assert all(doc.knowledge_base_id == "kb-a1" for doc in docs)
        doc_ids = {doc.id for doc in docs}
        assert doc_ids == {"doc-1", "doc-2"}


@pytest.mark.asyncio
async def test_list_by_knowledge_base_returns_empty_for_cross_tenant_kb(
    database: tuple[AsyncEngine, async_sessionmaker[AsyncSession]],
) -> None:
    """Test that list_by_knowledge_base returns empty list when KB belongs to different tenant."""
    _, session_factory = database

    async with session_factory() as session:
        await _seed_tenant(session, "tenant-a")
        await _seed_tenant(session, "tenant-b")
        await _seed_knowledge_base(session, "kb-a1", "tenant-a")
        
        session.add(
            DocumentModel(
                id="doc-1",
                tenant_id="tenant-a",
                knowledge_base_id="kb-a1",
                source_name="Source 1",
                original_filename="file1.pdf",
                mime_type="application/pdf",
                file_size_bytes=1024,
                content_hash="hash1",
            )
        )
        await session.commit()

    async with session_factory() as session:
        repo = TenantScopedDocumentRepository(session)
        docs = await repo.list_by_knowledge_base("kb-a1", "tenant-b")

        assert len(docs) == 0


@pytest.mark.asyncio
async def test_get_by_id_returns_document_when_kb_owned(
    database: tuple[AsyncEngine, async_sessionmaker[AsyncSession]],
) -> None:
    """Test that get_by_id returns document only if its KB belongs to the tenant."""
    _, session_factory = database

    async with session_factory() as session:
        await _seed_tenant(session, "tenant-a")
        await _seed_knowledge_base(session, "kb-a1", "tenant-a")
        
        session.add(
            DocumentModel(
                id="doc-1",
                tenant_id="tenant-a",
                knowledge_base_id="kb-a1",
                source_name="Source 1",
                original_filename="file1.pdf",
                mime_type="application/pdf",
                file_size_bytes=1024,
                content_hash="hash1",
            )
        )
        await session.commit()

    async with session_factory() as session:
        repo = TenantScopedDocumentRepository(session)
        doc = await repo.get_by_id("doc-1", "kb-a1", "tenant-a")

        assert doc is not None
        assert doc.id == "doc-1"
        assert doc.tenant_id == "tenant-a"
        assert doc.knowledge_base_id == "kb-a1"


@pytest.mark.asyncio
async def test_get_by_id_returns_none_for_cross_tenant_kb(
    database: tuple[AsyncEngine, async_sessionmaker[AsyncSession]],
) -> None:
    """Test that get_by_id returns None when KB belongs to different tenant."""
    _, session_factory = database

    async with session_factory() as session:
        await _seed_tenant(session, "tenant-a")
        await _seed_tenant(session, "tenant-b")
        await _seed_knowledge_base(session, "kb-a1", "tenant-a")
        
        session.add(
            DocumentModel(
                id="doc-1",
                tenant_id="tenant-a",
                knowledge_base_id="kb-a1",
                source_name="Source 1",
                original_filename="file1.pdf",
                mime_type="application/pdf",
                file_size_bytes=1024,
                content_hash="hash1",
            )
        )
        await session.commit()

    async with session_factory() as session:
        repo = TenantScopedDocumentRepository(session)
        doc = await repo.get_by_id("doc-1", "kb-a1", "tenant-b")

        assert doc is None


@pytest.mark.asyncio
async def test_create_succeeds_when_kb_owned_by_tenant(
    database: tuple[AsyncEngine, async_sessionmaker[AsyncSession]],
) -> None:
    """Test that create succeeds when KB belongs to tenant."""
    _, session_factory = database

    async with session_factory() as session:
        await _seed_tenant(session, "tenant-a")
        await _seed_knowledge_base(session, "kb-a1", "tenant-a")
        await session.commit()

    async with session_factory() as session:
        repo = TenantScopedDocumentRepository(session)
        doc = await repo.create(
            doc_id="doc-new",
            kb_id="kb-a1",
            tenant_id="tenant-a",
            source_name="New Source",
            original_filename="newfile.pdf",
            mime_type="application/pdf",
            file_size_bytes=1024,
            content_hash="newhash",
        )
        await session.commit()

        assert doc is not None
        assert doc.id == "doc-new"
        assert doc.tenant_id == "tenant-a"
        assert doc.knowledge_base_id == "kb-a1"

    # Verify document was persisted
    async with session_factory() as session:
        result = await session.scalar(
            select(DocumentModel).where(DocumentModel.id == "doc-new")
        )
        assert result is not None
        assert result.tenant_id == "tenant-a"


@pytest.mark.asyncio
async def test_create_returns_none_for_cross_tenant_kb(
    database: tuple[AsyncEngine, async_sessionmaker[AsyncSession]],
) -> None:
    """Test that create returns None when KB belongs to different tenant."""
    _, session_factory = database

    async with session_factory() as session:
        await _seed_tenant(session, "tenant-a")
        await _seed_tenant(session, "tenant-b")
        await _seed_knowledge_base(session, "kb-a1", "tenant-a")
        await session.commit()

    async with session_factory() as session:
        repo = TenantScopedDocumentRepository(session)
        doc = await repo.create(
            doc_id="doc-new",
            kb_id="kb-a1",
            tenant_id="tenant-b",  # Different tenant
            source_name="New Source",
            original_filename="newfile.pdf",
            mime_type="application/pdf",
            file_size_bytes=1024,
            content_hash="newhash",
        )
        await session.commit()

        assert doc is None

    # Verify document was not created
    async with session_factory() as session:
        result = await session.scalar(
            select(DocumentModel).where(DocumentModel.id == "doc-new")
        )
        assert result is None


@pytest.mark.asyncio
async def test_delete_succeeds_when_kb_owned_by_tenant(
    database: tuple[AsyncEngine, async_sessionmaker[AsyncSession]],
) -> None:
    """Test that delete succeeds when KB belongs to tenant."""
    _, session_factory = database

    async with session_factory() as session:
        await _seed_tenant(session, "tenant-a")
        await _seed_knowledge_base(session, "kb-a1", "tenant-a")
        
        session.add(
            DocumentModel(
                id="doc-1",
                tenant_id="tenant-a",
                knowledge_base_id="kb-a1",
                source_name="Source 1",
                original_filename="file1.pdf",
                mime_type="application/pdf",
                file_size_bytes=1024,
                content_hash="hash1",
            )
        )
        await session.commit()

    async with session_factory() as session:
        repo = TenantScopedDocumentRepository(session)
        deleted = await repo.delete("doc-1", "kb-a1", "tenant-a")
        await session.commit()

        assert deleted is True

    # Verify document was deleted
    async with session_factory() as session:
        result = await session.scalar(
            select(DocumentModel).where(DocumentModel.id == "doc-1")
        )
        assert result is None


@pytest.mark.asyncio
async def test_delete_returns_false_for_cross_tenant_kb(
    database: tuple[AsyncEngine, async_sessionmaker[AsyncSession]],
) -> None:
    """Test that delete returns False when KB belongs to different tenant."""
    _, session_factory = database

    async with session_factory() as session:
        await _seed_tenant(session, "tenant-a")
        await _seed_tenant(session, "tenant-b")
        await _seed_knowledge_base(session, "kb-a1", "tenant-a")
        
        session.add(
            DocumentModel(
                id="doc-1",
                tenant_id="tenant-a",
                knowledge_base_id="kb-a1",
                source_name="Source 1",
                original_filename="file1.pdf",
                mime_type="application/pdf",
                file_size_bytes=1024,
                content_hash="hash1",
            )
        )
        await session.commit()

    async with session_factory() as session:
        repo = TenantScopedDocumentRepository(session)
        deleted = await repo.delete("doc-1", "kb-a1", "tenant-b")
        await session.commit()

        assert deleted is False

    # Verify document still exists
    async with session_factory() as session:
        result = await session.scalar(
            select(DocumentModel).where(DocumentModel.id == "doc-1")
        )
        assert result is not None


@pytest.mark.asyncio
async def test_create_ingestion_job_succeeds_when_kb_and_doc_owned(
    database: tuple[AsyncEngine, async_sessionmaker[AsyncSession]],
) -> None:
    """Test that create_ingestion_job succeeds when both KB and document belong to tenant."""
    _, session_factory = database

    async with session_factory() as session:
        await _seed_tenant(session, "tenant-a")
        await _seed_knowledge_base(session, "kb-a1", "tenant-a")
        await _seed_agent(session, "agent-a1", "tenant-a")
        
        session.add(
            DocumentModel(
                id="doc-1",
                tenant_id="tenant-a",
                knowledge_base_id="kb-a1",
                source_name="Source 1",
                original_filename="file1.pdf",
                mime_type="application/pdf",
                file_size_bytes=1024,
                content_hash="hash1",
            )
        )
        await session.commit()

    async with session_factory() as session:
        repo = TenantScopedDocumentRepository(session)
        job = await repo.create_ingestion_job(
            job_id="job-1",
            doc_id="doc-1",
            kb_id="kb-a1",
            tenant_id="tenant-a",
            agent_id="agent-a1",
            storage_key="s3://bucket/key",
            source_filename="file1.pdf",
            source_mime_type="application/pdf",
            source_name="Source 1",
        )
        await session.commit()

        assert job is not None
        assert job.id == "job-1"
        assert job.tenant_id == "tenant-a"
        assert job.knowledge_base_id == "kb-a1"
        assert job.document_id == "doc-1"


@pytest.mark.asyncio
async def test_create_ingestion_job_returns_none_for_cross_tenant_kb(
    database: tuple[AsyncEngine, async_sessionmaker[AsyncSession]],
) -> None:
    """Test that create_ingestion_job returns None when KB belongs to different tenant."""
    _, session_factory = database

    async with session_factory() as session:
        await _seed_tenant(session, "tenant-a")
        await _seed_tenant(session, "tenant-b")
        await _seed_knowledge_base(session, "kb-a1", "tenant-a")
        await _seed_agent(session, "agent-a1", "tenant-a")
        
        session.add(
            DocumentModel(
                id="doc-1",
                tenant_id="tenant-a",
                knowledge_base_id="kb-a1",
                source_name="Source 1",
                original_filename="file1.pdf",
                mime_type="application/pdf",
                file_size_bytes=1024,
                content_hash="hash1",
            )
        )
        await session.commit()

    async with session_factory() as session:
        repo = TenantScopedDocumentRepository(session)
        job = await repo.create_ingestion_job(
            job_id="job-1",
            doc_id="doc-1",
            kb_id="kb-a1",
            tenant_id="tenant-b",  # Different tenant
            agent_id="agent-a1",
            storage_key="s3://bucket/key",
        )
        await session.commit()

        assert job is None


@pytest.mark.asyncio
async def test_get_ingestion_job_returns_job_when_kb_owned(
    database: tuple[AsyncEngine, async_sessionmaker[AsyncSession]],
) -> None:
    """Test that get_ingestion_job returns job only if its KB belongs to tenant."""
    _, session_factory = database

    async with session_factory() as session:
        await _seed_tenant(session, "tenant-a")
        await _seed_knowledge_base(session, "kb-a1", "tenant-a")
        await _seed_agent(session, "agent-a1", "tenant-a")
        
        session.add(
            DocumentModel(
                id="doc-1",
                tenant_id="tenant-a",
                knowledge_base_id="kb-a1",
                source_name="Source 1",
                original_filename="file1.pdf",
                mime_type="application/pdf",
                file_size_bytes=1024,
                content_hash="hash1",
            )
        )
        session.add(
            IngestionJob(
                id="job-1",
                tenant_id="tenant-a",
                agent_id="agent-a1",
                knowledge_base_id="kb-a1",
                document_id="doc-1",
                storage_key="s3://bucket/key",
            )
        )
        await session.commit()

    async with session_factory() as session:
        repo = TenantScopedDocumentRepository(session)
        job = await repo.get_ingestion_job("job-1", "kb-a1", "tenant-a")

        assert job is not None
        assert job.id == "job-1"
        assert job.tenant_id == "tenant-a"
        assert job.knowledge_base_id == "kb-a1"


@pytest.mark.asyncio
async def test_get_ingestion_job_returns_none_for_cross_tenant_kb(
    database: tuple[AsyncEngine, async_sessionmaker[AsyncSession]],
) -> None:
    """Test that get_ingestion_job returns None when KB belongs to different tenant."""
    _, session_factory = database

    async with session_factory() as session:
        await _seed_tenant(session, "tenant-a")
        await _seed_tenant(session, "tenant-b")
        await _seed_knowledge_base(session, "kb-a1", "tenant-a")
        await _seed_agent(session, "agent-a1", "tenant-a")
        
        session.add(
            DocumentModel(
                id="doc-1",
                tenant_id="tenant-a",
                knowledge_base_id="kb-a1",
                source_name="Source 1",
                original_filename="file1.pdf",
                mime_type="application/pdf",
                file_size_bytes=1024,
                content_hash="hash1",
            )
        )
        session.add(
            IngestionJob(
                id="job-1",
                tenant_id="tenant-a",
                agent_id="agent-a1",
                knowledge_base_id="kb-a1",
                document_id="doc-1",
                storage_key="s3://bucket/key",
            )
        )
        await session.commit()

    async with session_factory() as session:
        repo = TenantScopedDocumentRepository(session)
        job = await repo.get_ingestion_job("job-1", "kb-a1", "tenant-b")

        assert job is None
