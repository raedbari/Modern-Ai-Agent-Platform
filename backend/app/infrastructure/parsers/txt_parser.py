"""Plain-text document parser.

Implements ``DocumentParser`` for ``.txt`` files.  Plain text has no page
boundaries, so the entire decoded content is returned as a single
``ParsedPage`` with ``page_number=0``.

Encoding strategy
-----------------
UTF-8 is attempted first.  If that fails, ``latin-1`` is used as a
byte-transparent fallback that never raises a ``UnicodeDecodeError``.
"""

from __future__ import annotations

from backend.app.domain.exceptions import ParseError
from backend.app.domain.ports.parser import (
    DocumentParser,
    ParsedDocument,
    ParsedPage,
    SupportedDocumentType,
)


class TxtParser(DocumentParser):
    """Parses plain-text (``.txt``) files into a single-page ``ParsedDocument``."""

    @property
    def supported_extensions(self) -> frozenset[str]:
        return frozenset({".txt"})

    @property
    def supported_mime_types(self) -> frozenset[str]:
        return frozenset({"text/plain"})

    async def parse(self, content: bytes, filename: str) -> ParsedDocument:
        """Decode raw bytes as UTF-8 (falling back to latin-1) and return one page.

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
            document_type=SupportedDocumentType.TXT,
            pages=(ParsedPage(page_number=0, content=text),),
        )
