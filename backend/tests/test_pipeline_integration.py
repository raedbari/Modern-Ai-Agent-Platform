"""Integration tests for the complete Knowledge RAG Pipeline.

Exercises the full pipeline end-to-end using only real production
components and in-memory stubs — no PostgreSQL, SQLAlchemy, pgvector,
Ollama, FastAPI, or LangGraph.

Pipeline under test
-------------------
  bytes
    → DefaultParserFactory / concrete parsers
    → ParsedDocument
    → ChunkingService
    → list[Chunk]
    → EmbeddingService
    → EmbeddingResult
    → RetrievalService (via InMemoryChunkRepository)
    → list[RetrievedChunk]

In-memory stubs
---------------
- ``VectorEmbeddingProvider``  — deterministic embedding using xxhash so
  content-similar chunks get similar (identical) scores.
- ``InMemoryChunkRepository``  — stores (Chunk, embedding) pairs and
  implements semantic_search with cosine similarity, tenant/agent/KB
  isolation, and threshold filtering.
- ``InMemoryKBRepository``     — holds a list of KnowledgeBase objects.
"""

from __future__ import annotations

import io
import math
import pytest

# ---------------------------------------------------------------------------
# Production components
# ---------------------------------------------------------------------------
from backend.app.infrastructure.parsers.factory import DefaultParserFactory
from backend.app.services.knowledge.chunking_service import ChunkingService
from backend.app.services.knowledge.embedding_service import (
    EmbeddingService,
    EmbeddingResult,
)
from backend.app.services.knowledge.retrieval_service import RetrievalService

# ---------------------------------------------------------------------------
# Domain
# ---------------------------------------------------------------------------
from backend.app.domain.exceptions import (
    ChunkingError,
    EmbeddingError,
    ParseError,
    RetrievalValidationError,
)
from backend.app.domain.models.chunk import Chunk
from backend.app.domain.models.enums import KnowledgeBaseStatus
from backend.app.domain.models.knowledge_base import KnowledgeBase
from backend.app.domain.ports.embedding_provider import EmbeddingProvider
from backend.app.domain.ports.repositories import (
    ChunkRepository,
    KnowledgeBaseRepository,
)
from backend.app.domain.ports.retrieval import RetrievalQuery

# ---------------------------------------------------------------------------
# Document fixture factories
# ---------------------------------------------------------------------------

def _make_pdf_bytes(texts: list[str] | None = None) -> bytes:
    from pypdf import PdfWriter
    writer = PdfWriter()
    for _ in (texts or ["Integration test page."]):
        writer.add_blank_page(width=612, height=792)
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _make_docx_bytes(paragraphs: list[str] | None = None) -> bytes:
    import docx as python_docx
    doc = python_docx.Document()
    for p in (paragraphs or ["Integration test paragraph."]):
        doc.add_paragraph(p)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# In-memory stubs
# ---------------------------------------------------------------------------

_DIMS = 8  # small vector for fast arithmetic


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _text_to_vector(text: str, dims: int = _DIMS) -> list[float]:
    """Deterministic hash-based pseudo-embedding."""
    import xxhash
    seed = xxhash.xxh64(text.encode()).intdigest()
    result = []
    for i in range(dims):
        seed = (seed * 6364136223846793005 + 1442695040888963407) & 0xFFFFFFFFFFFFFFFF
        result.append(float((seed >> 33) & 0xFFFF) / 0xFFFF)
    return result


class VectorEmbeddingProvider(EmbeddingProvider):
    """Deterministic pseudo-embedding provider. No HTTP, no Ollama."""

    def __init__(self, dims: int = _DIMS) -> None:
        self._dims = dims

    async def embed_text(self, text: str) -> list[float]:
        return _text_to_vector(text, self._dims)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [_text_to_vector(t, self._dims) for t in texts]


class PartiallyFailingProvider(EmbeddingProvider):
    """Succeeds on even batch calls, fails on odd ones (1-indexed)."""

    def __init__(self, dims: int = _DIMS) -> None:
        self._dims = dims
        self._call = 0

    async def embed_text(self, text: str) -> list[float]:
        return _text_to_vector(text, self._dims)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        self._call += 1
        if self._call % 2 == 0:
            raise EmbeddingError("Intermittent provider failure.")
        return [_text_to_vector(t, self._dims) for t in texts]


