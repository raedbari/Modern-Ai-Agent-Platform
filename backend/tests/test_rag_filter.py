"""Tests for ready-document filtering in semantic retrieval."""

from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.app.db.base import Base
from backend.app.db.models import (
    Agent,
    ChunkModel,
    DocumentModel,
    KnowledgeBaseModel,
    Tenant,
)
from backend.app.infrastructure.database.repositories.sqlalchemy_repositories import (
    SQLAlchemyChunkRepository,
)


def _vector(
    first: float,
    second: float = 0.0,
) -> list[float]:
    return [first, second] + [0.0] * 1022


async def _open_sessions(
    database_path: Path,
) -> tuple[
    async_sessionmaker[AsyncSession],
    AsyncEngine,
]:
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{database_path.as_posix()}"
    )

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    return (
        async_sessionmaker(
            engine,
            expire_on_commit=False,
        ),
        engine,
    )


async def _seed_scope(
    sessions: async_sessionmaker[AsyncSession],
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
                Agent(
                    id="agent-a",
                    tenant_id="tenant-a",
                    name="Agent A",
                ),
                Agent(
                    id="agent-a2",
                    tenant_id="tenant-a",
                    name="Agent A2",
                ),
                Agent(
                    id="agent-b",
                    tenant_id="tenant-b",
                    name="Agent B",
                ),
            ]
        )

        session.add_all(
            [
                KnowledgeBaseModel(
                    id="kb-a",
                    tenant_id="tenant-a",
                    name="KB A",
                ),
                KnowledgeBaseModel(
                    id="kb-a2",
                    tenant_id="tenant-a",
                    name="KB A2",
                ),
                KnowledgeBaseModel(
                    id="kb-b",
                    tenant_id="tenant-b",
                    name="KB B",
                ),
            ]
        )

        await session.commit()


def _add_document_and_chunk(
    session: AsyncSession,
    *,
    suffix: str,
    tenant_id: str,
    document_agent_id: str,
    chunk_agent_id: str,
    knowledge_base_id: str,
    status: str,
    embedding: list[float],
) -> None:
    document_id = f"document-{suffix}"

    session.add(
        DocumentModel(
            id=document_id,
            tenant_id=tenant_id,
            knowledge_base_id=knowledge_base_id,
            agent_id=document_agent_id,
            source_name=f"{suffix}.txt",
            original_filename=f"{suffix}.txt",
            mime_type="text/plain",
            file_size_bytes=10,
            content_hash=f"document-hash-{suffix}",
            status=status,
        )
    )

    session.add(
        ChunkModel(
            id=f"chunk-{suffix}",
            tenant_id=tenant_id,
            agent_id=chunk_agent_id,
            knowledge_base_id=knowledge_base_id,
            document_id=document_id,
            source_name=f"{suffix}.txt",
            page_number=0,
            chunk_index=0,
            content=f"Content {suffix}",
            content_hash=f"chunk-hash-{suffix}",
            embedding=embedding,
        )
    )


