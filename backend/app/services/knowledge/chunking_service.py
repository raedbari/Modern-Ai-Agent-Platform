"""Chunking engine for the Knowledge RAG Pipeline.

Converts a ``ParsedDocument`` produced by a parser into a list of domain
``Chunk`` objects ready for embedding and storage.

Algorithm
---------
The chunker uses a **character-level sliding window** with configurable
``chunk_size`` and ``chunk_overlap``.  Both values are read from the
application ``Settings`` object injected at construction time.

Page boundaries are fully preserved: chunks are never formed by merging
text from two different pages.  Each page is sliced independently and the
resulting chunks carry the ``page_number`` of their source page.

Processing order
~~~~~~~~~~~~~~~~
1. Filter out pages whose text is empty or whitespace-only.
2. Raise ``ChunkingError`` if no pages survive the filter.
3. For each surviving page, slide a window of size ``chunk_size`` forward
   by ``chunk_size - chunk_overlap`` characters.
4. Strip each window; skip windows that are empty after stripping.
5. Assign a document-global ``chunk_index`` that increments monotonically
   across all pages.
6. Generate a deterministic ``content_hash`` (xxHash-64) for each window.
7. Generate a deterministic ``id`` from the hash and ``chunk_index`` so the
   same document always produces the same chunk IDs.

Hash strategy
-------------
``xxhash.xxh64`` is used because:
- It is already declared in ``requirements.lock.txt``.
- It is deterministic: same input → same output on every platform.
- It is fast enough to hash thousands of chunks without noticeable overhead.

The hash input is the UTF-8–encoded chunk content.  No random salt is
added so deduplication comparisons remain stable across re-ingestion.

Chunk ID strategy
-----------------
The ``id`` field of each ``Chunk`` is derived as
``xxh64("<document_id>:<chunk_index>")`` encoded as a hex string so it is:
- Stable across re-ingestion of the same document.
- Unique within a document (``chunk_index`` is the discriminator).
- Safe to use as a database primary key without a round-trip to generate a
  UUID.

Design constraints
------------------
- No persistence: the service never touches a repository.
- No embedding: the service never calls ``EmbeddingProvider``.
- No framework imports: no FastAPI, no SQLAlchemy.
- Fully synchronous: chunking is CPU-bound; wrapping in async is the
  caller's responsibility if needed.
- Stateless: all inputs are passed as arguments; no instance state mutates
  between calls.
"""

from __future__ import annotations

import xxhash

from backend.app.domain.exceptions import ChunkingError
from backend.app.domain.models.chunk import Chunk
from backend.app.domain.ports.parser import ParsedDocument


def _hash_content(text: str) -> str:
    """Return the xxHash-64 hex digest of the UTF-8–encoded text."""
    return xxhash.xxh64(text.encode("utf-8")).hexdigest()


def _derive_chunk_id(document_id: str, chunk_index: int) -> str:
    """Return a stable, document-scoped chunk identifier.

    The identifier is derived from the parent document ID and the
    chunk's position, so re-ingesting the same document produces the
    same IDs for the same chunks.
    """
    return xxhash.xxh64(f"{document_id}:{chunk_index}".encode()).hexdigest()


def _slide(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Split *text* into overlapping windows of at most *chunk_size* chars.

    Args:
        text:          The input string to split.  May be of any length.
        chunk_size:    Maximum character length of each window.
        chunk_overlap: Number of characters carried over from the previous
                       window into the next one.  Must be < ``chunk_size``.

    Returns:
        A list of non-empty text windows.  Each window is stripped of leading
        and trailing whitespace.  Windows that are empty after stripping are
        omitted so callers never receive blank chunks.
    """
    step = chunk_size - chunk_overlap
    windows: list[str] = []
    start = 0
    while start < len(text):
        window = text[start : start + chunk_size].strip()
        if window:
            windows.append(window)
        start += step
    return windows


class ChunkingService:
    """Converts a ``ParsedDocument`` into domain ``Chunk`` objects.

    Responsibilities:
    - Validate ``chunk_size`` and ``chunk_overlap`` on construction.
    - Filter empty pages from the input document.
    - Apply the sliding-window algorithm to each surviving page.
    - Assign stable, deterministic IDs and content hashes to every chunk.
    - Propagate all isolation metadata (tenant, agent, KB, document) to
      every chunk without modification.

    This class has no I/O dependencies.  It does not call any repository,
    provider, or external service.
    """

    def __init__(self, chunk_size: int, chunk_overlap: int) -> None:
        """Initialise the chunker with the given window parameters.

        Args:
            chunk_size:    Target character count per chunk.  Must be > 0.
            chunk_overlap: Characters shared between consecutive chunks.
                           Must satisfy ``0 <= chunk_overlap < chunk_size``.

        Raises:
            ValueError: When either parameter violates the constraints above.
        """
        if chunk_size <= 0:
            raise ValueError(
                f"chunk_size must be a positive integer, got {chunk_size}."
            )
        if chunk_overlap < 0:
            raise ValueError(
                f"chunk_overlap must be non-negative, got {chunk_overlap}."
            )
        if chunk_overlap >= chunk_size:
            raise ValueError(
                f"chunk_overlap ({chunk_overlap}) must be strictly less than "
                f"chunk_size ({chunk_size})."
            )
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def chunk_document(
        self,
        parsed_document: ParsedDocument,
        *,
        document_id: str,
        tenant_id: str,
        agent_id: str,
        knowledge_base_id: str,
        source_name: str,
    ) -> list[Chunk]:
        """Produce an ordered list of ``Chunk`` objects from a parsed document.

        Pages are processed in the order they appear in
        ``parsed_document.pages``.  Pages that contain only whitespace are
        silently skipped.  The ``chunk_index`` is assigned globally across
        all pages so it is stable and monotonically increasing for the
        entire document.

        Args:
            parsed_document:   The output of a ``DocumentParser.parse()``
                               call.
            document_id:       Identifier of the parent ``Document`` entity.
            tenant_id:         Identifier of the owning tenant.
            agent_id:          Identifier of the agent that owns this document.
            knowledge_base_id: Identifier of the target knowledge base.
            source_name:       Logical source label (URL, system name, etc.)
                               inherited from the parent ``Document``.

        Returns:
            A non-empty, ordered list of ``Chunk`` domain objects.

        Raises:
            ChunkingError: When all pages are empty or whitespace-only so
                           no chunks can be produced.
        """
        # Filter empty pages.
        active_pages = [
            page
            for page in parsed_document.pages
            if page.content and page.content.strip()
        ]

        if not active_pages:
            raise ChunkingError(
                f"Document '{document_id}' produced no extractable text. "
                "All pages are empty or whitespace-only."
            )

        chunks: list[Chunk] = []
        global_chunk_index = 0

        for page in active_pages:
            windows = _slide(page.content, self._chunk_size, self._chunk_overlap)
            for window in windows:
                content_hash = _hash_content(window)
                chunk_id = _derive_chunk_id(document_id, global_chunk_index)
                chunks.append(
                    Chunk(
                        id=chunk_id,
                        tenant_id=tenant_id,
                        agent_id=agent_id,
                        knowledge_base_id=knowledge_base_id,
                        document_id=document_id,
                        source_name=source_name,
                        page_number=page.page_number,
                        chunk_index=global_chunk_index,
                        content=window,
                        content_hash=content_hash,
                    )
                )
                global_chunk_index += 1

        return chunks
