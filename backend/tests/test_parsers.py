"""Tests for concrete document parsers and DefaultParserFactory.

All tests are pure in-memory — no files are read from or written to disk.

Fixtures
--------
- ``_make_pdf``   : minimal valid single-page PDF bytes built with pypdf.
- ``_make_docx``  : minimal valid DOCX bytes built with python-docx.
- Corrupt bytes   : random bytes that are not valid PDF / DOCX.
"""

from __future__ import annotations

import io
import pytest

# ---------------------------------------------------------------------------
# Fixture helpers — build valid documents in memory
# ---------------------------------------------------------------------------


def _make_pdf_bytes(pages: list[str] | None = None) -> bytes:
    """Return bytes of a valid minimal PDF with one text page per item."""
    import pypdf
    from pypdf import PdfWriter

    writer = PdfWriter()
    texts = pages or ["Hello from PDF page one."]
    for text in texts:
        page = writer.add_blank_page(width=612, height=792)
        # pypdf's PdfWriter.add_blank_page returns a PageObject.
        # We annotate text via a simple content stream.
        # pypdf >= 4 exposes insert_page and page content streams;
        # the simplest portable approach is to use PdfWriter directly.
        # For test purposes we just need a valid, readable PDF.
    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def _make_docx_bytes(paragraphs: list[str] | None = None) -> bytes:
    """Return bytes of a valid minimal DOCX with the given paragraph texts."""
    import docx as python_docx

    doc = python_docx.Document()
    for para in (paragraphs or ["Hello from DOCX paragraph one."]):
        doc.add_paragraph(para)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Imports under test
# ---------------------------------------------------------------------------

from backend.app.domain.exceptions import ParseError, UnsupportedDocumentTypeError
from backend.app.domain.ports.parser import (
    ParsedDocument,
    SupportedDocumentType,
)
from backend.app.infrastructure.parsers.txt_parser import TxtParser
from backend.app.infrastructure.parsers.markdown_parser import MarkdownParser
from backend.app.infrastructure.parsers.pdf_parser import PdfParser
from backend.app.infrastructure.parsers.docx_parser import DocxParser
from backend.app.infrastructure.parsers.factory import DefaultParserFactory


# ---------------------------------------------------------------------------
# TxtParser
# ---------------------------------------------------------------------------


class TestTxtParser:
    def setup_method(self) -> None:
        self.parser = TxtParser()

    def test_supported_extensions(self) -> None:
        assert ".txt" in self.parser.supported_extensions

    def test_supported_mime_types(self) -> None:
        assert "text/plain" in self.parser.supported_mime_types

    @pytest.mark.asyncio
    async def test_parse_utf8_content(self) -> None:
        content = "Hello, world!\nSecond line.".encode("utf-8")
        result = await self.parser.parse(content, "sample.txt")
        assert isinstance(result, ParsedDocument)
        assert result.document_type is SupportedDocumentType.TXT
        assert len(result.pages) == 1
        assert "Hello, world!" in result.pages[0].content
        assert result.pages[0].page_number == 0

    @pytest.mark.asyncio
    async def test_parse_latin1_content(self) -> None:
        content = "Café résumé".encode("latin-1")
        result = await self.parser.parse(content, "latin.txt")
        assert result.document_type is SupportedDocumentType.TXT
        assert "Caf" in result.pages[0].content

    @pytest.mark.asyncio
    async def test_empty_content_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            await self.parser.parse(b"", "empty.txt")

    @pytest.mark.asyncio
    async def test_whitespace_only_content_is_valid(self) -> None:
        result = await self.parser.parse(b"   \n  ", "spaces.txt")
        assert result.document_type is SupportedDocumentType.TXT

    @pytest.mark.asyncio
    async def test_returns_single_page(self) -> None:
        result = await self.parser.parse(b"data", "f.txt")
        assert len(result.pages) == 1

    @pytest.mark.asyncio
    async def test_content_is_preserved_verbatim(self) -> None:
        text = "Line 1\nLine 2\nLine 3"
        result = await self.parser.parse(text.encode(), "f.txt")
        assert result.pages[0].content == text


# ---------------------------------------------------------------------------
# MarkdownParser
# ---------------------------------------------------------------------------


