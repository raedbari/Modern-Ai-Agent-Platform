"""Database repository implementations."""
"""Concrete persistence adapters for the knowledge domain."""

from backend.app.infrastructure.database.repositories.sqlalchemy_repositories import (
    SQLAlchemyChunkRepository,
    SQLAlchemyDocumentRepository,
    SQLAlchemyKnowledgeBaseRepository,
)

__all__ = [
    "SQLAlchemyChunkRepository",
    "SQLAlchemyDocumentRepository",
    "SQLAlchemyKnowledgeBaseRepository",
]
