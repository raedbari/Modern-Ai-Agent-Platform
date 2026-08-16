"""Voyage AI embedding and reranking providers.

Voyage AI is the authorised embedding and reranking backend for this
platform.  This module provides two separate provider classes:

- ``VoyageEmbeddingProvider``: wraps the Voyage embed endpoint and returns
  1024-dimensional vectors produced by ``voyage-4-large``.
- ``VoyageRerankProvider``: wraps the Voyage rerank endpoint using
  ``rerank-2.5`` to sort candidate chunks by relevance.

Neither class calls a paid API in tests.  All network I/O is confined to
the methods documented below; callers inject fakes/mocks for testing.

Security
--------
Only the minimum data required by each Voyage endpoint is sent:
- Embedding: ``input_type`` + text list.
- Reranking: query string + candidate texts (no tenant IDs, no secrets).

Do NOT modify the model names or dimension constants in this file without
updating the database VECTOR column dimension and running a full migration.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

import voyageai  # type: ignore[import-untyped]

from backend.app.ai.contracts import EmbeddingRequest, EmbeddingResult
from backend.app.domain.exceptions import EmbeddingError, RetrievalError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants — must match the pgvector VECTOR(1024) column definition.
# ---------------------------------------------------------------------------

VOYAGE_EMBEDDING_MODEL = "voyage-4-large"
VOYAGE_EMBEDDING_DIMENSION = 1024
VOYAGE_QUERY_INPUT_TYPE = "query"        # Voyage: optimises vectors for retrieval queries
VOYAGE_DOCUMENT_INPUT_TYPE = "document"  # Voyage: optimises vectors for document storage
VOYAGE_RERANK_MODEL = "rerank-2.5"


# ---------------------------------------------------------------------------
# Rerank data transfer objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RerankRequest:
    """Input required to rerank a list of candidate documents."""

    query: str
    documents: list[str]
    top_k: int


@dataclass(frozen=True)
class RerankResult:
    """Reranked indices into the original ``documents`` list.

    ``ranked_indices`` is ordered from most to least relevant.  Each value
    is the zero-based index of the document in the original input list.
    ``relevance_scores`` mirrors the same ordering.
    """

    ranked_indices: list[int]
    relevance_scores: list[float]


# ---------------------------------------------------------------------------
# Voyage embedding provider
# ---------------------------------------------------------------------------


class VoyageEmbeddingProvider:
    """Embed query/document texts using Voyage AI ``voyage-4-large``.

    Args:
        api_key: Voyage AI API key.  Must not be empty.
        model:   Override the model name.  Defaults to ``voyage-4-large``.
    """

    def __init__(
        self,
        api_key: str,
        *,
        model: str = VOYAGE_EMBEDDING_MODEL,
    ) -> None:
        if not api_key or not api_key.strip():
            raise ValueError("Voyage AI API key must not be empty.")
        self._model = model
        self._client = voyageai.AsyncClient(api_key=api_key)

    @property
    def model(self) -> str:
        return self._model

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        """Embed one or more texts with the correct Voyage ``input_type``.

        Voyage AI optimises vector representations differently depending on
        whether the text will be stored (``input_type="document"``) or used
        as a retrieval query (``input_type="query"``).  The caller signals
        intent via ``request.input_type``:

        - ``"document"`` — use for document chunks being written to pgvector.
        - ``"query"``    — use for retrieval queries at search time.

        Args:
            request: An ``EmbeddingRequest`` containing the text(s) to embed
                     and the ``input_type`` hint.

        Returns:
            An ``EmbeddingResult`` with ``dimension=1024`` vectors.

        Raises:
            EmbeddingError: When the Voyage API call fails or returns an
                unexpected response shape.
        """
        if not request.texts:
            raise EmbeddingError("EmbeddingRequest.texts must not be empty.")

        try:
            response = await self._client.embed(
                request.texts,
                model=self._model,
                input_type=request.input_type,
            )
        except Exception as exc:
            raise EmbeddingError(
                "Voyage AI embedding request failed."
            ) from exc

        vectors: list[list[float]] = response.embeddings

        if len(vectors) != len(request.texts):
            raise EmbeddingError(
                f"Voyage AI returned {len(vectors)} vector(s) for "
                f"{len(request.texts)} input(s)."
            )

        for vec in vectors:
            if len(vec) != VOYAGE_EMBEDDING_DIMENSION:
                raise EmbeddingError(
                    f"Voyage AI returned a vector of dimension {len(vec)}; "
                    f"expected {VOYAGE_EMBEDDING_DIMENSION}."
                )

        return EmbeddingResult(
            embeddings=vectors,
            model=self._model,
            dimension=VOYAGE_EMBEDDING_DIMENSION,
        )


# ---------------------------------------------------------------------------
# Voyage rerank provider
# ---------------------------------------------------------------------------


class VoyageRerankProvider:
    """Rerank candidate chunks using Voyage AI ``rerank-2.5``.

    Only the query text and candidate chunk texts are sent to Voyage.
    No tenant IDs, internal IDs, or credentials are transmitted.

    Args:
        api_key: Voyage AI API key.  Must not be empty.
        model:   Override the model name.  Defaults to ``rerank-2.5``.
    """

    def __init__(
        self,
        api_key: str,
        *,
        model: str = VOYAGE_RERANK_MODEL,
    ) -> None:
        if not api_key or not api_key.strip():
            raise ValueError("Voyage AI API key must not be empty.")
        self._model = model
        self._client = voyageai.AsyncClient(api_key=api_key)

    @property
    def model(self) -> str:
        return self._model

    async def rerank(self, request: RerankRequest) -> RerankResult:
        """Rerank candidate documents by relevance to a query.

        Args:
            request: A ``RerankRequest`` carrying query, candidate texts,
                     and the desired number of final results.

        Returns:
            A ``RerankResult`` with ranked indices into the original
            candidates list, ordered from most to least relevant.

        Raises:
            RetrievalError: When the Voyage API call fails.
        """
        if not request.documents:
            return RerankResult(ranked_indices=[], relevance_scores=[])

        try:
            response = await self._client.rerank(
                request.query,
                request.documents,
                model=self._model,
                top_k=min(request.top_k, len(request.documents)),
            )
        except Exception as exc:
            raise RetrievalError(
                "Voyage AI rerank request failed."
            ) from exc

        ranked_indices: list[int] = [item.index for item in response.results]
        relevance_scores: list[float] = [
            float(item.relevance_score) for item in response.results
        ]

        return RerankResult(
            ranked_indices=ranked_indices,
            relevance_scores=relevance_scores,
        )