@pytest.mark.asyncio
async def test_only_ready_documents_are_retrievable(
    tmp_path: Path,
) -> None:
    sessions, engine = await _open_sessions(
        tmp_path / "statuses.sqlite3"
    )

    try:
        await _seed_scope(sessions)

        async with sessions() as session:
            for status in (
                "pending",
                "processing",
                "ready",
                "failed",
            ):
                _add_document_and_chunk(
                    session,
                    suffix=status,
                    tenant_id="tenant-a",
                    document_agent_id="agent-a",
                    chunk_agent_id="agent-a",
                    knowledge_base_id="kb-a",
                    status=status,
                    embedding=_vector(1.0),
                )

            await session.commit()

        async with sessions() as session:
            repository = SQLAlchemyChunkRepository(session)

            results = await repository.semantic_search(
                query_embedding=_vector(1.0),
                tenant_id="tenant-a",
                agent_id="agent-a",
                knowledge_base_id="kb-a",
                top_k=10,
                min_similarity=0.0,
            )

        assert [chunk.id for chunk, _ in results] == [
            "chunk-ready"
        ]

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_search_enforces_tenant_agent_and_knowledge_base_scope(
    tmp_path: Path,
) -> None:
    sessions, engine = await _open_sessions(
        tmp_path / "scope.sqlite3"
    )

    try:
        await _seed_scope(sessions)

        async with sessions() as session:
            _add_document_and_chunk(
                session,
                suffix="exact",
                tenant_id="tenant-a",
                document_agent_id="agent-a",
                chunk_agent_id="agent-a",
                knowledge_base_id="kb-a",
                status="ready",
                embedding=_vector(1.0),
            )

            _add_document_and_chunk(
                session,
                suffix="wrong-agent",
                tenant_id="tenant-a",
                document_agent_id="agent-a2",
                chunk_agent_id="agent-a2",
                knowledge_base_id="kb-a",
                status="ready",
                embedding=_vector(1.0),
            )

            _add_document_and_chunk(
                session,
                suffix="wrong-kb",
                tenant_id="tenant-a",
                document_agent_id="agent-a",
                chunk_agent_id="agent-a",
                knowledge_base_id="kb-a2",
                status="ready",
                embedding=_vector(1.0),
            )

            _add_document_and_chunk(
                session,
                suffix="wrong-tenant",
                tenant_id="tenant-b",
                document_agent_id="agent-b",
                chunk_agent_id="agent-b",
                knowledge_base_id="kb-b",
                status="ready",
                embedding=_vector(1.0),
            )

            await session.commit()

        async with sessions() as session:
            repository = SQLAlchemyChunkRepository(session)

            results = await repository.semantic_search(
                query_embedding=_vector(1.0),
                tenant_id="tenant-a",
                agent_id="agent-a",
                knowledge_base_id="kb-a",
                top_k=10,
                min_similarity=0.0,
            )

        assert [chunk.id for chunk, _ in results] == [
            "chunk-exact"
        ]

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_document_agent_must_match_chunk_agent(
    tmp_path: Path,
) -> None:
    sessions, engine = await _open_sessions(
        tmp_path / "agent-binding.sqlite3"
    )

    try:
        await _seed_scope(sessions)

        async with sessions() as session:
            _add_document_and_chunk(
                session,
                suffix="mismatched-agent",
                tenant_id="tenant-a",
                document_agent_id="agent-a2",
                chunk_agent_id="agent-a",
                knowledge_base_id="kb-a",
                status="ready",
                embedding=_vector(1.0),
            )

            await session.commit()

        async with sessions() as session:
            repository = SQLAlchemyChunkRepository(session)

            results = await repository.semantic_search(
                query_embedding=_vector(1.0),
                tenant_id="tenant-a",
                agent_id="agent-a",
                knowledge_base_id="kb-a",
                top_k=10,
                min_similarity=0.0,
            )

        assert results == []

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_ready_results_preserve_similarity_order_and_top_k(
    tmp_path: Path,
) -> None:
    sessions, engine = await _open_sessions(
        tmp_path / "ranking.sqlite3"
    )

    try:
        await _seed_scope(sessions)

        async with sessions() as session:
            _add_document_and_chunk(
                session,
                suffix="best",
                tenant_id="tenant-a",
                document_agent_id="agent-a",
                chunk_agent_id="agent-a",
                knowledge_base_id="kb-a",
                status="ready",
                embedding=_vector(1.0, 0.0),
            )

            _add_document_and_chunk(
                session,
                suffix="second",
                tenant_id="tenant-a",
                document_agent_id="agent-a",
                chunk_agent_id="agent-a",
                knowledge_base_id="kb-a",
                status="ready",
                embedding=_vector(0.8, 0.6),
            )

            _add_document_and_chunk(
                session,
                suffix="below-threshold",
                tenant_id="tenant-a",
                document_agent_id="agent-a",
                chunk_agent_id="agent-a",
                knowledge_base_id="kb-a",
                status="ready",
                embedding=_vector(0.0, 1.0),
            )

            await session.commit()

        async with sessions() as session:
            repository = SQLAlchemyChunkRepository(session)

            results = await repository.semantic_search(
                query_embedding=_vector(1.0, 0.0),
                tenant_id="tenant-a",
                agent_id="agent-a",
                knowledge_base_id="kb-a",
                top_k=2,
                min_similarity=0.5,
            )

        assert [chunk.id for chunk, _ in results] == [
            "chunk-best",
            "chunk-second",
        ]

        assert results[0][1] > results[1][1] >= 0.5

    finally:
        await engine.dispose()
