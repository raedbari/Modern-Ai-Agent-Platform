"""Composition root for document ingestion services."""

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.ai.ports import EmbeddingProvider
from backend.app.core.config import Settings
from backend.app.infrastructure.database.repositories import (
    SQLAlchemyChunkRepository,
    SQLAlchemyDocumentRepository,
    SQLAlchemyKnowledgeBaseRepository,
)
from backend.app.infrastructure.parsers.factory import DefaultParserFactory
from backend.app.services.knowledge.chunking_service import ChunkingService
from backend.app.services.knowledge.embedding_service import EmbeddingService
from backend.app.services.knowledge.ingestion_service import IngestionService


def build_ingestion_service(
    *,
    session: AsyncSession,
    runtime: EmbeddingProvider,
    settings: Settings,
) -> IngestionService:
    """Assemble the production ingestion pipeline for one DB transaction."""

    return IngestionService(
        parser_factory=DefaultParserFactory(),
        chunking_service=ChunkingService(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        ),
        embedding_service=EmbeddingService(
            provider=runtime,
            batch_size=settings.embedding_batch_size,
            embedding_dimensions=settings.embedding_dimension,
        ),
        document_repository=SQLAlchemyDocumentRepository(session),
        chunk_repository=SQLAlchemyChunkRepository(
            session,
            embedding_dimension=settings.embedding_dimension,
        ),
        knowledge_base_repository=SQLAlchemyKnowledgeBaseRepository(session),
        max_upload_size_bytes=settings.max_upload_size_bytes,
        max_pdf_pages=settings.max_pdf_pages,
        allowed_extensions=settings.allowed_extensions,
        allowed_mime_types=settings.allowed_mime_types,
    )
