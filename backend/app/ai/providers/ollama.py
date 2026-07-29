"""Ollama embedding provider implemented with LangChain."""

from langchain_ollama import OllamaEmbeddings

from backend.app.ai.contracts import EmbeddingRequest, EmbeddingResult
from backend.app.core.config import Settings


class OllamaEmbeddingProvider:
    """Generate embeddings through local Ollama using LangChain."""

    def __init__(self, settings: Settings) -> None:
        self._model_name = settings.ollama_embedding_model
        self._dimension = settings.embedding_dimension

        self._model = OllamaEmbeddings(
            model=settings.ollama_embedding_model,
            base_url=str(settings.ollama_base_url).rstrip("/"),
            dimensions=settings.embedding_dimension,
            client_kwargs={
                "timeout": settings.ollama_timeout_seconds,
            },
        )

    async def embed(
        self,
        request: EmbeddingRequest,
    ) -> EmbeddingResult:
        """Generate and validate embedding vectors."""

        vectors = await self._model.aembed_documents(request.texts)

        if len(vectors) != len(request.texts):
            raise RuntimeError(
                "Ollama returned an unexpected number of embeddings"
            )

        if any(len(vector) != self._dimension for vector in vectors):
            raise RuntimeError(
                "Ollama returned an unexpected embedding dimension"
            )

        return EmbeddingResult(
            embeddings=vectors,
            model=self._model_name,
            dimension=self._dimension,
        )