"""Voyage AI embedding and reranking providers.

Voyage AI is the authorised embedding and reranking backend for this
platform.  This module provides two separate provider classes:

- ``VoyageEmbeddingProvider``: wraps the Voyage embed endpoint and returns
  1024-dimensional vectors produced by ``voyage-4-large``.
- ``VoyageRerankProvider``: wraps the Voyage rerank endpoint using
  ``rerank-2.5`` to sort candidate chunks by relevance.

Neither class calls a paid API in tests.  All network I/O is confined to
the methods documented below; callers inject a custom ``transport`` for
testing — the ``voyageai`` SDK is NOT used so this module is importable
in any environment regardless of whether the SDK is installed.

Security
--------
Only the minimum data required by each Voyage endpoint is sent:
- Embedding: ``input_type`` + text list.
- Reranking: query string + candidate texts (no tenant IDs, no secrets).

Do NOT modify the model names or dimension constants in this file without
updating the database VECTOR column dimension and running a full migration.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any

import httpx

from backend.app.ai.ports import RerankRequest, RerankResult
from backend.app.ai.contracts import EmbeddingRequest, EmbeddingResult
from backend.app.core.config import Settings
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

# HTTP status codes that are safe to retry.
_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


# ---------------------------------------------------------------------------
# Rerank data transfer objects
# ---------------------------------------------------------------------------



# ---------------------------------------------------------------------------
# Voyage embedding provider
# ---------------------------------------------------------------------------


class VoyageEmbeddingProvider:
    """Embed query/document texts using Voyage AI ``voyage-4-large``.

    Communicates directly with the Voyage REST API over ``httpx``; the
    ``voyageai`` SDK is not required.  An injectable ``transport`` parameter
    allows tests to intercept HTTP traffic without network access.

    Args:
        settings:   Application settings.  ``settings.voyage_api_key`` must
                    be set; it is validated at construction time.
        transport:  Optional ``httpx.AsyncBaseTransport`` override.  Inject
                    a mock transport in tests to avoid real HTTP calls.
        input_type: Default Voyage ``input_type`` used when the
                    ``EmbeddingRequest`` does not specify one.  Defaults to
                    ``"document"`` (suitable for ingestion).  Pass
                    ``"query"`` when constructing a retrieval provider.
    """

    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
        input_type: str = VOYAGE_DOCUMENT_INPUT_TYPE,
    ) -> None:
        api_key = (
            settings.voyage_api_key.get_secret_value().strip()
            if settings.voyage_api_key is not None
            else ""
        )
        if not api_key:
            raise ValueError(
                "VOYAGE_API_KEY is required but not set in settings."
            )

        self._api_key = api_key
        self._model = settings.voyage_model
        self._base_url = str(settings.voyage_base_url).rstrip("/")
        self._dimension = settings.embedding_dimension
        self._default_input_type = input_type
        self._max_retries = settings.voyage_max_retries
        self._timeout = settings.voyage_timeout_seconds
        self._retry_base = settings.voyage_retry_base_seconds

        client_kwargs: dict[str, Any] = {
            "headers": {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            "timeout": self._timeout,
        }
        if transport is not None:
            client_kwargs["transport"] = transport

        self._client = httpx.AsyncClient(**client_kwargs)

    @property
    def model(self) -> str:
        return self._model

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

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

        payload = {
            "input": request.texts,
            "model": self._model,
            "input_type": request.input_type,
            "output_dimension": self._dimension,
        }

        response_data = await self._post_with_retry(
            f"{self._base_url}/embeddings",
            payload,
        )

        try:
            items: list[dict[str, Any]] = response_data["data"]
            vectors: list[list[float]] = [item["embedding"] for item in items]
        except Exception as exc:
            raise EmbeddingError(
                "Voyage AI returned an unexpected response structure."
            ) from exc

        if len(vectors) != len(request.texts):
            raise EmbeddingError(
                f"Voyage AI returned unexpected number of embeddings: "
                f"got {len(vectors)}, expected {len(request.texts)}."
            )

        for vec in vectors:
            if len(vec) != self._dimension:
                raise EmbeddingError(
                    f"Voyage AI returned embedding with incorrect dimension: "
                    f"got {len(vec)}, expected {self._dimension}."
                )

        return EmbeddingResult(
            embeddings=vectors,
            model=self._model,
            dimension=self._dimension,
        )

    async def _post_with_retry(
        self,
        url: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """POST ``payload`` to ``url``, retrying on transient errors.

        Raises:
            EmbeddingError: After all retries are exhausted or on a
                non-retryable HTTP error.
        """
        attempts = 0
        max_attempts = self._max_retries + 1

        while attempts < max_attempts:
            try:
                response = await self._client.post(
                    url,
                    content=json.dumps(payload).encode(),
                )
            except Exception as exc:
                raise EmbeddingError(
                    "Voyage AI request failed due to a network error."
                ) from exc

            if response.status_code == 200:
                try:
                    return response.json()
                except Exception as exc:
                    raise EmbeddingError(
                        "Voyage AI returned a non-JSON response."
                    ) from exc

            if response.status_code not in _RETRYABLE_STATUS_CODES:
                raise EmbeddingError(
                    f"Voyage AI embedding is temporarily unavailable "
                    f"(HTTP {response.status_code})."
                )

            attempts += 1
            if attempts < max_attempts:
                await asyncio.sleep(self._retry_base * (2 ** (attempts - 1)))

        raise EmbeddingError(
            "Voyage AI embedding is temporarily unavailable "
            f"after {max_attempts} attempt(s)."
        )


# ---------------------------------------------------------------------------
# Voyage rerank provider
# ---------------------------------------------------------------------------


class VoyageRerankProvider:
    """Rerank candidate chunks using Voyage AI ``rerank-2.5``.

    Only the query text and candidate chunk texts are sent to Voyage.
    No tenant IDs, internal IDs, or credentials are transmitted.

    Args:
        settings:  Application settings.  ``settings.voyage_api_key`` must
                   be set.
        transport: Optional ``httpx.AsyncBaseTransport`` override for tests.
    """

    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        api_key = (
            settings.voyage_api_key.get_secret_value().strip()
            if settings.voyage_api_key is not None
            else ""
        )
        if not api_key:
            raise ValueError(
                "VOYAGE_API_KEY is required but not set in settings."
            )

        self._api_key = api_key
        self._model = settings.voyage_rerank_model
        self._base_url = str(settings.voyage_base_url).rstrip("/")
        self._max_retries = settings.voyage_max_retries
        self._timeout = settings.voyage_timeout_seconds
        self._retry_base = settings.voyage_retry_base_seconds

        client_kwargs: dict[str, Any] = {
            "headers": {
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            "timeout": self._timeout,
        }
        if transport is not None:
            client_kwargs["transport"] = transport

        self._client = httpx.AsyncClient(**client_kwargs)

    @property
    def model(self) -> str:
        return self._model

    async def aclose(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.aclose()

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
            return RerankResult(ranked_indices=[], scores=[])

        payload = {
            "query": request.query,
            "documents": request.documents,
            "model": self._model,
            "top_k": (
                len(request.documents)
                if request.top_k is None
                else min(request.top_k, len(request.documents))
            ),
        }

        attempts = 0
        max_attempts = self._max_retries + 1

        while attempts < max_attempts:
            try:
                response = await self._client.post(
                    f"{self._base_url}/rerank",
                    content=json.dumps(payload).encode(),
                )
            except Exception as exc:
                raise RetrievalError(
                    "Voyage AI rerank request failed."
                ) from exc

            if response.status_code == 200:
                break

            if response.status_code not in _RETRYABLE_STATUS_CODES:
                raise RetrievalError(
                    f"Voyage AI rerank failed (HTTP {response.status_code})."
                )

            attempts += 1
            if attempts < max_attempts:
                await asyncio.sleep(self._retry_base * (2 ** (attempts - 1)))
        else:
            raise RetrievalError(
                "Voyage AI rerank request failed after all retries."
            )

        try:
            data = response.json()
            results = data["data"]
        except Exception as exc:
            raise RetrievalError(
                "Voyage AI returned an unexpected rerank response structure."
            ) from exc

        ranked_indices: list[int] = [item["index"] for item in results]
        relevance_scores: list[float] = [
            float(item["relevance_score"]) for item in results
        ]

        return RerankResult(
            ranked_indices=ranked_indices,
            scores=relevance_scores,
        )
