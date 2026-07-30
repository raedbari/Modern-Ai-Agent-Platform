"""Tests for domain port contracts and data transfer objects.

Verifies:
- All port interfaces can be imported without error.
- All port interfaces are abstract (cannot be instantiated directly).
- Data transfer objects (RetrievalQuery, RetrievedChunk) can be constructed.
- DTOs enforce immutability where appropriate (frozen dataclasses).
"""

import pytest
from abc import ABC

from backend.app.domain.models.chunk import Chunk
from backend.app.domain.models.document import Document
from backend.app.domain.models.enums import DocumentProcessingStatus
from backend.app.domain.models.knowledge_base import KnowledgeBase

from backend.app.domain.ports.repositories import (
    ChunkRepository,
    DocumentRepository,
    KnowledgeBaseRepository,
)
from backend.app.domain.ports.embedding_provider import EmbeddingProvider
from backend.app.domain.ports.retrieval import (
    RetrievalPort,
    RetrievalQuery,
    RetrievedChunk,
)


# ---------------------------------------------------------------------------
# Repository contracts
# ---------------------------------------------------------------------------


class TestDocumentRepository:
    def test_is_abstract(self) -> None:
        """DocumentRepository cannot be instantiated directly."""
        with pytest.raises(TypeError):
            DocumentRepository()  # type: ignore

    def test_is_abc(self) -> None:
        """DocumentRepository inherits from ABC."""
        assert issubclass(DocumentRepository, ABC)

    def test_has_expected_methods(self) -> None:
        """All declared abstract methods are present."""
        methods = {
            "create",
            "update",
            "get_by_id",
            "get_by_content_hash",
            "list_by_knowledge_base",
            "update_processing_status",
        }
        assert methods <= set(dir(DocumentRepository))


class TestChunkRepository:
    def test_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            ChunkRepository()  # type: ignore

    def test_is_abc(self) -> None:
        assert issubclass(ChunkRepository, ABC)

    def test_has_expected_methods(self) -> None:
        methods = {
            "create_many",
            "delete_by_document",
            "list_by_document",
            "semantic_search",
        }
        assert methods <= set(dir(ChunkRepository))


class TestKnowledgeBaseRepository:
    def test_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            KnowledgeBaseRepository()  # type: ignore

    def test_is_abc(self) -> None:
        assert issubclass(KnowledgeBaseRepository, ABC)

    def test_has_expected_methods(self) -> None:
        methods = {
            "get_by_id",
            "list_for_agent",
            "exists_for_tenant",
        }
        assert methods <= set(dir(KnowledgeBaseRepository))


# ---------------------------------------------------------------------------
# EmbeddingProvider contract
# ---------------------------------------------------------------------------


class TestEmbeddingProvider:
    def test_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            EmbeddingProvider()  # type: ignore

    def test_is_abc(self) -> None:
        assert issubclass(EmbeddingProvider, ABC)

    def test_has_expected_methods(self) -> None:
        methods = {"embed_text", "embed_batch"}
        assert methods <= set(dir(EmbeddingProvider))


# ---------------------------------------------------------------------------
# RetrievalPort contract
# ---------------------------------------------------------------------------


class TestRetrievalPort:
    def test_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            RetrievalPort()  # type: ignore

    def test_is_abc(self) -> None:
        assert issubclass(RetrievalPort, ABC)

    def test_has_retrieve_method(self) -> None:
        assert "retrieve" in dir(RetrievalPort)


# ---------------------------------------------------------------------------
# Data transfer objects
# ---------------------------------------------------------------------------


class TestRetrievalQuery:
    def test_construction(self) -> None:
        q = RetrievalQuery(
            tenant_id="t-1",
            agent_id="a-1",
            query="What is the refund policy?",
            top_k=5,
            min_similarity=0.5,
        )
        assert q.tenant_id == "t-1"
        assert q.agent_id == "a-1"
        assert q.query == "What is the refund policy?"
        assert q.top_k == 5
        assert q.min_similarity == 0.5

    def test_is_frozen(self) -> None:
        """RetrievalQuery is immutable."""
        q = RetrievalQuery(
            tenant_id="t-1",
            agent_id="a-1",
            query="Query",
            top_k=5,
            min_similarity=0.5,
        )
        with pytest.raises(AttributeError):
            q.tenant_id = "t-2"  # type: ignore


class TestRetrievedChunk:
    def test_construction(self) -> None:
        chunk = Chunk(
            id="c-1",
            tenant_id="t-1",
            agent_id="a-1",
            knowledge_base_id="kb-1",
            document_id="doc-1",
            source_name="upload",
            page_number=0,
            chunk_index=0,
            content="Some content",
            content_hash="abc123",
        )
        retrieved = RetrievedChunk(chunk=chunk, similarity_score=0.85)
        assert retrieved.chunk == chunk
        assert retrieved.similarity_score == 0.85

    def test_is_frozen(self) -> None:
        """RetrievedChunk is immutable."""
        chunk = Chunk(
            id="c-1",
            tenant_id="t-1",
            agent_id="a-1",
            knowledge_base_id="kb-1",
            document_id="doc-1",
            source_name="upload",
            page_number=0,
            chunk_index=0,
            content="Content",
            content_hash="abc",
        )
        retrieved = RetrievedChunk(chunk=chunk, similarity_score=0.9)
        with pytest.raises(AttributeError):
            retrieved.similarity_score = 0.95  # type: ignore


# ---------------------------------------------------------------------------
# Package exports
# ---------------------------------------------------------------------------


class TestPortsPackageExports:
    def test_all_ports_exported(self) -> None:
        """All port interfaces and DTOs are re-exported from __init__."""
        from backend.app.domain.ports import (
            ChunkRepository,
            DocumentRepository,
            EmbeddingProvider,
            KnowledgeBaseRepository,
            RetrievalPort,
            RetrievalQuery,
            RetrievedChunk,
        )
        # If the import succeeds, the exports are correct.
        assert ChunkRepository is not None
        assert DocumentRepository is not None
        assert EmbeddingProvider is not None
        assert KnowledgeBaseRepository is not None
        assert RetrievalPort is not None
        assert RetrievalQuery is not None
        assert RetrievedChunk is not None
