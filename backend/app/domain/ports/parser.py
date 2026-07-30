"""Document parser port interfaces and associated types.

Defines the abstraction layer that separates the ingestion service from any
specific parsing library.  The service layer depends only on these contracts;
concrete parsers (PDF, DOCX, TXT, Markdown) implement them in the
infrastructure layer without the domain layer knowing which library is used.

Design notes:
- ``SupportedDocumentType`` enumerates every format the platform accepts.
- ``ParsedDocument`` is the single output type for all parsers — a plain
  dataclass carrying extracted pages.
- ``DocumentParser`` is the per-format ABC.
- ``ParserFactory`` is the registry ABC that selects the correct parser for
  a given MIME type or file extension.
- No framework imports, no file I/O, no library imports.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum

from backend.app.domain.exceptions import UnsupportedDocumentTypeError


# ---------------------------------------------------------------------------
# Enum
# ---------------------------------------------------------------------------


class SupportedDocumentType(str, Enum):
    """Document formats that the ingestion pipeline can process.

    Values are lowercase strings that match common file extensions (without
    the leading dot) for convenient display and logging.

    Members:
        TXT:  Plain-text files (.txt), MIME: text/plain
        MD:   Markdown files (.md),   MIME: text/markdown
        PDF:  PDF documents (.pdf),   MIME: application/pdf
        DOCX: Word documents (.docx), MIME:
              application/vnd.openxmlformats-officedocument.
              wordprocessingml.document
    """

    TXT = "txt"
    MD = "md"
    PDF = "pdf"
    DOCX = "docx"


# ---------------------------------------------------------------------------
# Output data transfer object
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ParsedPage:
    """A single page of text extracted from a document.

    For non-paginated formats (TXT, MD, HTML) the entire document is
    represented as a single ``ParsedPage`` with ``page_number=0``.

    Attributes:
        page_number: 0-based index of the page within the source document.
        content:     Raw extracted text for this page.  May be empty for
                     blank pages; callers should skip empty pages during
                     chunking.
    """

    page_number: int
    content: str


@dataclass(frozen=True)
class ParsedDocument:
    """The complete output of a ``DocumentParser.parse()`` call.

    Attributes:
        document_type: The ``SupportedDocumentType`` that was parsed.
        pages:         Ordered list of extracted pages.  At least one
                       entry is always present (even for empty documents
                       a single page with empty content is returned so
                       callers do not need to handle a missing-pages case).
        metadata:      Optional key-value pairs carrying parser-extracted
                       metadata (e.g. title, author, creation date).
                       Values are always plain strings.
    """

    document_type: SupportedDocumentType
    pages: tuple[ParsedPage, ...]
    metadata: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# DocumentParser interface
# ---------------------------------------------------------------------------


class DocumentParser(ABC):
    """Contract for a single-format document parser.

    Each concrete parser handles exactly one ``SupportedDocumentType`` and
    declares which extensions and MIME types it accepts.  The service layer
    never instantiates a parser directly — it always goes through the
    ``ParserFactory``.

    All implementations must be stateless so they can be used concurrently
    without synchronisation.
    """

    @property
    @abstractmethod
    def supported_extensions(self) -> frozenset[str]:
        """File extensions this parser accepts, including the leading dot.

        Example:
            frozenset({".pdf"})
        """

    @property
    @abstractmethod
    def supported_mime_types(self) -> frozenset[str]:
        """MIME types this parser accepts.

        Example:
            frozenset({"application/pdf"})
        """

    @abstractmethod
    async def parse(self, content: bytes, filename: str) -> ParsedDocument:
        """Extract structured text from raw file bytes.

        Args:
            content:  Raw bytes of the uploaded file.  Must not be empty.
            filename: Original filename including extension, used only for
                      logging and error messages — not for determining format.
                      Format detection is done by the factory before this
                      method is called.

        Returns:
            A ``ParsedDocument`` containing at least one ``ParsedPage``.

        Raises:
            ValueError:  When ``content`` is empty.
            ParseError:  When the parser cannot extract text from the bytes
                         (corrupted file, encrypted PDF, etc.).  Must never
                         expose raw library exceptions.
        """


# ---------------------------------------------------------------------------
# ParserFactory interface
# ---------------------------------------------------------------------------


class ParserFactory(ABC):
    """Contract for selecting the correct ``DocumentParser`` for a given file.

    The factory is the single point where MIME type / extension matching
    logic lives.  Service code calls ``get_parser()`` and receives a ready-
    to-use parser without knowing which concrete class is returned.

    Implementations should register parsers at construction time and expose
    them through ``get_parser()`` only.
    """

    @abstractmethod
    def get_parser(
        self,
        *,
        mime_type: str | None = None,
        extension: str | None = None,
    ) -> DocumentParser:
        """Return the appropriate ``DocumentParser`` for the given type hint.

        The factory tries ``mime_type`` first; if that does not resolve to a
        known parser it falls back to ``extension``.  At least one of the
        two arguments must be provided.

        Args:
            mime_type: MIME type string (e.g. ``"application/pdf"``).
                       Takes precedence over ``extension`` when both are
                       given and both resolve to a known parser.
            extension: File extension including the leading dot
                       (e.g. ``".pdf"``).  Used as a fallback when
                       ``mime_type`` is absent or unrecognised.

        Returns:
            The ``DocumentParser`` registered for the resolved type.

        Raises:
            ValueError:                  When both ``mime_type`` and
                                         ``extension`` are ``None``.
            UnsupportedDocumentTypeError: When neither argument resolves to
                                          a registered parser.
        """
