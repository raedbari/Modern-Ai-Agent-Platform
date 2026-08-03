"""Integration tests for the SQLAlchemy knowledge repositories."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import event, select
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.app.db.base import Base
from backend.app.db.models import (
    Agent,
    AgentKnowledgeBase,
    ChunkModel,
    KnowledgeBaseModel,
    Tenant,
)
from backend.app.domain.exceptions import DocumentNotFoundError
from backend.app.domain.models.chunk import Chunk
from backend.app.domain.models.document import Document
from backend.app.domain.models.enums import DocumentProcessingStatus
from backend.app.domain.ports.repositories import ChunkWrite
from backend.app.infrastructure.database.repositories import (
    SQLAlchemyChunkRepository,
    SQLAlchemyDocumentRepository,
    SQLAlchemyKnowledgeBaseRepository,
)


@pytest_asyncio.fixture
async def database() -> tuple[
    AsyncEngine,
    async_sessionmaker[AsyncSession],
]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

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
    try:
        yield engine, session_factory
    finally:
        await engine.dispose()


async def _seed_knowledge_scope(
    session: AsyncSession,
    *,
    tenant_id: str,
    agent_id: str,
    knowledge_base_id: str,
    status: str = "active",
) -> None:
    session.add(Tenant(id=tenant_id, name=tenant_id))
    await session.flush()
    session.add_all(
        [
            Agent(
                id=agent_id,
                tenant_id=tenant_id,
                name=agent_id,
            ),
            KnowledgeBaseModel(
                id=knowledge_base_id,
                tenant_id=tenant_id,
                name=knowledge_base_id,
                status=status,
            ),
        ]
    )
    await session.flush()
    session.add(
        AgentKnowledgeBase(
            tenant_id=tenant_id,
            agent_id=agent_id,
            knowledge_base_id=knowledge_base_id,
        )
    )
    await session.flush()


def _document(
    *,
    document_id: str,
    tenant_id: str,
    knowledge_base_id: str,
    agent_id: str,
    content_hash: str,
) -> Document:
    timestamp = datetime.now(timezone.utc)
    return Document(
        id=document_id,
        tenant_id=tenant_id,
        knowledge_base_id=knowledge_base_id,
        agent_id=agent_id,
        source_name="upload",
        original_filename=f"{document_id}.txt",
        mime_type="text/plain",
        file_size_bytes=20,
        content_hash=content_hash,
        created_at=timestamp,
        updated_at=timestamp,
    )


def _chunk(
    *,
    chunk_id: str,
    tenant_id: str,
    agent_id: str,
    knowledge_base_id: str,
    document_id: str,
    chunk_index: int,
) -> Chunk:
    return Chunk(
        id=chunk_id,
        tenant_id=tenant_id,
        agent_id=agent_id,
        knowledge_base_id=knowledge_base_id,
        document_id=document_id,
        source_name="upload",
        page_number=0,
        chunk_index=chunk_index,
        content=f"content for {chunk_id}",
        content_hash=f"{chunk_index:064x}",
    )


def _unit_vector(index: int) -> tuple[float, ...]:
    values = [0.0] * 1024
    values[index] = 1.0
    return tuple(values)


def test_postgresql_semantic_query_uses_cosine_and_all_scope_filters() -> None:
    vector = list(_unit_vector(0))
    distance = ChunkModel.embedding.cosine_distance(vector)
    similarity = (1.0 - distance).label("similarity")
    statement = (
        select(ChunkModel, similarity)
        .where(
            ChunkModel.tenant_id == "tenant-a",
            ChunkModel.agent_id == "agent-a",
            ChunkModel.knowledge_base_id == "kb-a",
            similarity >= 0.5,
        )
        .order_by(distance, ChunkModel.id)
        .limit(5)
    )

    sql = str(statement.compile(dialect=postgresql.dialect()))
    assert "<=>" in sql
    assert "chunks.tenant_id" in sql
    assert "chunks.agent_id" in sql
    assert "chunks.knowledge_base_id" in sql
    assert "ORDER BY chunks.embedding <=>" in sql


@pytest.mark.asyncio
async def test_knowledge_base_queries_are_tenant_and_agent_scoped(
    database,
) -> None:
    _, session_factory = database
    async with session_factory() as session:
        await _seed_knowledge_scope(
            session,
            tenant_id="tenant-a",
            agent_id="agent-a",
            knowledge_base_id="kb-a",
        )
        await _seed_knowledge_scope(
            session,
            tenant_id="tenant-b",
            agent_id="agent-b",
            knowledge_base_id="kb-b",
        )
        repository = SQLAlchemyKnowledgeBaseRepository(session)

        assert await repository.get_by_id("kb-b", "tenant-a") is None
        assert not await repository.exists_for_tenant("kb-b", "tenant-a")
        assert [
            item.id
            for item in await repository.list_for_agent(
                "agent-a",
                "tenant-a",
            )
        ] == ["kb-a"]


@pytest.mark.asyncio
async def test_document_repository_persists_status_and_scopes_hash_lookup(
    database,
) -> None:
    _, session_factory = database
    async with session_factory() as session:
        await _seed_knowledge_scope(
            session,
            tenant_id="tenant-a",
            agent_id="agent-a",
            knowledge_base_id="kb-a",
        )
        await _seed_knowledge_scope(
            session,
            tenant_id="tenant-b",
            agent_id="agent-b",
            knowledge_base_id="kb-b",
        )
        repository = SQLAlchemyDocumentRepository(session)
        stored = await repository.create(
            _document(
                document_id="doc-a",
                tenant_id="tenant-a",
                knowledge_base_id="kb-a",
                agent_id="agent-a",
                content_hash="a" * 64,
            )
        )

        assert stored.status == DocumentProcessingStatus.PENDING
        assert (
            await repository.get_by_content_hash(
                "a" * 64,
                "tenant-b",
                "kb-b",
            )
            is None
        )

        await repository.update_processing_status(
            "doc-a",
            "tenant-a",
            DocumentProcessingStatus.READY,
        )
        updated = await repository.get_by_id("doc-a", "tenant-a")
        assert updated is not None
        assert updated.status == DocumentProcessingStatus.READY
        assert updated.failure_reason is None

        with pytest.raises(DocumentNotFoundError):
            await repository.update_processing_status(
                "doc-a",
                "tenant-b",
                DocumentProcessingStatus.FAILED,
            )


@pytest.mark.asyncio
async def test_chunk_repository_search_filters_scope_before_ranking(
    database,
) -> None:
    _, session_factory = database
    async with session_factory() as session:
        await _seed_knowledge_scope(
            session,
            tenant_id="tenant-a",
            agent_id="agent-a",
            knowledge_base_id="kb-a",
        )
        await _seed_knowledge_scope(
            session,
            tenant_id="tenant-b",
            agent_id="agent-b",
            knowledge_base_id="kb-b",
        )
        documents = SQLAlchemyDocumentRepository(session)
        await documents.create(
            _document(
                document_id="doc-a",
                tenant_id="tenant-a",
                knowledge_base_id="kb-a",
                agent_id="agent-a",
                content_hash="a" * 64,
            )
        )
        await documents.create(
            _document(
                document_id="doc-b",
                tenant_id="tenant-b",
                knowledge_base_id="kb-b",
                agent_id="agent-b",
                content_hash="b" * 64,
            )
        )

        await documents.update_processing_status(
            document_id="doc-a",
            tenant_id="tenant-a",
            status=DocumentProcessingStatus.READY,
        )
        await documents.update_processing_status(
            document_id="doc-b",
            tenant_id="tenant-b",
            status=DocumentProcessingStatus.READY,
        )

        chunks = SQLAlchemyChunkRepository(session)
        await chunks.create_many(
            [
                ChunkWrite(
                    chunk=_chunk(
                        chunk_id="chunk-a-best",
                        tenant_id="tenant-a",
                        agent_id="agent-a",
                        knowledge_base_id="kb-a",
                        document_id="doc-a",
                        chunk_index=0,
                    ),
                    embedding=_unit_vector(0),
                ),
                ChunkWrite(
                    chunk=_chunk(
                        chunk_id="chunk-a-other",
                        tenant_id="tenant-a",
                        agent_id="agent-a",
                        knowledge_base_id="kb-a",
                        document_id="doc-a",
                        chunk_index=1,
                    ),
                    embedding=_unit_vector(1),
                ),
            ]
        )
        await chunks.create_many(
            [
                ChunkWrite(
                    chunk=_chunk(
                        chunk_id="chunk-b-identical",
                        tenant_id="tenant-b",
                        agent_id="agent-b",
                        knowledge_base_id="kb-b",
                        document_id="doc-b",
                        chunk_index=0,
                    ),
                    embedding=_unit_vector(0),
                )
            ]
        )

        results = await chunks.semantic_search(
            query_embedding=list(_unit_vector(0)),
            tenant_id="tenant-a",
            agent_id="agent-a",
            knowledge_base_id="kb-a",
            top_k=5,
            min_similarity=0.5,
        )

        assert [(chunk.id, score) for chunk, score in results] == [
            ("chunk-a-best", pytest.approx(1.0))
        ]
        assert [
            chunk.chunk_index
            for chunk in await chunks.list_by_document(
                "doc-a",
                "tenant-a",
            )
        ] == [0, 1]
        assert await chunks.delete_by_document("doc-a", "tenant-b") == 0
        assert await chunks.delete_by_document("doc-a", "tenant-a") == 2


@pytest.mark.asyncio
async def test_chunk_repository_rejects_invalid_embedding_dimension(
    database,
) -> None:
    _, session_factory = database
    async with session_factory() as session:
        repository = SQLAlchemyChunkRepository(session)
        with pytest.raises(ValueError, match="1024"):
            await repository.semantic_search(
                query_embedding=[1.0, 0.0],
                tenant_id="tenant-a",
                agent_id="agent-a",
                knowledge_base_id="kb-a",
                top_k=5,
                min_similarity=0.5,
            )
