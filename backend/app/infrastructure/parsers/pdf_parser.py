"""PDF document parser.

Implements ``DocumentParser`` for ``.pdf`` files using ``pypdf``.

Parsing strategy
----------------
Each PDF page is extracted separately to preserve physical page boundaries.
``page_number`` in the output matches the 0-based page index in the source
file so downstream components can cite accurate page references.

Corruption detection
--------------------
``pypdf`` raises ``pypdf.errors.PdfReadError`` for structurally broken PDFs
and ``pypdf.errors.PdfStreamError`` for malformed cross-reference tables.
Both are caught and re-raised as ``ParseError`` so callers receive a safe,
library-agnostic message.

Encrypted PDFs
--------------
PDFs that are encrypted without an embedded owner password are not readable.
``pypdf`` reports these via ``PdfReadError`` after the ``is_encrypted``
check, so they are caught by the same handler and reported as ``ParseError``.
"""

from __future__ import annotations

import io

import pypdf
import pypdf.errors

from backend.app.domain.exceptions import ParseError
from backend.app.domain.ports.parser import (
    DocumentParser,
    ParsedDocument,
    ParsedPage,
    SupportedDocumentType,
)


class PdfParser(DocumentParser):
    """Parses PDF (``.pdf``) files into a per-page ``ParsedDocument``."""

    @property
    def supported_extensions(self) -> frozenset[str]:
        return frozenset({".pdf"})

    @property
    def supported_mime_types(self) -> frozenset[str]:
        return frozenset({"application/pdf"})

    async def parse(self, content: bytes, filename: str) -> ParsedDocument:
        """Extract text from each PDF page in order.

        Args:
            content:  Raw PDF bytes.  Must not be empty.
            filename: Original filename, used in error messages only.

        Returns:
            A ``ParsedDocument`` with one ``ParsedPage`` per PDF page.
            Pages with no extractable text have an empty ``content`` string.

        Raises:
            ValueError:  When ``content`` is empty.
            ParseError:  When the bytes are not a valid PDF, are encrypted,
                         or are otherwise unreadable.
        """
        if not content:
            raise ValueError(f"Cannot parse '{filename}': file is empty.")

        try:
            reader = pypdf.PdfReader(io.BytesIO(content))

            if reader.is_encrypted:
                raise ParseError(
                    f"'{filename}' is encrypted and cannot be read."
                )

            pages: list[ParsedPage] = []
            for index, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                pages.append(ParsedPage(page_number=index, content=text))

        except ParseError:
            raise
        except pypdf.errors.PdfReadError as exc:
            raise ParseError(
                f"'{filename}' could not be read: the file may be corrupted."
            ) from exc
        except pypdf.errors.PdfStreamError as exc:
            raise ParseError(
                f"'{filename}' has a malformed structure and cannot be parsed."
            ) from exc
        except Exception as exc:
            raise ParseError(
                f"An unexpected error occurred while parsing '{filename}'."
            ) from exc

        # Always return at least one page even for empty PDFs so callers do
        # not need to guard against an empty pages tuple.
        if not pages:
            pages = [ParsedPage(page_number=0, content="")]

        page_count = len(reader.pages)
        metadata: dict[str, str] = {"page_count": str(page_count)}
        raw_meta = reader.metadata
        if raw_meta:
            if raw_meta.title:
                metadata["title"] = str(raw_meta.title)
            if raw_meta.author:
                metadata["author"] = str(raw_meta.author)

        return ParsedDocument(
            document_type=SupportedDocumentType.PDF,
            pages=tuple(pages),
            metadata=metadata,
        )
