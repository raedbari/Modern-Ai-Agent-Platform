"""Tests for the ChunkingService.

All tests are pure in-memory — no parsers, no repositories, no I/O.

Fixtures construct ``ParsedDocument`` objects directly so the tests remain
isolated from the parser implementations tested elsewhere.
"""

from __future__ import annotations

import pytest

from backend.app.domain.exceptions import ChunkingError
from backend.app.domain.models.chunk import Chunk
from backend.app.domain.ports.parser import ParsedDocument, ParsedPage, SupportedDocumentType
from backend.app.services.knowledge.chunking_service import (
    ChunkingService,
    _hash_content,
    _derive_chunk_id,
    _slide,
)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

_BASE_KWARGS = dict(
    document_id="doc-1",
    tenant_id="tenant-1",
    agent_id="agent-1",
    knowledge_base_id="kb-1",
    source_name="upload",
)


def _make_doc(*page_contents: str) -> ParsedDocument:
    """Build a minimal ``ParsedDocument`` from a variable number of page texts."""
    pages = tuple(
        ParsedPage(page_number=i, content=text)
        for i, text in enumerate(page_contents)
    )
    return ParsedDocument(
        document_type=SupportedDocumentType.TXT,
        pages=pages,
    )


def _make_service(chunk_size: int = 100, chunk_overlap: int = 20) -> ChunkingService:
    return ChunkingService(chunk_size=chunk_size, chunk_overlap=chunk_overlap)


# ---------------------------------------------------------------------------
# Internal helpers (white-box)
# ---------------------------------------------------------------------------


class TestSlide:
    def test_single_window_when_text_fits(self) -> None:
        result = _slide("hello world", chunk_size=50, chunk_overlap=10)
        assert result == ["hello world"]

    def test_two_windows_for_long_text(self) -> None:
        text = "A" * 100
        result = _slide(text, chunk_size=60, chunk_overlap=20)
        assert len(result) == 2
        # Second window starts at 60-20=40, so it has 60 chars
        assert len(result[0]) == 60
        assert len(result[1]) == 60

    def test_overlap_content_shared(self) -> None:
        text = "0123456789"  # 10 chars
        result = _slide(text, chunk_size=6, chunk_overlap=2)
        # step = 6-2 = 4
        # window 0: [0:6]  = "012345"
        # window 1: [4:10] = "456789"
        assert result[0] == "012345"
        assert result[1] == "456789"

    def test_empty_windows_skipped(self) -> None:
        result = _slide("   \n  ", chunk_size=100, chunk_overlap=0)
        assert result == []

    def test_single_char_text(self) -> None:
        result = _slide("X", chunk_size=100, chunk_overlap=0)
        assert result == ["X"]

    def test_no_trailing_empty_window(self) -> None:
        """The final window must never be empty after stripping."""
        text = "hello" + " " * 200
        result = _slide(text, chunk_size=10, chunk_overlap=2)
        for w in result:
            assert w.strip() != ""


class TestHashContent:
    def test_same_input_same_output(self) -> None:
        assert _hash_content("hello") == _hash_content("hello")

    def test_different_input_different_output(self) -> None:
        assert _hash_content("hello") != _hash_content("world")

    def test_returns_hex_string(self) -> None:
        result = _hash_content("test")
        assert isinstance(result, str)
        int(result, 16)  # must be valid hex

    def test_arabic_text_hashed(self) -> None:
        result = _hash_content("مرحبا بالعالم")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_mixed_text_hashed(self) -> None:
        result = _hash_content("Hello مرحبا")
        assert isinstance(result, str)


class TestDeriveChunkId:
    def test_same_inputs_same_id(self) -> None:
        assert _derive_chunk_id("doc-1", 0) == _derive_chunk_id("doc-1", 0)

    def test_different_index_different_id(self) -> None:
        assert _derive_chunk_id("doc-1", 0) != _derive_chunk_id("doc-1", 1)

    def test_different_document_different_id(self) -> None:
        assert _derive_chunk_id("doc-1", 0) != _derive_chunk_id("doc-2", 0)

    def test_returns_hex_string(self) -> None:
        result = _derive_chunk_id("doc-1", 42)
        int(result, 16)  # must be valid hex


# ---------------------------------------------------------------------------
# ChunkingService construction
# ---------------------------------------------------------------------------


