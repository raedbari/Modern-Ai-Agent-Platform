"""Async SQLAlchemy repositories for tenant-safe knowledge persistence."""

from __future__ import annotations

import math
from datetime import datetime, timezone

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import (
    EMBEDDING_DIMENSION,
    AgentKnowledgeBase,
    ChunkModel,
    DocumentModel,
    KnowledgeBaseModel,
)
from backend.app.domain.exceptions import DocumentNotFoundError
from backend.app.domain.models.chunk import Chunk
from backend.app.domain.models.document import Document
from backend.app.domain.models.enums import (
    DocumentProcessingStatus,
    KnowledgeBaseStatus,
)
from backend.app.domain.models.knowledge_base import KnowledgeBase
from backend.app.domain.ports.repositories import (
    ChunkRepository,
    ChunkWrite,
    DocumentRepository,
    KnowledgeBaseRepository,
)


def _document_to_domain(row: DocumentModel) -> Document:
    return Document(
        id=row.id,
        tenant_id=row.tenant_id,
        knowledge_base_id=row.knowledge_base_id,
        agent_id=row.agent_id,
        source_name=row.source_name,
        original_filename=row.original_filename,
        mime_type=row.mime_type,
        file_size_bytes=row.file_size_bytes,
        content_hash=row.content_hash,
        status=DocumentProcessingStatus(row.status),
        failure_reason=row.failure_reason,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _chunk_to_domain(row: ChunkModel) -> Chunk:
    return Chunk(
        id=row.id,
        tenant_id=row.tenant_id,
        agent_id=row.agent_id,
        knowledge_base_id=row.knowledge_base_id,
        document_id=row.document_id,
        source_name=row.source_name,
        page_number=row.page_number,
        chunk_index=row.chunk_index,
        content=row.content,
        content_hash=row.content_hash,
    )


def _knowledge_base_to_domain(row: KnowledgeBaseModel) -> KnowledgeBase:
    return KnowledgeBase(
        id=row.id,
        tenant_id=row.tenant_id,
        name=row.name,
        description=row.description,
        status=KnowledgeBaseStatus(row.status),
    )


class SQLAlchemyDocumentRepository(DocumentRepository):
    """Persist and query documents through one caller-owned transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, document: Document) -> Document:
        row = DocumentModel(
            id=document.id,
            tenant_id=document.tenant_id,
            knowledge_base_id=document.knowledge_base_id,
            agent_id=document.agent_id,
            source_name=document.source_name,
            original_filename=document.original_filename,
            mime_type=document.mime_type,
            file_size_bytes=document.file_size_bytes,
            content_hash=document.content_hash,
            status=document.status.value,
            failure_reason=document.failure_reason,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )
        self._session.add(row)
        await self._session.flush()
        return _document_to_domain(row)

    async def update(self, document: Document) -> Document:
        row = await self._get_row(document.id, document.tenant_id)
        if row is None:
            raise DocumentNotFoundError("Document not found.")

        row.knowledge_base_id = document.knowledge_base_id
        row.agent_id = document.agent_id
        row.source_name = document.source_name
        row.original_filename = document.original_filename
        row.mime_type = document.mime_type
        row.file_size_bytes = document.file_size_bytes
        row.content_hash = document.content_hash
        row.status = document.status.value
        row.failure_reason = document.failure_reason
        row.updated_at = document.updated_at
        await self._session.flush()
        return _document_to_domain(row)

    async def get_by_id(
        self,
        document_id: str,
        tenant_id: str,
    ) -> Document | None:
        row = await self._get_row(document_id, tenant_id)
        return _document_to_domain(row) if row is not None else None

    async def get_by_content_hash(
        self,
        content_hash: str,
        tenant_id: str,
        knowledge_base_id: str,
    ) -> Document | None:
        row = await self._session.scalar(
            select(DocumentModel).where(
                DocumentModel.content_hash == content_hash,
                DocumentModel.tenant_id == tenant_id,
                DocumentModel.knowledge_base_id == knowledge_base_id,
            )
        )
        return _document_to_domain(row) if row is not None else None

    async def list_by_knowledge_base(
        self,
        knowledge_base_id: str,
        tenant_id: str,
    ) -> list[Document]:
        rows = list(
            (
                await self._session.scalars(
                    select(DocumentModel)
                    .where(
                        DocumentModel.knowledge_base_id
                        == knowledge_base_id,
                        DocumentModel.tenant_id == tenant_id,
                    )
                    .order_by(
                        DocumentModel.created_at,
                        DocumentModel.id,
                    )
                )
            ).all()
        )
        return [_document_to_domain(row) for row in rows]

    async def update_processing_status(
        self,
        document_id: str,
        tenant_id: str,
        status: DocumentProcessingStatus,
        failure_reason: str | None = None,
    ) -> None:
        result = await self._session.execute(
            update(DocumentModel)
            .where(
                DocumentModel.id == document_id,
                DocumentModel.tenant_id == tenant_id,
            )
            .values(
                status=status.value,
                failure_reason=failure_reason,
                updated_at=datetime.now(timezone.utc),
            )
        )
        if result.rowcount != 1:
            raise DocumentNotFoundError("Document not found.")
        await self._session.flush()

    async def _get_row(
        self,
        document_id: str,
        tenant_id: str,
    ) -> DocumentModel | None:
        return await self._session.scalar(
            select(DocumentModel).where(
                DocumentModel.id == document_id,
                DocumentModel.tenant_id == tenant_id,
            )
        )


class SQLAlchemyChunkRepository(ChunkRepository):
    """Store vectors and execute tenant-first cosine similarity search."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        embedding_dimension: int = EMBEDDING_DIMENSION,
    ) -> None:
        if embedding_dimension != EMBEDDING_DIMENSION:
            raise ValueError(
                "The repository dimension must match vector(1024)."
            )
        self._session = session
        self._embedding_dimension = embedding_dimension

    async def create_many(self, records: list[ChunkWrite]) -> list[Chunk]:
        if not records:
            return []

        scope = (
            records[0].chunk.tenant_id,
            records[0].chunk.agent_id,
        )
        rows: list[ChunkModel] = []
        for record in records:
            if (
                record.chunk.tenant_id,
                record.chunk.agent_id,
            ) != scope:
                raise ValueError(
                    "All chunks in one batch must share tenant and agent."
                )
            vector = self._validated_vector(record.embedding)
            rows.append(
                ChunkModel(
                    id=record.chunk.id,
                    tenant_id=record.chunk.tenant_id,
                    agent_id=record.chunk.agent_id,
                    knowledge_base_id=record.chunk.knowledge_base_id,
                    document_id=record.chunk.document_id,
                    source_name=record.chunk.source_name,
                    page_number=record.chunk.page_number,
                    chunk_index=record.chunk.chunk_index,
                    content=record.chunk.content,
                    content_hash=record.chunk.content_hash,
                    embedding=vector,
                )
            )

        self._session.add_all(rows)
        await self._session.flush()
        return [record.chunk for record in records]

    async def delete_by_document(
        self,
        document_id: str,
        tenant_id: str,
    ) -> int:
        result = await self._session.execute(
            delete(ChunkModel).where(
                ChunkModel.document_id == document_id,
                ChunkModel.tenant_id == tenant_id,
            )
        )
        await self._session.flush()
        return int(result.rowcount or 0)

    async def list_by_document(
        self,
        document_id: str,
        tenant_id: str,
    ) -> list[Chunk]:
        rows = list(
            (
                await self._session.scalars(
                    select(ChunkModel)
                    .where(
                        ChunkModel.document_id == document_id,
                        ChunkModel.tenant_id == tenant_id,
                    )
                    .order_by(ChunkModel.chunk_index, ChunkModel.id)
                )
            ).all()
        )
        return [_chunk_to_domain(row) for row in rows]

    async def semantic_search(
        self,
        query_embedding: list[float],
        tenant_id: str,
        agent_id: str,
        knowledge_base_id: str,
        top_k: int,
        min_similarity: float,
    ) -> list[tuple[Chunk, float]]:
        vector = self._validated_vector(query_embedding)
        if top_k <= 0:
            raise ValueError("top_k must be positive.")
        if not 0.0 <= min_similarity <= 1.0:
            raise ValueError("min_similarity must be between 0.0 and 1.0.")

        bind = self._session.get_bind()
        if bind.dialect.name == "sqlite":
            return await self._sqlite_semantic_search(
                vector=vector,
                tenant_id=tenant_id,
                agent_id=agent_id,
                knowledge_base_id=knowledge_base_id,
                top_k=top_k,
                min_similarity=min_similarity,
            )

        distance = ChunkModel.embedding.cosine_distance(vector)
        similarity = (1.0 - distance).label("similarity")
        rows = (
            await self._session.execute(
                select(ChunkModel, similarity)
                .where(
                    ChunkModel.tenant_id == tenant_id,
                    ChunkModel.agent_id == agent_id,
                    ChunkModel.knowledge_base_id == knowledge_base_id,
                    similarity >= min_similarity,
                )
                .order_by(distance, ChunkModel.id)
                .limit(top_k)
            )
        ).all()
        return [
            (_chunk_to_domain(row), float(score))
            for row, score in rows
        ]

    async def _sqlite_semantic_search(
        self,
        *,
        vector: list[float],
        tenant_id: str,
        agent_id: str,
        knowledge_base_id: str,
        top_k: int,
        min_similarity: float,
    ) -> list[tuple[Chunk, float]]:
        """Exact fallback used only by SQLite tests and local development."""

        rows = list(
            (
                await self._session.scalars(
                    select(ChunkModel).where(
                        ChunkModel.tenant_id == tenant_id,
                        ChunkModel.agent_id == agent_id,
                        ChunkModel.knowledge_base_id == knowledge_base_id,
                    )
                )
            ).all()
        )
        scored = [
            (row, self._cosine_similarity(vector, row.embedding))
            for row in rows
        ]
        filtered = [
            (row, score)
            for row, score in scored
            if score >= min_similarity
        ]
        filtered.sort(key=lambda item: (-item[1], item[0].id))
        return [
            (_chunk_to_domain(row), score)
            for row, score in filtered[:top_k]
        ]

    def _validated_vector(
        self,
        embedding: tuple[float, ...] | list[float],
    ) -> list[float]:
        if len(embedding) != self._embedding_dimension:
            raise ValueError(
                f"Embedding dimension must be {self._embedding_dimension}."
            )
        vector = [float(value) for value in embedding]
        if not all(math.isfinite(value) for value in vector):
            raise ValueError("Embedding values must be finite.")
        return vector

    @staticmethod
    def _cosine_similarity(
        left: list[float],
        right: list[float],
    ) -> float:
        dot_product = sum(a * b for a, b in zip(left, right))
        left_norm = math.sqrt(sum(value * value for value in left))
        right_norm = math.sqrt(sum(value * value for value in right))
        if left_norm == 0.0 or right_norm == 0.0:
            return 0.0
        score = dot_product / (left_norm * right_norm)
        return max(-1.0, min(1.0, score))


