"""Markdown document parser.

Implements ``DocumentParser`` for ``.md`` files.

Parsing strategy
----------------
Markdown is plain text at its core.  The raw bytes are decoded and the
text is returned verbatim as a single ``ParsedPage`` — the downstream
chunking step will segment the content.

The Markdown syntax is intentionally preserved rather than stripped.
Stripping headers and emphasis requires a rendering library which adds a
dependency for marginal retrieval benefit.  If the team decides stripping
is needed, this parser can be updated independently without touching the
contract or factory.

Encoding strategy
-----------------
UTF-8 is attempted first.  On failure, ``latin-1`` is used as a
byte-transparent fallback.
"""

from __future__ import annotations

from backend.app.domain.exceptions import ParseError
from backend.app.domain.ports.parser import (
    DocumentParser,
    ParsedDocument,
    ParsedPage,
    SupportedDocumentType,
)

# text/markdown is the IANA-registered MIME type; text/plain is commonly
# sent by clients that do not recognise .md files.
_MIME_TYPES: frozenset[str] = frozenset({"text/markdown", "text/plain; charset=utf-8", "text/plain"})


class MarkdownParser(DocumentParser):
    """Parses Markdown (``.md``) files into a single-page ``ParsedDocument``."""

    @property
    def supported_extensions(self) -> frozenset[str]:
        return frozenset({".md"})

    @property
    def supported_mime_types(self) -> frozenset[str]:
        return _MIME_TYPES

    async def parse(self, content: bytes, filename: str) -> ParsedDocument:
        """Decode raw bytes and return the full Markdown source as one page.

        Args:
            content:  Raw file bytes.  Must not be empty.
            filename: Original filename, used in error messages only.

        Returns:
            A ``ParsedDocument`` with a single ``ParsedPage``.

        Raises:
            ValueError:  When ``content`` is empty.
            ParseError:  When the bytes cannot be decoded by any strategy.
        """
        if not content:
            raise ValueError(f"Cannot parse '{filename}': file is empty.")

        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = content.decode("latin-1")
            except Exception as exc:
                raise ParseError(
                    f"Could not decode '{filename}' as text."
                ) from exc

        return ParsedDocument(
            document_type=SupportedDocumentType.MD,
            pages=(ParsedPage(page_number=0, content=text),),
        )