class TestChunkingServiceConstruction:
    def test_valid_parameters(self) -> None:
        svc = ChunkingService(chunk_size=100, chunk_overlap=20)
        assert svc._chunk_size == 100
        assert svc._chunk_overlap == 20

    def test_zero_overlap_allowed(self) -> None:
        svc = ChunkingService(chunk_size=100, chunk_overlap=0)
        assert svc._chunk_overlap == 0

    def test_zero_chunk_size_raises(self) -> None:
        with pytest.raises(ValueError, match="chunk_size"):
            ChunkingService(chunk_size=0, chunk_overlap=0)

    def test_negative_chunk_size_raises(self) -> None:
        with pytest.raises(ValueError, match="chunk_size"):
            ChunkingService(chunk_size=-1, chunk_overlap=0)

    def test_negative_chunk_overlap_raises(self) -> None:
        with pytest.raises(ValueError, match="chunk_overlap"):
            ChunkingService(chunk_size=100, chunk_overlap=-1)

    def test_overlap_equal_to_size_raises(self) -> None:
        with pytest.raises(ValueError, match="chunk_overlap"):
            ChunkingService(chunk_size=100, chunk_overlap=100)

    def test_overlap_greater_than_size_raises(self) -> None:
        with pytest.raises(ValueError, match="chunk_overlap"):
            ChunkingService(chunk_size=100, chunk_overlap=200)


# ---------------------------------------------------------------------------
# chunk_document — basic behaviour
# ---------------------------------------------------------------------------