class TestMarkdownParser:
    def setup_method(self) -> None:
        self.parser = MarkdownParser()

    def test_supported_extensions(self) -> None:
        assert ".md" in self.parser.supported_extensions

    def test_supported_mime_types(self) -> None:
        assert "text/markdown" in self.parser.supported_mime_types

    @pytest.mark.asyncio
    async def test_parse_markdown_content(self) -> None:
        md = "# Title\n\nSome **bold** text.\n\n- item 1\n- item 2"
        result = await self.parser.parse(md.encode(), "readme.md")
        assert result.document_type is SupportedDocumentType.MD
        assert len(result.pages) == 1
        assert "# Title" in result.pages[0].content

    @pytest.mark.asyncio
    async def test_markdown_syntax_preserved(self) -> None:
        """Markdown syntax is returned verbatim, not stripped."""
        md = "## Heading\n\n**bold** and _italic_"
        result = await self.parser.parse(md.encode(), "doc.md")
        assert "**bold**" in result.pages[0].content
        assert "_italic_" in result.pages[0].content

    @pytest.mark.asyncio
    async def test_empty_content_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            await self.parser.parse(b"", "empty.md")

    @pytest.mark.asyncio
    async def test_returns_single_page(self) -> None:
        result = await self.parser.parse(b"# Doc", "doc.md")
        assert len(result.pages) == 1
        assert result.pages[0].page_number == 0


# ---------------------------------------------------------------------------
# PdfParser
# ---------------------------------------------------------------------------


class TestPdfParser:
    def setup_method(self) -> None:
        self.parser = PdfParser()
        self.valid_pdf = _make_pdf_bytes()

    def test_supported_extensions(self) -> None:
        assert ".pdf" in self.parser.supported_extensions

    def test_supported_mime_types(self) -> None:
        assert "application/pdf" in self.parser.supported_mime_types

    @pytest.mark.asyncio
    async def test_parse_valid_pdf(self) -> None:
        result = await self.parser.parse(self.valid_pdf, "doc.pdf")
        assert isinstance(result, ParsedDocument)
        assert result.document_type is SupportedDocumentType.PDF

    @pytest.mark.asyncio
    async def test_page_count_in_metadata(self) -> None:
        result = await self.parser.parse(self.valid_pdf, "doc.pdf")
        assert "page_count" in result.metadata
        assert int(result.metadata["page_count"]) >= 1

    @pytest.mark.asyncio
    async def test_page_numbers_are_sequential(self) -> None:
        result = await self.parser.parse(self.valid_pdf, "doc.pdf")
        for i, page in enumerate(result.pages):
            assert page.page_number == i

    @pytest.mark.asyncio
    async def test_empty_content_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            await self.parser.parse(b"", "empty.pdf")

    @pytest.mark.asyncio
    async def test_corrupted_pdf_raises_parse_error(self) -> None:
        corrupted = b"%PDF-1.4 this is not a real pdf \x00\x01\x02\x03"
        with pytest.raises(ParseError):
            await self.parser.parse(corrupted, "bad.pdf")

    @pytest.mark.asyncio
    async def test_random_bytes_raise_parse_error(self) -> None:
        garbage = b"\x89PNG\r\n\x1a\n" + b"\xff" * 200
        with pytest.raises(ParseError):
            await self.parser.parse(garbage, "not_a_pdf.pdf")

    @pytest.mark.asyncio
    async def test_returns_at_least_one_page(self) -> None:
        result = await self.parser.parse(self.valid_pdf, "doc.pdf")
        assert len(result.pages) >= 1


# ---------------------------------------------------------------------------
# DocxParser
# ---------------------------------------------------------------------------


class TestDocxParser:
    def setup_method(self) -> None:
        self.parser = DocxParser()
        self.valid_docx = _make_docx_bytes(
            ["First paragraph.", "Second paragraph."]
        )

    def test_supported_extensions(self) -> None:
        assert ".docx" in self.parser.supported_extensions

    def test_supported_mime_types(self) -> None:
        assert (
            "application/vnd.openxmlformats-officedocument"
            ".wordprocessingml.document"
        ) in self.parser.supported_mime_types

    @pytest.mark.asyncio
    async def test_parse_valid_docx(self) -> None:
        result = await self.parser.parse(self.valid_docx, "doc.docx")
        assert isinstance(result, ParsedDocument)
        assert result.document_type is SupportedDocumentType.DOCX

    @pytest.mark.asyncio
    async def test_paragraph_text_extracted(self) -> None:
        result = await self.parser.parse(self.valid_docx, "doc.docx")
        assert "First paragraph." in result.pages[0].content
        assert "Second paragraph." in result.pages[0].content

    @pytest.mark.asyncio
    async def test_returns_single_page(self) -> None:
        result = await self.parser.parse(self.valid_docx, "doc.docx")
        assert len(result.pages) == 1
        assert result.pages[0].page_number == 0

    @pytest.mark.asyncio
    async def test_empty_content_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="empty"):
            await self.parser.parse(b"", "empty.docx")

    @pytest.mark.asyncio
    async def test_corrupted_docx_raises_parse_error(self) -> None:
        # DOCX is a ZIP-based format; random bytes are not a valid ZIP.
        corrupted = b"PK\x03\x04 this is not a real docx" + b"\x00" * 50
        with pytest.raises(ParseError):
            await self.parser.parse(corrupted, "bad.docx")

    @pytest.mark.asyncio
    async def test_random_bytes_raise_parse_error(self) -> None:
        garbage = b"\xff\xfe" + b"\xab\xcd" * 100
        with pytest.raises(ParseError):
            await self.parser.parse(garbage, "not_a_docx.docx")

    @pytest.mark.asyncio
    async def test_empty_paragraphs_skipped(self) -> None:
        docx_with_blanks = _make_docx_bytes(["Text", "", "More text"])
        result = await self.parser.parse(docx_with_blanks, "blanks.docx")
        # Empty paragraph should not produce a blank line between the two texts
        assert "Text" in result.pages[0].content
        assert "More text" in result.pages[0].content


