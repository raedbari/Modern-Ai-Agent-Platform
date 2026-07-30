"""Domain ports — abstract contracts for external dependencies.

Re-exports all port interfaces and associated data transfer objects.
"""

from backend.app.domain.ports.embedding_provider import EmbeddingProvider
from backend.app.domain.ports.parser import (
    DocumentParser,
    ParsedDocument,
    ParsedPage,
    ParserFactory,
    SupportedDocumentType,
)
from backend.app.domain.ports.repositories import (
    ChunkRepository,
    DocumentRepository,
    KnowledgeBaseRepository,
)
from backend.app.domain.ports.retrieval import (
    RetrievalPort,
    RetrievalQuery,
    RetrievedChunk,
)

__all__ = [
    "ChunkRepository",
    "DocumentParser",
    "DocumentRepository",
    "EmbeddingProvider",
    "KnowledgeBaseRepository",
    "ParsedDocument",
    "ParsedPage",
    "ParserFactory",
    "RetrievalPort",
    "RetrievalQuery",
    "RetrievedChunk",
    "SupportedDocumentType",
]
