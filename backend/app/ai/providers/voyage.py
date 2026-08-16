"""Voyage AI embedding provider with retry logic and error handling."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Literal

import httpx

from backend.app.ai.contracts import EmbeddingRequest, EmbeddingResult
from backend.app.core.config import Settings
from backend.app.domain.exceptions import EmbeddingError, RetrievalError
from backend.app.ai.rerank import RerankRequest, RerankResult


LOGGER = logging.getLogger("maap.voyage_embeddings")

_RETRYABLE_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})

# Voyage AI voyage-4-large produces exactly 1024-dimensional embeddings
# for the Knowledge/RAG pipeline. This is a fixed requirement per DEV2.md.
VOYAGE_EMBEDDING_DIMENSION = 1024


class VoyageEmbeddingProvider:
    """Generate embeddings through Voyage AI API with retry logic."""

    def __init__(
        self,
        settings: Settings,
        *,
        input_type: Literal["document", "query"] = "document",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._model_name = settings.voyage_model
        self._input_type = input_type
        self._dimension = VOYAGE_EMBEDDING_DIMENSION
        self._base_url = str(settings.voyage_base_url).rstrip("/")
        self._timeout = settings.voyage_timeout_seconds
        self._max_retries = settings.voyage_max_retries
        self._retry_base_seconds = settings.voyage_retry_base_seconds
        self._transport = transport

        api_key = settings.voyage_api_key
        if api_key is None or not api_key.get_secret_value().strip():
            raise ValueError(
                "VOYAGE_API_KEY is required for VoyageEmbeddingProvider"
            )
        self._api_key = api_key.get_secret_value().strip()

    async def embed(
        self,
        request: EmbeddingRequest,
    ) -> EmbeddingResult:
        """Generate and validate embedding vectors."""

        payload: dict[str, Any] = {
            "input": request.texts,
            "model": self._model_name,
            "input_type": self._input_type,
            "output_dimension": VOYAGE_EMBEDDING_DIMENSION,
        }

        timeout = httpx.Timeout(self._timeout)
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout,
            headers=headers,
            transport=self._transport,
        ) as client:
            response = await self._post_with_retries(client, payload)

        try:
            response_payload = response.json()
        except ValueError as exc:
            raise EmbeddingError(
                "Embedding provider returned an invalid response."
            ) from exc

        data = response_payload.get("data")
        if not isinstance(data, list):
            raise EmbeddingError(
                "Embedding provider returned an invalid response."
            )

        vectors = [item.get("embedding") for item in data]

        if len(vectors) != len(request.texts):
            raise EmbeddingError(
                "Voyage returned an unexpected number of embeddings"
            )

        if any(
            not isinstance(vector, list)
            or len(vector) != VOYAGE_EMBEDDING_DIMENSION
            for vector in vectors
        ):
            raise EmbeddingError(
                f"Voyage returned embeddings with incorrect dimension; "
                f"expected exactly {VOYAGE_EMBEDDING_DIMENSION}"
            )

        return EmbeddingResult(
            embeddings=vectors,
            model=self._model_name,
            dimension=VOYAGE_EMBEDDING_DIMENSION,
        )

    async def _post_with_retries(
        self,
        client: httpx.AsyncClient,
        payload: dict[str, Any],
    ) -> httpx.Response:
        """POST one embedding request with bounded exponential backoff."""

        for attempt in range(self._max_retries + 1):
            try:
                response = await client.post("/embeddings", json=payload)
            except httpx.RequestError as exc:
                if attempt >= self._max_retries:
                    raise EmbeddingError(
                        "Embedding provider is temporarily unavailable."
                    ) from exc
                LOGGER.warning(
                    "Voyage embedding request failed before receiving a "
                    "response; retrying (%s/%s).",
                    attempt + 1,
                    self._max_retries,
                )
                await self._sleep_before_retry(attempt)
                continue

            if response.status_code < 400:
                return response

            if (
                response.status_code not in _RETRYABLE_STATUS_CODES
                or attempt >= self._max_retries
            ):
                raise EmbeddingError(
                    "Embedding provider is temporarily unavailable."
                )

            LOGGER.warning(
                "Voyage embedding request returned HTTP %s; retrying "
                "(%s/%s).",
                response.status_code,
                attempt + 1,
                self._max_retries,
            )
            await self._sleep_before_retry(attempt)

        raise EmbeddingError("Embedding provider is temporarily unavailable.")

    async def _sleep_before_retry(self, attempt: int) -> None:
        delay = self._retry_base_seconds * (2**attempt)
        if delay > 0:
            await asyncio.sleep(delay)


class VoyageRerankProvider:
    """Rerank tenant-filtered RAG candidates with Voyage AI."""

    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        api_key = settings.voyage_api_key

        if (
            api_key is None
            or not api_key.get_secret_value().strip()
        ):
            raise ValueError(
                "VOYAGE_API_KEY is required for VoyageRerankProvider"
            )

        self._api_key = api_key.get_secret_value().strip()
        self._model_name = settings.voyage_rerank_model
        self._base_url = str(
            settings.voyage_base_url
        ).rstrip("/")
        self._timeout = settings.voyage_timeout_seconds
        self._max_retries = settings.voyage_max_retries
        self._retry_base_seconds = (
            settings.voyage_retry_base_seconds
        )
        self._transport = transport

    async def rerank(
        self,
        request: RerankRequest,
    ) -> RerankResult:
        if not request.documents:
            return RerankResult(
                ranked_indices=[],
                scores=[],
            )

        payload = {
            "query": request.query,
            "documents": request.documents,
            "model": self._model_name,
            "top_k": (
                len(request.documents)
                if request.top_k is None
                else min(request.top_k, len(request.documents))
            ),
        }

        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(self._timeout),
            headers=headers,
            transport=self._transport,
        ) as client:
            response = await self._post_with_retries(
                client,
                payload,
            )

        try:
            body = response.json()
        except ValueError as exc:
            raise RetrievalError(
                "Rerank provider returned an invalid response."
            ) from exc

        data = body.get("data")

        if not isinstance(data, list):
            raise RetrievalError(
                "Rerank provider returned an invalid response."
            )

        indices: list[int] = []
        scores: list[float] = []

        for item in data:
            if not isinstance(item, dict):
                raise RetrievalError(
                    "Rerank provider returned an invalid result."
                )

            index = item.get("index")
            score = item.get("relevance_score")

            if (
                not isinstance(index, int)
                or not isinstance(score, (int, float))
                or index < 0
                or index >= len(request.documents)
            ):
                raise RetrievalError(
                    "Rerank provider returned an invalid result."
                )

            indices.append(index)
            scores.append(float(score))

        return RerankResult(
            ranked_indices=indices,
            scores=scores,
        )

    async def _post_with_retries(
        self,
        client: httpx.AsyncClient,
        payload: dict[str, Any],
    ) -> httpx.Response:
        for attempt in range(self._max_retries + 1):
            try:
                response = await client.post(
                    "/rerank",
                    json=payload,
                )
            except httpx.RequestError as exc:
                if attempt >= self._max_retries:
                    raise RetrievalError(
                        "Rerank provider is temporarily unavailable."
                    ) from exc

                await self._sleep_before_retry(attempt)
                continue

            if response.status_code < 400:
                return response

            if (
                response.status_code not in _RETRYABLE_STATUS_CODES
                or attempt >= self._max_retries
            ):
                raise RetrievalError(
                    "Rerank provider is temporarily unavailable."
                )

            await self._sleep_before_retry(attempt)

        raise RetrievalError(
            "Rerank provider is temporarily unavailable."
        )

    async def _sleep_before_retry(
        self,
        attempt: int,
    ) -> None:
        delay = self._retry_base_seconds * (2**attempt)

        if delay > 0:
            await asyncio.sleep(delay)
