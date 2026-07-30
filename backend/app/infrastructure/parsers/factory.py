"""Concrete ``ParserFactory`` implementation.

``DefaultParserFactory`` is the production registry.  It is constructed once
(typically as a dependency-injection singleton) and reused across requests.
All parser instances are stateless, so they are created once at factory
construction time and shared safely.

Resolution order
----------------
1. ``mime_type`` is checked against all registered MIME sets.
2. If no match, ``extension`` is checked against all registered extension sets.
3. If neither resolves, ``UnsupportedDocumentTypeError`` is raised.

The factory never falls back silently — an ambiguous or unknown type always
surfaces as an explicit error so misconfigured uploads are caught early.
"""

from __future__ import annotations

from backend.app.domain.exceptions import UnsupportedDocumentTypeError
from backend.app.domain.ports.parser import DocumentParser, ParserFactory
from backend.app.infrastructure.parsers.docx_parser import DocxParser
from backend.app.infrastructure.parsers.markdown_parser import MarkdownParser
from backend.app.infrastructure.parsers.pdf_parser import PdfParser
from backend.app.infrastructure.parsers.txt_parser import TxtParser


class DefaultParserFactory(ParserFactory):
    """Production parser registry that resolves parsers by MIME type or extension.

    All parsers are instantiated once at construction time and reused for
    the lifetime of the factory instance.
    """

    def __init__(self) -> None:
        # Ordered list of registered parsers.  The first parser whose
        # supported_mime_types or supported_extensions set contains the
        # requested value is returned.
        self._parsers: list[DocumentParser] = [
            PdfParser(),
            DocxParser(),
            TxtParser(),
            MarkdownParser(),
        ]

        # Eagerly build lookup dictionaries for O(1) resolution.
        self._by_mime: dict[str, DocumentParser] = {}
        self._by_ext: dict[str, DocumentParser] = {}

        for parser in self._parsers:
            for mime in parser.supported_mime_types:
                # Some clients label Markdown as text/plain.  Keep the first
                # registered parser as the unambiguous MIME-only default
                # (TxtParser), while extension resolution still selects
                # Markdown correctly.
                self._by_mime.setdefault(mime.lower(), parser)
            for ext in parser.supported_extensions:
                self._by_ext[ext.lower()] = parser

    def get_parser(
        self,
        *,
        mime_type: str | None = None,
        extension: str | None = None,
    ) -> DocumentParser:
        """Return the parser registered for the given MIME type or extension.

        Args:
            mime_type: MIME type string (e.g. ``"application/pdf"``).
                       Checked first when provided.
            extension: File extension including the leading dot
                       (e.g. ``".pdf"``).  Used as a fallback.

        Returns:
            The matching ``DocumentParser``.

        Raises:
            ValueError:                   When both arguments are ``None``.
            UnsupportedDocumentTypeError: When no registered parser matches.
        """
        if mime_type is None and extension is None:
            raise ValueError(
                "At least one of 'mime_type' or 'extension' must be provided."
            )

        # When both hints are known, the extension identifies the concrete
        # parser and the MIME type must be compatible with it.  This prevents
        # a renamed executable or PDF from being accepted under a text suffix.
        if extension is not None:
            normalised = extension.lower()
            if not normalised.startswith("."):
                normalised = f".{normalised}"
            extension_parser = self._by_ext.get(normalised)
            if extension_parser is not None and mime_type is not None:
                if mime_type.lower() not in {
                    value.lower()
                    for value in extension_parser.supported_mime_types
                }:
                    raise UnsupportedDocumentTypeError(
                        mime_type=mime_type,
                        extension=normalised,
                    )
                return extension_parser

        # Try MIME type when there is no resolvable extension.
        if mime_type is not None:
            parser = self._by_mime.get(mime_type.lower())
            if parser is not None:
                return parser

        # Fall back to extension.
        if extension is not None:
            normalised = extension.lower()
            if not normalised.startswith("."):
                normalised = f".{normalised}"
            parser = self._by_ext.get(normalised)
            if parser is not None:
                return parser

        raise UnsupportedDocumentTypeError(
            mime_type=mime_type,
            extension=extension,
        )
