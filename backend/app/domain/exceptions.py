"""Domain exception hierarchy for the Modern AI Agent Platform.

All domain exceptions inherit from ``DomainError`` so callers can catch the
entire domain surface with a single clause when needed, while still being
able to target specific exception types for fine-grained handling.

Rules:
- No framework imports (no FastAPI, no SQLAlchemy, no Pydantic).
- Error messages must be safe for end-user display — no stack traces, no
  internal IDs, no infrastructure details.
- Infrastructure layers translate these into appropriate HTTP responses.
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


class DomainError(Exception):
    """Base class for all domain exceptions."""


# ---------------------------------------------------------------------------
# Entity not found
# ---------------------------------------------------------------------------


class DocumentNotFoundError(DomainError):
    """Raised when a Document cannot be located for the given tenant scope."""


class KnowledgeBaseNotFoundError(DomainError):
    """Raised when a KnowledgeBase cannot be located for the given tenant scope."""


class AgentNotFoundError(DomainError):
    """Raised when an Agent cannot be located for the given tenant scope."""


# ---------------------------------------------------------------------------
# Parser errors
# ---------------------------------------------------------------------------


class UnsupportedDocumentTypeError(DomainError):
    """Raised when the ingestion pipeline receives a file type it cannot parse.

    This is a domain error, not an infrastructure error: the decision about
    which types are supported is a business rule, not a driver limitation.

    Example:
        raise UnsupportedDocumentTypeError(
            mime_type="application/zip",
            extension=".zip",
        )
    """

    def __init__(
        self,
        *,
        mime_type: str | None = None,
        extension: str | None = None,
    ) -> None:
        self.mime_type = mime_type
        self.extension = extension
        parts: list[str] = []
        if mime_type:
            parts.append(f"MIME type '{mime_type}'")
        if extension:
            parts.append(f"extension '{extension}'")
        detail = " / ".join(parts) if parts else "unknown type"
        super().__init__(f"Unsupported document type: {detail}.")


class ParseError(DomainError):
    """Raised when a parser fails to extract text from a document.

    The message must be a safe, human-readable explanation.  Raw library
    exceptions must be caught and re-raised as ``ParseError`` by parser
    implementations so infrastructure details never surface to callers.
    """


# ---------------------------------------------------------------------------
# Chunking errors
# ---------------------------------------------------------------------------


class ChunkingError(DomainError):
    """Raised when the chunking engine cannot process a parsed document.

    Examples: document has no extractable text after filtering empty pages,
    or the chunk configuration is invalid for the given document.
    """


# ---------------------------------------------------------------------------
# Embedding errors
# ---------------------------------------------------------------------------


class EmbeddingError(DomainError):
    """Raised when an embedding provider fails to produce a valid vector."""


# ---------------------------------------------------------------------------
# Retrieval errors
# ---------------------------------------------------------------------------


class RetrievalError(DomainError):
    """Raised when the vector search infrastructure fails during retrieval."""


class RetrievalValidationError(DomainError):
    """Raised when a ``RetrievalQuery`` fails pre-flight validation.

    Examples: empty query text, non-positive ``top_k``, similarity threshold
    outside [0.0, 1.0], or the agent has no active knowledge bases.
    """
