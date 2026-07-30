"""EmbeddingProvider port interface.

Defines the contract for converting text into dense vector representations.
The service layer depends only on this interface; infrastructure code (Ollama,
OpenAI, etc.) implements it without the domain layer knowing the provider.

All methods are declared async to support HTTP-based providers without
blocking the event loop.
"""

from __future__ import annotations

from abc import ABC, abstractmethod


class EmbeddingProvider(ABC):
    """Contract for any service that produces text embeddings.

    Implementations are responsible for:
    - Managing the HTTP connection to the underlying model server.
    - Returning vectors whose dimensionality matches ``Settings.embedding_dimensions``.
    - Raising ``EmbeddingError`` on any provider-side failure so callers do not
      need to handle provider-specific exceptions.
    """

    @abstractmethod
    async def embed_text(self, text: str) -> list[float]:
        """Produce a single embedding vector for the given text.

        Use this method for query-time embedding (one query string per
        retrieval request).  For bulk ingestion, prefer ``embed_batch``.

        Args:
            text: The input text to embed.  Must not be empty.

        Returns:
            A dense vector of floats whose length equals
            ``Settings.embedding_dimensions``.

        Raises:
            ValueError:      When ``text`` is empty.
            EmbeddingError:  When the provider fails to return a valid
                             embedding (network error, model error, etc.).
        """

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Produce embedding vectors for a list of texts in a single call.

        Use this method during document ingestion to embed chunks
        efficiently.  The returned list preserves the input order so that
        ``result[i]`` is the embedding for ``texts[i]``.

        Args:
            texts: A non-empty list of input texts.  Individual items must
                   not be empty strings.

        Returns:
            A list of dense vectors, one per input text, each of length
            ``Settings.embedding_dimensions``.

        Raises:
            ValueError:      When ``texts`` is empty or contains empty strings.
            EmbeddingError:  When the provider fails for any item in the batch.
        """