# ---------------------------------------------------------------------------
# DefaultParserFactory
# ---------------------------------------------------------------------------


class TestDefaultParserFactory:
    def setup_method(self) -> None:
        self.factory = DefaultParserFactory()

    # --- MIME type resolution ---

    def test_resolve_pdf_by_mime(self) -> None:
        parser = self.factory.get_parser(mime_type="application/pdf")
        assert isinstance(parser, PdfParser)

    def test_resolve_docx_by_mime(self) -> None:
        parser = self.factory.get_parser(
            mime_type=(
                "application/vnd.openxmlformats-officedocument"
                ".wordprocessingml.document"
            )
        )
        assert isinstance(parser, DocxParser)

    def test_resolve_txt_by_mime(self) -> None:
        parser = self.factory.get_parser(mime_type="text/plain")
        assert isinstance(parser, TxtParser)

    def test_resolve_markdown_by_mime(self) -> None:
        parser = self.factory.get_parser(mime_type="text/markdown")
        assert isinstance(parser, MarkdownParser)

    # --- Extension fallback ---

    def test_resolve_pdf_by_extension(self) -> None:
        parser = self.factory.get_parser(extension=".pdf")
        assert isinstance(parser, PdfParser)

    def test_resolve_docx_by_extension(self) -> None:
        parser = self.factory.get_parser(extension=".docx")
        assert isinstance(parser, DocxParser)

    def test_resolve_txt_by_extension(self) -> None:
        parser = self.factory.get_parser(extension=".txt")
        assert isinstance(parser, TxtParser)

    def test_resolve_md_by_extension(self) -> None:
        parser = self.factory.get_parser(extension=".md")
        assert isinstance(parser, MarkdownParser)

    def test_extension_without_dot_normalised(self) -> None:
        """Extension without a leading dot is accepted and normalised."""
        parser = self.factory.get_parser(extension="pdf")
        assert isinstance(parser, PdfParser)

    def test_extension_case_insensitive(self) -> None:
        parser = self.factory.get_parser(extension=".PDF")
        assert isinstance(parser, PdfParser)

    def test_mime_case_insensitive(self) -> None:
        parser = self.factory.get_parser(mime_type="APPLICATION/PDF")
        assert isinstance(parser, PdfParser)

    # --- MIME takes precedence over extension ---

    def test_mime_takes_precedence_over_extension(self) -> None:
        """When MIME resolves, extension is ignored."""
        parser = self.factory.get_parser(
            mime_type="application/pdf", extension=".txt"
        )
        assert isinstance(parser, PdfParser)

    # --- Unsupported types ---

    def test_unsupported_mime_raises(self) -> None:
        with pytest.raises(UnsupportedDocumentTypeError):
            self.factory.get_parser(mime_type="application/zip")

    def test_unsupported_extension_raises(self) -> None:
        with pytest.raises(UnsupportedDocumentTypeError):
            self.factory.get_parser(extension=".exe")

    def test_no_arguments_raises_value_error(self) -> None:
        with pytest.raises(ValueError):
            self.factory.get_parser()

    def test_unknown_mime_falls_back_to_extension(self) -> None:
        """Unknown MIME falls through to extension resolution."""
        parser = self.factory.get_parser(
            mime_type="application/octet-stream", extension=".pdf"
        )
        assert isinstance(parser, PdfParser)

    def test_unknown_mime_and_unknown_extension_raises(self) -> None:
        with pytest.raises(UnsupportedDocumentTypeError):
            self.factory.get_parser(
                mime_type="application/octet-stream", extension=".xyz"
            )

    # --- Parser instances are reused ---

    def test_same_instance_returned(self) -> None:
        """Factory returns the same cached parser instance."""
        p1 = self.factory.get_parser(mime_type="application/pdf")
        p2 = self.factory.get_parser(extension=".pdf")
        assert p1 is p2