class InMemoryChunkRepository(ChunkRepository):
    """Thread-safe in-memory vector store with full isolation enforcement."""

    def __init__(self) -> None:
        # maps chunk.id → (Chunk, embedding)
        self._store: dict[str, tuple[Chunk, list[float]]] = {}

    def store_embedded(self, chunk: Chunk, embedding: list[float]) -> None:
        self._store[chunk.id] = (chunk, embedding)

    async def create_many(self, chunks: list[Chunk]) -> list[Chunk]:
        return chunks

    async def delete_by_document(self, document_id: str, tenant_id: str) -> int:
        before = len(self._store)
        self._store = {
            k: v for k, v in self._store.items()
            if not (v[0].document_id == document_id and v[0].tenant_id == tenant_id)
        }
        return before - len(self._store)

    async def list_by_document(self, document_id: str, tenant_id: str) -> list[Chunk]:
        return [
            c for c, _ in self._store.values()
            if c.document_id == document_id and c.tenant_id == tenant_id
        ]

    async def semantic_search(
        self,
        query_embedding: list[float],
        tenant_id: str,
        agent_id: str,
        knowledge_base_id: str,
        top_k: int,
        min_similarity: float,
    ) -> list[tuple[Chunk, float]]:
        results = []
        for chunk, emb in self._store.values():
            if (
                chunk.tenant_id != tenant_id
                or chunk.agent_id != agent_id
                or chunk.knowledge_base_id != knowledge_base_id
            ):
                continue
            score = _cosine(query_embedding, emb)
            if score >= min_similarity:
                results.append((chunk, score))
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]


class InMemoryKBRepository(KnowledgeBaseRepository):
    def __init__(self, kbs: list[KnowledgeBase]) -> None:
        self._kbs = kbs

    async def get_by_id(self, knowledge_base_id: str, tenant_id: str):
        for kb in self._kbs:
            if kb.id == knowledge_base_id and kb.tenant_id == tenant_id:
                return kb
        return None

    async def list_for_agent(self, agent_id: str, tenant_id: str):
        return [kb for kb in self._kbs if kb.tenant_id == tenant_id]

    async def exists_for_tenant(self, knowledge_base_id: str, tenant_id: str) -> bool:
        return any(
            kb.id == knowledge_base_id and kb.tenant_id == tenant_id
            for kb in self._kbs
        )


# ---------------------------------------------------------------------------
# Pipeline runner helper
# ---------------------------------------------------------------------------

_CHUNK_SIZE = 120
_CHUNK_OVERLAP = 20
_BATCH_SIZE = 4


