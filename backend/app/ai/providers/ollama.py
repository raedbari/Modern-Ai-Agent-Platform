"""Memory-bounded Ollama embedding provider with transient retries."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from backend.app.ai.contracts import EmbeddingRequest, EmbeddingResult
from backend.app.core.config import Settings
from backend.app.domain.exceptions import EmbeddingError


LOGGER = logging.getLogger("maap.ollama_embeddings")

_RETRYABLE_STATUS_CODES = frozenset({408, 429, 500, 502, 503, 504})


class OllamaEmbeddingProvider:
    """Generate embeddings through Ollama using bounded runner options."""

    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._model_name = settings.ollama_embedding_model
        self._dimension = settings.embedding_dimension
        self._base_url = str(settings.ollama_base_url).rstrip("/")
        self._timeout = settings.ollama_timeout_seconds
        self._num_ctx = settings.ollama_embedding_num_ctx
        self._num_batch = settings.ollama_embedding_num_batch
        self._keep_alive = settings.ollama_embedding_keep_alive
        self._max_retries = settings.ollama_embedding_max_retries
        self._retry_base_seconds = (
            settings.ollama_embedding_retry_base_seconds
        )
        self._transport = transport

    async def embed(
        self,
        request: EmbeddingRequest,
    ) -> EmbeddingResult:
        """Generate and validate embedding vectors."""

        payload: dict[str, Any] = {
            "model": self._model_name,
            "input": request.texts,
            "dimensions": self._dimension,
            "truncate": True,
            "keep_alive": self._keep_alive,
            "options": {
                "num_ctx": self._num_ctx,
                "num_batch": self._num_batch,
            },
        }

        timeout = httpx.Timeout(self._timeout)
        async with httpx.AsyncClient(
            base_url=self._base_url,
            timeout=timeout,
            transport=self._transport,
        ) as client:
            response = await self._post_with_retries(client, payload)

        try:
            response_payload = response.json()
        except ValueError as exc:
            raise EmbeddingError(
                "Embedding provider returned an invalid response."
            ) from exc

        vectors = response_payload.get("embeddings")
        if not isinstance(vectors, list):
            raise EmbeddingError(
                "Embedding provider returned an invalid response."
            )

        if len(vectors) != len(request.texts):
            raise EmbeddingError(
                "Ollama returned an unexpected number of embeddings"
            )

        if any(
            not isinstance(vector, list)
            or len(vector) != self._dimension
            for vector in vectors
        ):
            raise EmbeddingError(
                "Ollama returned an unexpected embedding dimension"
            )

        return EmbeddingResult(
            embeddings=vectors,
            model=self._model_name,
            dimension=self._dimension,
        )

    async def _post_with_retries(
        self,
        client: httpx.AsyncClient,
        payload: dict[str, Any],
    ) -> httpx.Response:
        """POST one embedding request with bounded exponential backoff."""

        for attempt in range(self._max_retries + 1):
            try:
                response = await client.post("/api/embed", json=payload)
            except httpx.RequestError as exc:
                if attempt >= self._max_retries:
                    raise EmbeddingError(
                        "Embedding provider is temporarily unavailable."
                    ) from exc
                LOGGER.warning(
                    "Ollama embedding request failed before receiving a "
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
                "Ollama embedding request returned HTTP %s; retrying "
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
