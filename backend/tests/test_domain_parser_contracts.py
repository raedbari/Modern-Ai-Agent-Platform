"""Tests for parser port contracts, enums, and domain exceptions.

Covers:
- SupportedDocumentType enum values and string inheritance.
- ParsedPage and ParsedDocument construction and immutability.
- DocumentParser is abstract and cannot be instantiated.
- ParserFactory is abstract and cannot be instantiated.
- UnsupportedDocumentTypeError message formatting.
- Domain exception hierarchy.
- Package __init__ re-exports all new symbols.
"""

from __future__ import annotations

import pytest
from abc import ABC

from backend.app.domain.exceptions import (
    AgentNotFoundError,
    DomainError,
    DocumentNotFoundError,
    EmbeddingError,
    KnowledgeBaseNotFoundError,
    ParseError,
    RetrievalError,
    UnsupportedDocumentTypeError,
)
from backend.app.domain.ports.parser import (
    DocumentParser,
    ParsedDocument,
    ParsedPage,
    ParserFactory,
    SupportedDocumentType,
)


# ---------------------------------------------------------------------------
# SupportedDocumentType
# ---------------------------------------------------------------------------


class TestSupportedDocumentType:
    def test_all_members_present(self) -> None:
        values = {t.value for t in SupportedDocumentType}
        assert values == {"txt", "md", "pdf", "docx"}

    def test_is_string_subclass(self) -> None:
        for doc_type in SupportedDocumentType:
            assert isinstance(doc_type, str)

    def test_values_are_lowercase(self) -> None:
        for doc_type in SupportedDocumentType:
            assert doc_type.value == doc_type.value.lower()

    def test_lookup_by_value(self) -> None:
        assert SupportedDocumentType("pdf") is SupportedDocumentType.PDF
        assert SupportedDocumentType("docx") is SupportedDocumentType.DOCX
        assert SupportedDocumentType("txt") is SupportedDocumentType.TXT
        assert SupportedDocumentType("md") is SupportedDocumentType.MD


# ---------------------------------------------------------------------------
# ParsedPage
# ---------------------------------------------------------------------------


class TestParsedPage:
    def test_construction(self) -> None:
        page = ParsedPage(page_number=0, content="Hello world")
        assert page.page_number == 0
        assert page.content == "Hello world"

    def test_is_frozen(self) -> None:
        page = ParsedPage(page_number=1, content="text")
        with pytest.raises(AttributeError):
            page.page_number = 2  # type: ignore

    def test_allows_empty_content(self) -> None:
        """Empty content is valid — callers decide whether to skip blank pages."""
        page = ParsedPage(page_number=0, content="")
        assert page.content == ""


# ---------------------------------------------------------------------------
# ParsedDocument
# ---------------------------------------------------------------------------


class TestParsedDocument:
    def _make(self, **overrides):
        defaults = dict(
            document_type=SupportedDocumentType.PDF,
            pages=(ParsedPage(page_number=0, content="Page text"),),
        )
        defaults.update(overrides)
        return ParsedDocument(**defaults)

    def test_construction_defaults(self) -> None:
        doc = self._make()
        assert doc.document_type is SupportedDocumentType.PDF
        assert len(doc.pages) == 1
        assert doc.metadata == {}

    def test_construction_with_metadata(self) -> None:
        doc = self._make(metadata={"author": "Alice", "title": "Report"})
        assert doc.metadata["author"] == "Alice"

    def test_is_frozen(self) -> None:
        doc = self._make()
        with pytest.raises(AttributeError):
            doc.document_type = SupportedDocumentType.TXT  # type: ignore

    def test_pages_is_tuple(self) -> None:
        doc = self._make()
        assert isinstance(doc.pages, tuple)

    def test_multiple_pages(self) -> None:
        pages = tuple(
            ParsedPage(page_number=i, content=f"Page {i}") for i in range(3)
        )
        doc = self._make(pages=pages)
        assert len(doc.pages) == 3
        assert doc.pages[2].content == "Page 2"


# ---------------------------------------------------------------------------
# DocumentParser (abstract)
# ---------------------------------------------------------------------------