class SQLAlchemyKnowledgeBaseRepository(KnowledgeBaseRepository):
    """Resolve knowledge bases with explicit tenant and agent scoping."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(
        self,
        knowledge_base_id: str,
        tenant_id: str,
    ) -> KnowledgeBase | None:
        row = await self._session.scalar(
            select(KnowledgeBaseModel).where(
                KnowledgeBaseModel.id == knowledge_base_id,
                KnowledgeBaseModel.tenant_id == tenant_id,
            )
        )
        return _knowledge_base_to_domain(row) if row is not None else None

    async def list_for_agent(
        self,
        agent_id: str,
        tenant_id: str,
    ) -> list[KnowledgeBase]:
        rows = list(
            (
                await self._session.scalars(
                    select(KnowledgeBaseModel)
                    .join(
                        AgentKnowledgeBase,
                        (
                            AgentKnowledgeBase.knowledge_base_id
                            == KnowledgeBaseModel.id
                        )
                        & (
                            AgentKnowledgeBase.tenant_id
                            == KnowledgeBaseModel.tenant_id
                        ),
                    )
                    .where(
                        AgentKnowledgeBase.agent_id == agent_id,
                        AgentKnowledgeBase.tenant_id == tenant_id,
                        KnowledgeBaseModel.tenant_id == tenant_id,
                    )
                    .order_by(
                        KnowledgeBaseModel.name,
                        KnowledgeBaseModel.id,
                    )
                )
            ).all()
        )
        return [_knowledge_base_to_domain(row) for row in rows]

    async def exists_for_tenant(
        self,
        knowledge_base_id: str,
        tenant_id: str,
    ) -> bool:
        value = await self._session.scalar(
            select(KnowledgeBaseModel.id)
            .where(
                KnowledgeBaseModel.id == knowledge_base_id,
                KnowledgeBaseModel.tenant_id == tenant_id,
            )
            .limit(1)
        )
        return value is not None
