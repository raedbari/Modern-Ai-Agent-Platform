"""Provider-independent AI runtime used by the chat workflow."""

from backend.app.ai.contracts import (
    EmbeddingRequest,
    EmbeddingResult,
    GenerationRequest,
    GenerationResult,
)
from backend.app.ai.ports import (
    EmbeddingProvider,
    GenerationProvider,
    RerankProvider,
    RerankRequest,
    RerankResult,
)


class CoreAIRuntime:
    """Provider gateway for generation, embeddings, and reranking.

    Conversation orchestration belongs to ``ChatWorkflow`` where LangGraph
    can coordinate retrieval, evidence policy, generation, and fallback.

    Reranking is optional and injected at construction. When None, callers
    (e.g., RetrievalService) degrade gracefully to pgvector-only ranking.
    """

    def __init__(
        self,
        generation_provider: GenerationProvider,
        embedding_provider: EmbeddingProvider,
        *,
        rerank_provider: RerankProvider | None = None,
    ) -> None:
        self._generation_provider = generation_provider
        self._embedding_provider = embedding_provider
        self._rerank_provider = rerank_provider

    async def generate(
        self,
        request: GenerationRequest,
    ) -> GenerationResult:
        return await self._generation_provider.generate(request)

    async def embed(
        self,
        request: EmbeddingRequest,
    ) -> EmbeddingResult:
        return await self._embedding_provider.embed(request)

    async def rerank(
        self,
        request: RerankRequest,
    ) -> RerankResult:
        """Rerank documents using the configured provider.

        Raises:
            ValueError: When no rerank provider is configured.
        """
        if self._rerank_provider is None:
            raise ValueError("No rerank provider configured in CoreAIRuntime")
        return await self._rerank_provider.rerank(request)