class TestDocumentParser:
    def test_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            DocumentParser()  # type: ignore

    def test_is_abc(self) -> None:
        assert issubclass(DocumentParser, ABC)

    def test_has_expected_interface(self) -> None:
        assert "supported_extensions" in dir(DocumentParser)
        assert "supported_mime_types" in dir(DocumentParser)
        assert "parse" in dir(DocumentParser)

    def test_concrete_subclass_must_implement_all_methods(self) -> None:
        """A partial implementation that skips one abstract member must fail."""

        class IncompleteParser(DocumentParser):
            @property
            def supported_extensions(self) -> frozenset[str]:
                return frozenset({".pdf"})

            @property
            def supported_mime_types(self) -> frozenset[str]:
                return frozenset({"application/pdf"})

            # parse() is intentionally omitted

        with pytest.raises(TypeError):
            IncompleteParser()  # type: ignore

    def test_fully_concrete_subclass_can_be_instantiated(self) -> None:
        """A parser that implements all abstract members instantiates cleanly."""

        class MinimalParser(DocumentParser):
            @property
            def supported_extensions(self) -> frozenset[str]:
                return frozenset({".txt"})

            @property
            def supported_mime_types(self) -> frozenset[str]:
                return frozenset({"text/plain"})

            async def parse(self, content: bytes, filename: str) -> ParsedDocument:
                return ParsedDocument(
                    document_type=SupportedDocumentType.TXT,
                    pages=(ParsedPage(page_number=0, content=content.decode()),),
                )

        parser = MinimalParser()
        assert frozenset({".txt"}) == parser.supported_extensions
        assert frozenset({"text/plain"}) == parser.supported_mime_types


# ---------------------------------------------------------------------------
# ParserFactory (abstract)
# ---------------------------------------------------------------------------


class TestParserFactory:
    def test_is_abstract(self) -> None:
        with pytest.raises(TypeError):
            ParserFactory()  # type: ignore

    def test_is_abc(self) -> None:
        assert issubclass(ParserFactory, ABC)

    def test_has_get_parser_method(self) -> None:
        assert "get_parser" in dir(ParserFactory)

    def test_concrete_factory_raises_on_unsupported_type(self) -> None:
        """A concrete factory must raise UnsupportedDocumentTypeError for unknown types."""

        class MinimalFactory(ParserFactory):
            def get_parser(
                self,
                *,
                mime_type: str | None = None,
                extension: str | None = None,
            ) -> DocumentParser:
                raise UnsupportedDocumentTypeError(
                    mime_type=mime_type, extension=extension
                )

        factory = MinimalFactory()
        with pytest.raises(UnsupportedDocumentTypeError):
            factory.get_parser(mime_type="application/zip", extension=".zip")


# ---------------------------------------------------------------------------
# Domain exceptions
# ---------------------------------------------------------------------------


class TestDomainExceptions:
    def test_all_exceptions_inherit_from_domain_error(self) -> None:
        for exc_cls in [
            DocumentNotFoundError,
            KnowledgeBaseNotFoundError,
            AgentNotFoundError,
            UnsupportedDocumentTypeError,
            ParseError,
            EmbeddingError,
            RetrievalError,
        ]:
            assert issubclass(exc_cls, DomainError)

    def test_domain_error_inherits_from_exception(self) -> None:
        assert issubclass(DomainError, Exception)

    def test_unsupported_type_message_includes_mime(self) -> None:
        exc = UnsupportedDocumentTypeError(mime_type="application/zip")
        assert "application/zip" in str(exc)

    def test_unsupported_type_message_includes_extension(self) -> None:
        exc = UnsupportedDocumentTypeError(extension=".zip")
        assert ".zip" in str(exc)

    def test_unsupported_type_message_includes_both(self) -> None:
        exc = UnsupportedDocumentTypeError(
            mime_type="application/zip", extension=".zip"
        )
        assert "application/zip" in str(exc)
        assert ".zip" in str(exc)

    def test_unsupported_type_no_args_produces_safe_message(self) -> None:
        exc = UnsupportedDocumentTypeError()
        assert "unknown type" in str(exc)

    def test_unsupported_type_stores_attributes(self) -> None:
        exc = UnsupportedDocumentTypeError(
            mime_type="application/zip", extension=".zip"
        )
        assert exc.mime_type == "application/zip"
        assert exc.extension == ".zip"

    def test_parse_error_is_raiseable(self) -> None:
        with pytest.raises(ParseError, match="corrupted"):
            raise ParseError("File is corrupted.")

    def test_embedding_error_is_raiseable(self) -> None:
        with pytest.raises(EmbeddingError):
            raise EmbeddingError("Provider unavailable.")

    def test_retrieval_error_is_raiseable(self) -> None:
        with pytest.raises(RetrievalError):
            raise RetrievalError("Vector search failed.")


# ---------------------------------------------------------------------------
# Package exports
# ---------------------------------------------------------------------------


class TestParserPortsPackageExports:
    def test_all_symbols_exported_from_ports_init(self) -> None:
        from backend.app.domain.ports import (
            DocumentParser,
            ParsedDocument,
            ParsedPage,
            ParserFactory,
            SupportedDocumentType,
        )
        assert DocumentParser is not None
        assert ParsedDocument is not None
        assert ParsedPage is not None
        assert ParserFactory is not None
        assert SupportedDocumentType is not None
