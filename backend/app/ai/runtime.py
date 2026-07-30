"""Provider-independent AI runtime used by the chat workflow."""

from backend.app.ai.contracts import (
    EmbeddingRequest,
    EmbeddingResult,
    GenerationRequest,
    GenerationResult,
)
from backend.app.ai.ports import EmbeddingProvider, GenerationProvider


class CoreAIRuntime:
    """Provider gateway for generation and embeddings.

    Conversation orchestration belongs to ``ChatWorkflow`` where LangGraph
    can coordinate retrieval, evidence policy, generation, and fallback.
    """

    def __init__(
        self,
        generation_provider: GenerationProvider,
        embedding_provider: EmbeddingProvider,
    ) -> None:
        self._generation_provider = generation_provider
        self._embedding_provider = embedding_provider

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
