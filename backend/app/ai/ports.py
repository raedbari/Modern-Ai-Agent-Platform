"""Provider interfaces for the Core AI Runtime."""

from typing import Protocol

from backend.app.ai.contracts import (
    EmbeddingRequest,
    EmbeddingResult,
    GenerationRequest,
    GenerationResult,
)


class GenerationProvider(Protocol):
    """Interface implemented by AI text-generation providers."""

    async def generate(
        self,
        request: GenerationRequest,
    ) -> GenerationResult:
        """Generate a normalized response."""
        ...


class EmbeddingProvider(Protocol):
    """Interface implemented by embedding providers."""

    async def embed(
        self,
        request: EmbeddingRequest,
    ) -> EmbeddingResult:
        """Generate normalized embedding vectors."""
        ...