class TestChunkDocument:
    def test_single_page_single_chunk(self) -> None:
        svc = _make_service(chunk_size=200, chunk_overlap=0)
        doc = _make_doc("Short text that fits in one chunk.")
        chunks = svc.chunk_document(doc, **_BASE_KWARGS)
        assert len(chunks) == 1
        assert isinstance(chunks[0], Chunk)

    def test_returns_list_of_chunk_objects(self) -> None:
        svc = _make_service(chunk_size=50, chunk_overlap=10)
        doc = _make_doc("A" * 200)
        chunks = svc.chunk_document(doc, **_BASE_KWARGS)
        assert all(isinstance(c, Chunk) for c in chunks)

    def test_chunks_are_non_empty(self) -> None:
        svc = _make_service(chunk_size=50, chunk_overlap=10)
        doc = _make_doc("B" * 300)
        for chunk in svc.chunk_document(doc, **_BASE_KWARGS):
            assert chunk.content.strip() != ""

    # --- Multi-page ---

    def test_multi_page_document(self) -> None:
        svc = _make_service(chunk_size=200, chunk_overlap=0)
        doc = _make_doc("Page zero text.", "Page one text.", "Page two text.")
        chunks = svc.chunk_document(doc, **_BASE_KWARGS)
        assert len(chunks) >= 3

    def test_page_numbers_preserved(self) -> None:
        svc = _make_service(chunk_size=200, chunk_overlap=0)
        doc = _make_doc("Page zero.", "Page one.", "Page two.")
        chunks = svc.chunk_document(doc, **_BASE_KWARGS)
        page_numbers = [c.page_number for c in chunks]
        assert 0 in page_numbers
        assert 1 in page_numbers
        assert 2 in page_numbers

    def test_chunks_from_different_pages_carry_correct_page_number(self) -> None:
        svc = _make_service(chunk_size=50, chunk_overlap=0)
        doc = _make_doc("A" * 100, "B" * 100)
        chunks = svc.chunk_document(doc, **_BASE_KWARGS)
        a_chunks = [c for c in chunks if "A" in c.content]
        b_chunks = [c for c in chunks if "B" in c.content]
        assert all(c.page_number == 0 for c in a_chunks)
        assert all(c.page_number == 1 for c in b_chunks)

    def test_no_cross_page_merging(self) -> None:
        """A single chunk must never contain text from two different pages."""
        svc = _make_service(chunk_size=50, chunk_overlap=0)
        doc = _make_doc("A" * 40, "B" * 40)
        chunks = svc.chunk_document(doc, **_BASE_KWARGS)
        for chunk in chunks:
            assert not ("A" in chunk.content and "B" in chunk.content)

    # --- Chunk indexes ---

    def test_chunk_indexes_are_sequential(self) -> None:
        svc = _make_service(chunk_size=50, chunk_overlap=0)
        doc = _make_doc("X" * 300)
        chunks = svc.chunk_document(doc, **_BASE_KWARGS)
        assert [c.chunk_index for c in chunks] == list(range(len(chunks)))

    def test_chunk_indexes_are_global_across_pages(self) -> None:
        svc = _make_service(chunk_size=50, chunk_overlap=0)
        doc = _make_doc("A" * 100, "B" * 100)
        chunks = svc.chunk_document(doc, **_BASE_KWARGS)
        assert [c.chunk_index for c in chunks] == list(range(len(chunks)))

    # --- Overlap ---

    def test_overlap_carries_content_between_chunks(self) -> None:
        svc = _make_service(chunk_size=10, chunk_overlap=5)
        text = "0123456789ABCDE"  # 15 chars
        doc = _make_doc(text)
        chunks = svc.chunk_document(doc, **_BASE_KWARGS)
        # chunk 0 covers [0:10] = "0123456789"
        # chunk 1 covers [5:15] = "56789ABCDE"
        assert len(chunks) >= 2
        assert chunks[0].content[-5:] == chunks[1].content[:5]

    def test_zero_overlap_no_shared_content(self) -> None:
        svc = _make_service(chunk_size=5, chunk_overlap=0)
        text = "AAABBBCCC"  # 9 chars → 2 full + 1 partial
        doc = _make_doc(text)
        chunks = svc.chunk_document(doc, **_BASE_KWARGS)
        combined = "".join(c.content for c in chunks)
        # No char should appear twice at the boundary
        assert combined == text

    # --- Metadata propagation ---

    def test_tenant_id_propagated(self) -> None:
        svc = _make_service()
        chunks = svc.chunk_document(_make_doc("text"), **_BASE_KWARGS)
        assert all(c.tenant_id == "tenant-1" for c in chunks)

    def test_agent_id_propagated(self) -> None:
        svc = _make_service()
        chunks = svc.chunk_document(_make_doc("text"), **_BASE_KWARGS)
        assert all(c.agent_id == "agent-1" for c in chunks)

    def test_knowledge_base_id_propagated(self) -> None:
        svc = _make_service()
        chunks = svc.chunk_document(_make_doc("text"), **_BASE_KWARGS)
        assert all(c.knowledge_base_id == "kb-1" for c in chunks)

    def test_document_id_propagated(self) -> None:
        svc = _make_service()
        chunks = svc.chunk_document(_make_doc("text"), **_BASE_KWARGS)
        assert all(c.document_id == "doc-1" for c in chunks)

    def test_source_name_propagated(self) -> None:
        svc = _make_service()
        chunks = svc.chunk_document(_make_doc("text"), **_BASE_KWARGS)
        assert all(c.source_name == "upload" for c in chunks)

    def test_metadata_not_leaked_between_calls(self) -> None:
        """Two successive calls with different metadata must not mix results."""
        svc = _make_service()
        doc = _make_doc("some text content here")
        kwargs_a = dict(
            document_id="doc-A",
            tenant_id="tenant-A",
            agent_id="agent-A",
            knowledge_base_id="kb-A",
            source_name="source-A",
        )
        kwargs_b = dict(
            document_id="doc-B",
            tenant_id="tenant-B",
            agent_id="agent-B",
            knowledge_base_id="kb-B",
            source_name="source-B",
        )
        chunks_a = svc.chunk_document(doc, **kwargs_a)
        chunks_b = svc.chunk_document(doc, **kwargs_b)
        assert all(c.tenant_id == "tenant-A" for c in chunks_a)
        assert all(c.tenant_id == "tenant-B" for c in chunks_b)

    # --- Content hash ---

    def test_content_hash_present_on_every_chunk(self) -> None:
        svc = _make_service()
        chunks = svc.chunk_document(_make_doc("hello world"), **_BASE_KWARGS)
        for chunk in chunks:
            assert chunk.content_hash
            assert len(chunk.content_hash) > 0

    def test_content_hash_is_deterministic(self) -> None:
        svc = _make_service()
        doc = _make_doc("deterministic content")
        run1 = svc.chunk_document(doc, **_BASE_KWARGS)
        run2 = svc.chunk_document(doc, **_BASE_KWARGS)
        assert [c.content_hash for c in run1] == [c.content_hash for c in run2]

    def test_different_content_different_hash(self) -> None:
        svc = _make_service(chunk_size=200, chunk_overlap=0)
        doc_a = _make_doc("Content A")
        doc_b = _make_doc("Content B")
        chunks_a = svc.chunk_document(doc_a, **_BASE_KWARGS)
        chunks_b = svc.chunk_document(doc_b, **_BASE_KWARGS)
        assert chunks_a[0].content_hash != chunks_b[0].content_hash

    # --- Deterministic IDs ---

    def test_chunk_ids_are_deterministic(self) -> None:
        svc = _make_service()
        doc = _make_doc("repeatable content")
        run1 = svc.chunk_document(doc, **_BASE_KWARGS)
        run2 = svc.chunk_document(doc, **_BASE_KWARGS)
        assert [c.id for c in run1] == [c.id for c in run2]

    def test_chunk_ids_are_unique_within_document(self) -> None:
        svc = _make_service(chunk_size=20, chunk_overlap=0)
        doc = _make_doc("A" * 200)
        chunks = svc.chunk_document(doc, **_BASE_KWARGS)
        ids = [c.id for c in chunks]
        assert len(ids) == len(set(ids))

    # --- Empty / whitespace pages ---

    def test_empty_page_skipped(self) -> None:
        svc = _make_service()
        doc = _make_doc("real text", "")
        chunks = svc.chunk_document(doc, **_BASE_KWARGS)
        assert all(c.page_number == 0 for c in chunks)

    def test_whitespace_only_page_skipped(self) -> None:
        svc = _make_service()
        doc = _make_doc("real text", "   \n\t  ")
        chunks = svc.chunk_document(doc, **_BASE_KWARGS)
        assert all(c.page_number == 0 for c in chunks)

    def test_all_empty_pages_raises_chunking_error(self) -> None:
        svc = _make_service()
        doc = _make_doc("", "   ", "\n")
        with pytest.raises(ChunkingError):
            svc.chunk_document(doc, **_BASE_KWARGS)

    def test_empty_document_no_pages_raises_chunking_error(self) -> None:
        svc = _make_service()
        doc = ParsedDocument(
            document_type=SupportedDocumentType.TXT,
            pages=(),
        )
        with pytest.raises(ChunkingError):
            svc.chunk_document(doc, **_BASE_KWARGS)

    # --- Arabic and mixed text ---

    def test_arabic_text_produces_chunks(self) -> None:
        svc = _make_service(chunk_size=50, chunk_overlap=10)
        arabic = "مرحبا بالعالم " * 20  # 280 chars
        doc = _make_doc(arabic)
        chunks = svc.chunk_document(doc, **_BASE_KWARGS)
        assert len(chunks) > 0
        assert all(c.content.strip() for c in chunks)

    def test_mixed_arabic_english_text(self) -> None:
        svc = _make_service(chunk_size=50, chunk_overlap=10)
        mixed = "Hello مرحبا world العالم " * 10
        doc = _make_doc(mixed)
        chunks = svc.chunk_document(doc, **_BASE_KWARGS)
        assert len(chunks) > 0

    def test_arabic_content_hash_deterministic(self) -> None:
        svc = _make_service(chunk_size=200, chunk_overlap=0)
        doc = _make_doc("مرحبا بالعالم")
        run1 = svc.chunk_document(doc, **_BASE_KWARGS)
        run2 = svc.chunk_document(doc, **_BASE_KWARGS)
        assert run1[0].content_hash == run2[0].content_hash

    # --- Large document ---

    def test_large_document_many_chunks(self) -> None:
        svc = _make_service(chunk_size=100, chunk_overlap=20)
        # 5000 chars → many chunks
        doc = _make_doc("word " * 1000)
        chunks = svc.chunk_document(doc, **_BASE_KWARGS)
        assert len(chunks) > 10

    def test_large_document_sequential_indexes(self) -> None:
        svc = _make_service(chunk_size=100, chunk_overlap=20)
        doc = _make_doc("word " * 1000)
        chunks = svc.chunk_document(doc, **_BASE_KWARGS)
        assert [c.chunk_index for c in chunks] == list(range(len(chunks)))

    def test_large_document_all_metadata_present(self) -> None:
        svc = _make_service(chunk_size=100, chunk_overlap=20)
        doc = _make_doc("word " * 1000)
        chunks = svc.chunk_document(doc, **_BASE_KWARGS)
        for chunk in chunks:
            assert chunk.tenant_id
            assert chunk.agent_id
            assert chunk.knowledge_base_id
            assert chunk.document_id
            assert chunk.source_name
            assert chunk.content_hash