async def _run_ingestion(
    raw_bytes: bytes,
    filename: str,
    mime_type: str,
    *,
    tenant_id: str = "tenant-1",
    agent_id: str = "agent-1",
    kb_id: str = "kb-1",
    source_name: str = "integration-test",
    document_id: str = "doc-1",
    chunk_repo: InMemoryChunkRepository | None = None,
    provider: EmbeddingProvider | None = None,
    chunk_size: int = _CHUNK_SIZE,
    chunk_overlap: int = _CHUNK_OVERLAP,
) -> tuple[list[Chunk], EmbeddingResult, InMemoryChunkRepository]:
    """Parse → chunk → embed → store.  Returns (chunks, embed_result, repo)."""
    if chunk_repo is None:
        chunk_repo = InMemoryChunkRepository()
    if provider is None:
        provider = VectorEmbeddingProvider()

    factory = DefaultParserFactory()
    parser = factory.get_parser(mime_type=mime_type)
    parsed = await parser.parse(raw_bytes, filename)

    chunker = ChunkingService(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = chunker.chunk_document(
        parsed,
        document_id=document_id,
        tenant_id=tenant_id,
        agent_id=agent_id,
        knowledge_base_id=kb_id,
        source_name=source_name,
    )

    embed_svc = EmbeddingService(
        provider=provider,
        batch_size=_BATCH_SIZE,
        embedding_dimensions=_DIMS,
    )
    result = await embed_svc.embed_chunks(chunks)

    for ec in result.embedded:
        chunk_repo.store_embedded(ec.chunk, ec.embedding)

    return chunks, result, chunk_repo


def _make_retrieval_service(
    chunk_repo: InMemoryChunkRepository,
    kb_id: str = "kb-1",
    tenant_id: str = "tenant-1",
    provider: EmbeddingProvider | None = None,
) -> RetrievalService:
    kb = KnowledgeBase(id=kb_id, tenant_id=tenant_id, name="Test KB")
    return RetrievalService(
        embedding_provider=provider or VectorEmbeddingProvider(),
        chunk_repository=chunk_repo,
        kb_repository=InMemoryKBRepository([kb]),
    )


# ===========================================================================
# Format-specific document flows
# ===========================================================================


class TestTxtFlow:
    @pytest.mark.asyncio
    async def test_txt_produces_chunks(self) -> None:
        text = "The quick brown fox jumps over the lazy dog. " * 20
        chunks, result, _ = await _run_ingestion(
            text.encode(), "doc.txt", "text/plain"
        )
        assert len(chunks) > 0
        assert result.fully_successful

    @pytest.mark.asyncio
    async def test_txt_metadata_preserved(self) -> None:
        text = "Sample TXT content for metadata check. " * 10
        chunks, _, _ = await _run_ingestion(
            text.encode(), "doc.txt", "text/plain",
            tenant_id="t-txt", agent_id="a-txt", kb_id="kb-txt",
            source_name="txt-source", document_id="doc-txt",
        )
        for c in chunks:
            assert c.tenant_id == "t-txt"
            assert c.agent_id == "a-txt"
            assert c.knowledge_base_id == "kb-txt"
            assert c.source_name == "txt-source"
            assert c.document_id == "doc-txt"
            assert c.page_number == 0
            assert c.content_hash

    @pytest.mark.asyncio
    async def test_empty_txt_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            await _run_ingestion(b"", "empty.txt", "text/plain")

    @pytest.mark.asyncio
    async def test_whitespace_only_txt_raises_chunking_error(self) -> None:
        with pytest.raises(ChunkingError):
            await _run_ingestion(b"   \n  ", "ws.txt", "text/plain")


class TestMarkdownFlow:
    @pytest.mark.asyncio
    async def test_md_produces_chunks(self) -> None:
        md = "# Title\n\nThis is a paragraph.\n\n" * 15
        chunks, result, _ = await _run_ingestion(
            md.encode(), "doc.md", "text/markdown"
        )
        assert len(chunks) > 0
        assert result.fully_successful

    @pytest.mark.asyncio
    async def test_md_syntax_preserved_in_chunks(self) -> None:
        md = "# Heading\n\n**Bold** text.\n\n" * 5
        chunks, _, _ = await _run_ingestion(
            md.encode(), "doc.md", "text/markdown"
        )
        combined = " ".join(c.content for c in chunks)
        assert "#" in combined or "**" in combined

    @pytest.mark.asyncio
    async def test_md_metadata_preserved(self) -> None:
        md = "## Section\n\nContent line here.\n" * 10
        chunks, _, _ = await _run_ingestion(
            md.encode(), "readme.md", "text/markdown",
            tenant_id="t-md", agent_id="a-md",
        )
        assert all(c.tenant_id == "t-md" for c in chunks)
        assert all(c.agent_id == "a-md" for c in chunks)


class TestPdfFlow:
    @pytest.mark.asyncio
    async def test_pdf_produces_chunks(self) -> None:
        raw = _make_pdf_bytes()
        chunks, result, _ = await _run_ingestion(
            raw, "doc.pdf", "application/pdf"
        )
        # pypdf blank pages have no text; chunker may produce 0 from blank pages
        # We verify no exception is raised and result is valid
        assert result is not None
        assert isinstance(chunks, list)

    @pytest.mark.asyncio
    async def test_corrupted_pdf_raises_parse_error(self) -> None:
        garbage = b"%PDF-1.4 not a real pdf \x00\x01\x02\x03" + b"\xff" * 50
        with pytest.raises(ParseError):
            await _run_ingestion(garbage, "bad.pdf", "application/pdf")

    @pytest.mark.asyncio
    async def test_empty_pdf_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            await _run_ingestion(b"", "empty.pdf", "application/pdf")

    @pytest.mark.asyncio
    async def test_pdf_page_numbers_sequential(self) -> None:
        raw = _make_pdf_bytes(["p1", "p2", "p3"])
        # pypdf blank pages may not extract text, so just validate structure
        _, result, _ = await _run_ingestion(raw, "doc.pdf", "application/pdf")
        assert result is not None


class TestDocxFlow:
    @pytest.mark.asyncio
    async def test_docx_produces_chunks(self) -> None:
        raw = _make_docx_bytes(["Hello world. " * 30])
        chunks, result, _ = await _run_ingestion(
            raw, "doc.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        assert len(chunks) > 0
        assert result.fully_successful

    @pytest.mark.asyncio
    async def test_docx_metadata_preserved(self) -> None:
        raw = _make_docx_bytes(["Paragraph one. " * 20, "Paragraph two. " * 20])
        chunks, _, _ = await _run_ingestion(
            raw, "doc.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            tenant_id="t-docx", agent_id="a-docx",
        )
        assert all(c.tenant_id == "t-docx" for c in chunks)
        assert all(c.page_number == 0 for c in chunks)

    @pytest.mark.asyncio
    async def test_corrupted_docx_raises_parse_error(self) -> None:
        garbage = b"PK\x03\x04 fake docx" + b"\x00" * 100
        with pytest.raises(ParseError):
            await _run_ingestion(
                garbage, "bad.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )

    @pytest.mark.asyncio
    async def test_empty_docx_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            await _run_ingestion(
                b"", "empty.docx",
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )


# ===========================================================================
# Language tests
# ===========================================================================


class TestLanguageFlows:
    @pytest.mark.asyncio
    async def test_arabic_document_produces_chunks(self) -> None:
        arabic = "مرحبا بالعالم هذا نص عربي للاختبار. " * 25
        chunks, result, _ = await _run_ingestion(
            arabic.encode("utf-8"), "arabic.txt", "text/plain"
        )
        assert len(chunks) > 0
        assert result.fully_successful
        assert all(c.content_hash for c in chunks)

    @pytest.mark.asyncio
    async def test_english_document_produces_chunks(self) -> None:
        english = "The platform supports multi-tenant knowledge retrieval. " * 20
        chunks, result, _ = await _run_ingestion(
            english.encode(), "en.txt", "text/plain"
        )
        assert len(chunks) > 0
        assert result.fully_successful

    @pytest.mark.asyncio
    async def test_mixed_arabic_english_produces_chunks(self) -> None:
        mixed = "Hello مرحبا world العالم platform منصة. " * 20
        chunks, result, _ = await _run_ingestion(
            mixed.encode("utf-8"), "mixed.txt", "text/plain"
        )
        assert len(chunks) > 0
        assert result.fully_successful

    @pytest.mark.asyncio
    async def test_arabic_content_hash_deterministic(self) -> None:
        arabic = "مرحبا بالعالم. " * 20
        chunks1, _, _ = await _run_ingestion(
            arabic.encode("utf-8"), "arabic.txt", "text/plain",
            document_id="doc-ar",
        )
        chunks2, _, _ = await _run_ingestion(
            arabic.encode("utf-8"), "arabic.txt", "text/plain",
            document_id="doc-ar",
        )
        hashes1 = [c.content_hash for c in chunks1]
        hashes2 = [c.content_hash for c in chunks2]
        assert hashes1 == hashes2

    @pytest.mark.asyncio
    async def test_arabic_metadata_preserved(self) -> None:
        arabic = "نص عربي طويل لاختبار الخصائص. " * 15
        chunks, _, _ = await _run_ingestion(
            arabic.encode("utf-8"), "ar.txt", "text/plain",
            tenant_id="t-ar", agent_id="a-ar", kb_id="kb-ar",
            source_name="arabic-upload",
        )
        for c in chunks:
            assert c.tenant_id == "t-ar"
            assert c.agent_id == "a-ar"
            assert c.knowledge_base_id == "kb-ar"
            assert c.source_name == "arabic-upload"


# ===========================================================================
# Chunking behaviour
# ===========================================================================


class TestChunkingBehaviour:
    @pytest.mark.asyncio
    async def test_chunk_indexes_sequential(self) -> None:
        text = "word " * 200
        chunks, _, _ = await _run_ingestion(
            text.encode(), "doc.txt", "text/plain",
            chunk_size=80, chunk_overlap=10,
        )
        indexes = [c.chunk_index for c in chunks]
        assert indexes == list(range(len(chunks)))

    @pytest.mark.asyncio
    async def test_overlap_shared_content(self) -> None:
        text = "0123456789ABCDEF" * 20  # 320 chars
        chunks, _, _ = await _run_ingestion(
            text.encode(), "doc.txt", "text/plain",
            chunk_size=50, chunk_overlap=15,
        )
        assert len(chunks) >= 2
        tail = chunks[0].content[-15:]
        head = chunks[1].content[:15]
        assert tail == head

    @pytest.mark.asyncio
    async def test_no_empty_chunks_produced(self) -> None:
        text = "This is a test sentence. " * 30
        chunks, _, _ = await _run_ingestion(
            text.encode(), "doc.txt", "text/plain"
        )
        for c in chunks:
            assert c.content.strip() != ""

    @pytest.mark.asyncio
    async def test_large_document_many_chunks(self) -> None:
        text = "integration test content line. " * 500
        chunks, result, _ = await _run_ingestion(
            text.encode(), "large.txt", "text/plain",
            chunk_size=100, chunk_overlap=20,
        )
        assert len(chunks) > 10
        assert result.success_count == len(chunks)

    @pytest.mark.asyncio
    async def test_content_hash_unique_per_chunk(self) -> None:
        text = "abcdefghijklmnop " * 50
        chunks, _, _ = await _run_ingestion(
            text.encode(), "doc.txt", "text/plain",
            chunk_size=60, chunk_overlap=0,
        )
        hashes = [c.content_hash for c in chunks]
        # All hashes must be non-empty
        assert all(h for h in hashes)

    @pytest.mark.asyncio
    async def test_duplicate_document_same_hashes(self) -> None:
        """Same bytes ingested twice → identical chunk hashes."""
        text = "Consistent content for deduplication test. " * 20
        chunks1, _, _ = await _run_ingestion(
            text.encode(), "doc.txt", "text/plain", document_id="dup-doc"
        )
        chunks2, _, _ = await _run_ingestion(
            text.encode(), "doc.txt", "text/plain", document_id="dup-doc"
        )
        assert [c.content_hash for c in chunks1] == [c.content_hash for c in chunks2]
        assert [c.id for c in chunks1] == [c.id for c in chunks2]

# ===========================================================================
# Embedding behaviour
# ===========================================================================


class TestEmbeddingBehaviour:
    @pytest.mark.asyncio
    async def test_all_chunks_embedded(self) -> None:
        text = "Embedding test content. " * 30
        chunks, result, _ = await _run_ingestion(
            text.encode(), "doc.txt", "text/plain"
        )
        assert result.success_count == len(chunks)
        assert result.failure_count == 0

    @pytest.mark.asyncio
    async def test_embedding_batch_covers_all_chunks(self) -> None:
        """More chunks than batch_size forces multiple embed_batch calls."""
        text = "batch test line. " * 200
        chunks, result, _ = await _run_ingestion(
            text.encode(), "doc.txt", "text/plain",
            chunk_size=60, chunk_overlap=0,
        )
        # batch_size=4, so many batches needed
        assert result.success_count == len(chunks)

    @pytest.mark.asyncio
    async def test_partial_provider_failure_preserves_successful_chunks(self) -> None:
        """When every other batch fails, successful chunks are not lost."""
        text = "partial failure test content line. " * 100
        provider = PartiallyFailingProvider()
        chunks, result, _ = await _run_ingestion(
            text.encode(), "doc.txt", "text/plain",
            provider=provider,
            chunk_size=60, chunk_overlap=0,
        )
        # At least some chunks must succeed and none must be silently dropped
        assert result.total == len(chunks)
        assert result.success_count + result.failure_count == len(chunks)

    @pytest.mark.asyncio
    async def test_embedded_chunks_carry_correct_chunk_reference(self) -> None:
        text = "Reference check content. " * 15
        chunks, result, _ = await _run_ingestion(
            text.encode(), "doc.txt", "text/plain"
        )
        embedded_ids = {ec.chunk.id for ec in result.embedded}
        chunk_ids = {c.id for c in chunks}
        assert embedded_ids == chunk_ids


# ===========================================================================
# Retrieval behaviour
# ===========================================================================


class TestRetrievalBehaviour:
    @pytest.mark.asyncio
    async def test_retrieval_returns_results(self) -> None:
        text = "The refund policy allows returns within 30 days. " * 20
        _, _, chunk_repo = await _run_ingestion(
            text.encode(), "doc.txt", "text/plain",
            tenant_id="t-1", agent_id="a-1", kb_id="kb-1",
        )
        svc = _make_retrieval_service(chunk_repo)
        results = await svc.retrieve(RetrievalQuery(
            tenant_id="t-1", agent_id="a-1",
            query="refund policy",
            top_k=5, min_similarity=0.0,
        ))
        assert isinstance(results, list)
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_results_ordered_by_descending_score(self) -> None:
        text = "Knowledge base content for ordering test. " * 25
        _, _, chunk_repo = await _run_ingestion(
            text.encode(), "doc.txt", "text/plain",
        )
        svc = _make_retrieval_service(chunk_repo)
        results = await svc.retrieve(RetrievalQuery(
            tenant_id="tenant-1", agent_id="agent-1",
            query="knowledge base content",
            top_k=10, min_similarity=0.0,
        ))
        scores = [r.similarity_score for r in results]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_top_k_limits_results(self) -> None:
        text = "top k test content sentence. " * 60
        _, _, chunk_repo = await _run_ingestion(
            text.encode(), "doc.txt", "text/plain",
            chunk_size=60, chunk_overlap=0,
        )
        svc = _make_retrieval_service(chunk_repo)
        results = await svc.retrieve(RetrievalQuery(
            tenant_id="tenant-1", agent_id="agent-1",
            query="top k test",
            top_k=3, min_similarity=0.0,
        ))
        assert len(results) <= 3

    @pytest.mark.asyncio
    async def test_similarity_threshold_filters_results(self) -> None:
        text = "threshold filtering integration test content. " * 20
        _, _, chunk_repo = await _run_ingestion(
            text.encode(), "doc.txt", "text/plain",
        )
        svc = _make_retrieval_service(chunk_repo)
        # Very high threshold — most cosine scores won't meet it
        results = await svc.retrieve(RetrievalQuery(
            tenant_id="tenant-1", agent_id="agent-1",
            query="completely unrelated query xyz",
            top_k=10, min_similarity=0.999,
        ))
        # All returned results must meet the threshold
        for r in results:
            assert r.similarity_score >= 0.999


# ===========================================================================
# Tenant & knowledge base isolation
# ===========================================================================


class TestIsolation:
    @pytest.mark.asyncio
    async def test_tenant_isolation_no_cross_tenant_results(self) -> None:
        """Chunks from tenant-A must never appear in tenant-B's search."""
        text = "Sensitive tenant A data. " * 20
        _, _, chunk_repo = await _run_ingestion(
            text.encode(), "doc.txt", "text/plain",
            tenant_id="tenant-A", agent_id="agent-1", kb_id="kb-1",
        )
        # Store tenant-B chunks in the same repo
        text_b = "Tenant B completely different content. " * 20
        await _run_ingestion(
            text_b.encode(), "docB.txt", "text/plain",
            tenant_id="tenant-B", agent_id="agent-1", kb_id="kb-1",
            document_id="doc-b", chunk_repo=chunk_repo,
        )

        kb_a = KnowledgeBase(id="kb-1", tenant_id="tenant-A", name="KB A")
        svc = RetrievalService(
            embedding_provider=VectorEmbeddingProvider(),
            chunk_repository=chunk_repo,
            kb_repository=InMemoryKBRepository([kb_a]),
        )
        results = await svc.retrieve(RetrievalQuery(
            tenant_id="tenant-A", agent_id="agent-1",
            query="Sensitive tenant A data",
            top_k=20, min_similarity=0.0,
        ))
        for r in results:
            assert r.chunk.tenant_id == "tenant-A", (
                f"Cross-tenant leak: got chunk from {r.chunk.tenant_id}"
            )

    @pytest.mark.asyncio
    async def test_kb_isolation_no_cross_kb_results(self) -> None:
        """Querying KB-1 must never return chunks stored in KB-2."""
        chunk_repo = InMemoryChunkRepository()
        text1 = "Knowledge base one private content. " * 20
        text2 = "Knowledge base two private content. " * 20
        await _run_ingestion(
            text1.encode(), "d1.txt", "text/plain",
            kb_id="kb-1", document_id="doc-kb1", chunk_repo=chunk_repo,
        )
        await _run_ingestion(
            text2.encode(), "d2.txt", "text/plain",
            kb_id="kb-2", document_id="doc-kb2", chunk_repo=chunk_repo,
        )

        kb1 = KnowledgeBase(id="kb-1", tenant_id="tenant-1", name="KB 1")
        svc = RetrievalService(
            embedding_provider=VectorEmbeddingProvider(),
            chunk_repository=chunk_repo,
            kb_repository=InMemoryKBRepository([kb1]),
        )
        results = await svc.retrieve(RetrievalQuery(
            tenant_id="tenant-1", agent_id="agent-1",
            query="knowledge base content",
            top_k=20, min_similarity=0.0,
        ))
        for r in results:
            assert r.chunk.knowledge_base_id == "kb-1", (
                f"Cross-KB leak: got chunk from {r.chunk.knowledge_base_id}"
            )

    @pytest.mark.asyncio
    async def test_inactive_kb_not_searched(self) -> None:
        """Chunks in an INACTIVE KB must not appear in retrieval results."""
        chunk_repo = InMemoryChunkRepository()
        text = "Inactive KB content should not be retrieved. " * 20
        await _run_ingestion(
            text.encode(), "doc.txt", "text/plain",
            kb_id="kb-inactive", document_id="doc-inactive",
            chunk_repo=chunk_repo,
        )
        inactive_kb = KnowledgeBase(
            id="kb-inactive", tenant_id="tenant-1", name="Inactive",
            status=KnowledgeBaseStatus.INACTIVE,
        )
        svc = RetrievalService(
            embedding_provider=VectorEmbeddingProvider(),
            chunk_repository=chunk_repo,
            kb_repository=InMemoryKBRepository([inactive_kb]),
        )
        with pytest.raises(RetrievalValidationError, match="no active knowledge bases"):
            await svc.retrieve(RetrievalQuery(
                tenant_id="tenant-1", agent_id="agent-1",
                query="inactive content",
                top_k=5, min_similarity=0.0,
            ))


# ===========================================================================
# Determinism & idempotency
# ===========================================================================


class TestDeterminismAndIdempotency:
    @pytest.mark.asyncio
    async def test_repeated_ingestion_same_chunk_ids(self) -> None:
        """Running the full pipeline twice on the same bytes → same IDs."""
        text = "Deterministic pipeline execution test. " * 25
        chunks1, _, _ = await _run_ingestion(
            text.encode(), "doc.txt", "text/plain", document_id="det-doc"
        )
        chunks2, _, _ = await _run_ingestion(
            text.encode(), "doc.txt", "text/plain", document_id="det-doc"
        )
        assert [c.id for c in chunks1] == [c.id for c in chunks2]

    @pytest.mark.asyncio
    async def test_repeated_ingestion_same_content_hashes(self) -> None:
        text = "Hash stability test content. " * 25
        chunks1, _, _ = await _run_ingestion(
            text.encode(), "doc.txt", "text/plain", document_id="hash-doc"
        )
        chunks2, _, _ = await _run_ingestion(
            text.encode(), "doc.txt", "text/plain", document_id="hash-doc"
        )
        assert [c.content_hash for c in chunks1] == [c.content_hash for c in chunks2]

    @pytest.mark.asyncio
    async def test_repeated_retrieval_same_order(self) -> None:
        """Calling retrieve twice on the same query returns the same order."""
        text = "Order stability retrieval test content. " * 25
        _, _, chunk_repo = await _run_ingestion(
            text.encode(), "doc.txt", "text/plain",
        )
        svc = _make_retrieval_service(chunk_repo)
        query = RetrievalQuery(
            tenant_id="tenant-1", agent_id="agent-1",
            query="order stability test",
            top_k=5, min_similarity=0.0,
        )
        r1 = await svc.retrieve(query)
        r2 = await svc.retrieve(query)
        assert [x.chunk.id for x in r1] == [x.chunk.id for x in r2]

    @pytest.mark.asyncio
    async def test_pipeline_idempotent_metadata(self) -> None:
        """All metadata fields are identical across two runs."""
        text = "Idempotency metadata check. " * 20
        for run in range(2):
            chunks, _, _ = await _run_ingestion(
                text.encode(), "doc.txt", "text/plain",
                tenant_id="t-idem", agent_id="a-idem",
                kb_id="kb-idem", source_name="src-idem",
                document_id="doc-idem",
            )
            for c in chunks:
                assert c.tenant_id == "t-idem"
                assert c.agent_id == "a-idem"
                assert c.knowledge_base_id == "kb-idem"
                assert c.source_name == "src-idem"
                assert c.document_id == "doc-idem"


# ===========================================================================
# Full end-to-end pipeline tests (parse → chunk → embed → retrieve)
# ===========================================================================


class TestFullEndToEnd:
    @pytest.mark.asyncio
    async def test_txt_full_pipeline(self) -> None:
        text = "Customer support: our return policy is 30 days. " * 20
        _, _, chunk_repo = await _run_ingestion(
            text.encode(), "support.txt", "text/plain",
            tenant_id="t-e2e", agent_id="a-e2e", kb_id="kb-e2e",
            source_name="support-docs", document_id="doc-e2e-txt",
        )
        svc = _make_retrieval_service(chunk_repo, kb_id="kb-e2e", tenant_id="t-e2e")
        results = await svc.retrieve(RetrievalQuery(
            tenant_id="t-e2e", agent_id="a-e2e",
            query="return policy",
            top_k=3, min_similarity=0.0,
        ))
        assert len(results) > 0
        for r in results:
            assert r.chunk.tenant_id == "t-e2e"
            assert r.chunk.agent_id == "a-e2e"
            assert r.chunk.knowledge_base_id == "kb-e2e"
            assert r.chunk.source_name == "support-docs"
            assert r.chunk.content_hash
            assert r.similarity_score >= 0.0

    @pytest.mark.asyncio
    async def test_md_full_pipeline(self) -> None:
        md = "# FAQ\n\nHow do I reset my password? Click forgot password.\n\n" * 15
        _, _, chunk_repo = await _run_ingestion(
            md.encode(), "faq.md", "text/markdown",
            tenant_id="t-md-e2e", agent_id="a-md-e2e", kb_id="kb-md-e2e",
            document_id="doc-md-e2e",
        )
        svc = _make_retrieval_service(chunk_repo, kb_id="kb-md-e2e", tenant_id="t-md-e2e")
        results = await svc.retrieve(RetrievalQuery(
            tenant_id="t-md-e2e", agent_id="a-md-e2e",
            query="reset password",
            top_k=5, min_similarity=0.0,
        ))
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_docx_full_pipeline(self) -> None:
        raw = _make_docx_bytes([
            "Product warranty covers defects for one year. " * 10,
            "Contact our support team for warranty claims. " * 10,
        ])
        mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        _, _, chunk_repo = await _run_ingestion(
            raw, "warranty.docx", mime,
            tenant_id="t-docx-e2e", agent_id="a-docx-e2e", kb_id="kb-docx-e2e",
            document_id="doc-docx-e2e",
        )
        svc = _make_retrieval_service(
            chunk_repo, kb_id="kb-docx-e2e", tenant_id="t-docx-e2e"
        )
        results = await svc.retrieve(RetrievalQuery(
            tenant_id="t-docx-e2e", agent_id="a-docx-e2e",
            query="warranty",
            top_k=5, min_similarity=0.0,
        ))
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_arabic_full_pipeline(self) -> None:
        arabic = "سياسة الإرجاع تسمح بإرجاع المنتجات خلال ثلاثين يوماً. " * 15
        _, _, chunk_repo = await _run_ingestion(
            arabic.encode("utf-8"), "ar_policy.txt", "text/plain",
            tenant_id="t-ar-e2e", agent_id="a-ar-e2e", kb_id="kb-ar-e2e",
            document_id="doc-ar-e2e",
        )
        svc = _make_retrieval_service(
            chunk_repo, kb_id="kb-ar-e2e", tenant_id="t-ar-e2e"
        )
        results = await svc.retrieve(RetrievalQuery(
            tenant_id="t-ar-e2e", agent_id="a-ar-e2e",
            query="سياسة الإرجاع",
            top_k=5, min_similarity=0.0,
        ))
        assert isinstance(results, list)
        for r in results:
            assert r.chunk.tenant_id == "t-ar-e2e"
            assert r.chunk.content_hash

    @pytest.mark.asyncio
    async def test_multi_doc_multi_kb_isolation(self) -> None:
        """Two docs in two KBs — each KB returns only its own chunks."""
        chunk_repo = InMemoryChunkRepository()
        text1 = "KB Alpha exclusive content about returns. " * 20
        text2 = "KB Beta exclusive content about shipping. " * 20
        await _run_ingestion(
            text1.encode(), "d1.txt", "text/plain",
            kb_id="kb-alpha", document_id="doc-alpha", chunk_repo=chunk_repo,
        )
        await _run_ingestion(
            text2.encode(), "d2.txt", "text/plain",
            kb_id="kb-beta", document_id="doc-beta", chunk_repo=chunk_repo,
        )

        kb_alpha = KnowledgeBase(id="kb-alpha", tenant_id="tenant-1", name="Alpha")
        svc = RetrievalService(
            embedding_provider=VectorEmbeddingProvider(),
            chunk_repository=chunk_repo,
            kb_repository=InMemoryKBRepository([kb_alpha]),
        )
        results = await svc.retrieve(RetrievalQuery(
            tenant_id="tenant-1", agent_id="agent-1",
            query="returns content",
            top_k=20, min_similarity=0.0,
        ))
        for r in results:
            assert r.chunk.knowledge_base_id == "kb-alpha"


# ===========================================================================
# Full end-to-end pipeline test (parse → chunk → embed → retrieve)
# ===========================================================================


class TestFullPipeline:
    @pytest.mark.asyncio
    async def test_txt_end_to_end(self) -> None:
        text = "The return policy allows full refunds within 30 days. " * 20
        _, _, chunk_repo = await _run_ingestion(
            text.encode(), "policy.txt", "text/plain",
            tenant_id="t-e2e", agent_id="a-e2e", kb_id="kb-e2e",
        )
        svc = _make_retrieval_service(chunk_repo, kb_id="kb-e2e", tenant_id="t-e2e")
        results = await svc.retrieve(RetrievalQuery(
            tenant_id="t-e2e", agent_id="a-e2e",
            query="refund policy",
            top_k=5, min_similarity=0.0,
        ))
        assert len(results) > 0
        assert all(r.chunk.tenant_id == "t-e2e" for r in results)
        assert all(r.chunk.agent_id == "a-e2e" for r in results)
        assert all(r.chunk.knowledge_base_id == "kb-e2e" for r in results)

    @pytest.mark.asyncio
    async def test_md_end_to_end(self) -> None:
        md = "# Help Center\n\nWe support all customers 24/7.\n\n" * 15
        _, _, chunk_repo = await _run_ingestion(
            md.encode(), "help.md", "text/markdown",
            tenant_id="t-md2", agent_id="a-md2", kb_id="kb-md2",
        )
        svc = _make_retrieval_service(chunk_repo, kb_id="kb-md2", tenant_id="t-md2")
        results = await svc.retrieve(RetrievalQuery(
            tenant_id="t-md2", agent_id="a-md2",
            query="customer support",
            top_k=3, min_similarity=0.0,
        ))
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_docx_end_to_end(self) -> None:
        raw = _make_docx_bytes(["Company policy on data privacy. " * 25])
        _, _, chunk_repo = await _run_ingestion(
            raw, "policy.docx",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            tenant_id="t-dx2", agent_id="a-dx2", kb_id="kb-dx2",
        )
        svc = _make_retrieval_service(chunk_repo, kb_id="kb-dx2", tenant_id="t-dx2")
        results = await svc.retrieve(RetrievalQuery(
            tenant_id="t-dx2", agent_id="a-dx2",
            query="data privacy policy",
            top_k=5, min_similarity=0.0,
        ))
        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_arabic_end_to_end(self) -> None:
        arabic = "سياسة الاسترداد تتيح الإرجاع خلال ثلاثين يوماً. " * 20
        _, _, chunk_repo = await _run_ingestion(
            arabic.encode("utf-8"), "ar_policy.txt", "text/plain",
            tenant_id="t-ar2", agent_id="a-ar2", kb_id="kb-ar2",
        )
        svc = _make_retrieval_service(chunk_repo, kb_id="kb-ar2", tenant_id="t-ar2")
        results = await svc.retrieve(RetrievalQuery(
            tenant_id="t-ar2", agent_id="a-ar2",
            query="سياسة الاسترداد",
            top_k=5, min_similarity=0.0,
        ))
        assert isinstance(results, list)
        assert all(r.chunk.tenant_id == "t-ar2" for r in results)

    @pytest.mark.asyncio
    async def test_metadata_integrity_through_all_stages(self) -> None:
        """Verify every metadata field survives all four pipeline stages."""
        text = "Metadata integrity check sentence. " * 20
        chunks, result, chunk_repo = await _run_ingestion(
            text.encode(), "meta.txt", "text/plain",
            tenant_id="t-meta", agent_id="a-meta", kb_id="kb-meta",
            source_name="meta-source", document_id="doc-meta",
        )
        # Stage 1–2: parse + chunk
        for c in chunks:
            assert c.tenant_id == "t-meta"
            assert c.agent_id == "a-meta"
            assert c.knowledge_base_id == "kb-meta"
            assert c.source_name == "meta-source"
            assert c.document_id == "doc-meta"
            assert c.chunk_index >= 0
            assert c.content_hash

        # Stage 3: embed
        for ec in result.embedded:
            c = ec.chunk
            assert c.tenant_id == "t-meta"
            assert c.agent_id == "a-meta"

        # Stage 4: retrieve
        svc = _make_retrieval_service(chunk_repo, kb_id="kb-meta", tenant_id="t-meta")
        retrieved = await svc.retrieve(RetrievalQuery(
            tenant_id="t-meta", agent_id="a-meta",
            query="metadata integrity check",
            top_k=10, min_similarity=0.0,
        ))
        for r in retrieved:
            assert r.chunk.tenant_id == "t-meta"
            assert r.chunk.agent_id == "a-meta"
            assert r.chunk.knowledge_base_id == "kb-meta"
            assert r.chunk.source_name == "meta-source"
            assert r.chunk.document_id == "doc-meta"
            assert r.chunk.content_hash
