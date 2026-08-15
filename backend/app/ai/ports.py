"""Provider interfaces for the Core AI Runtime."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from backend.app.ai.contracts import (
    EmbeddingRequest,
    EmbeddingResult,
    GenerationRequest,
    GenerationResult,
)


@dataclass(frozen=True)
class RerankRequest:
    """Request to rerank candidate documents by relevance to a query."""

    query: str
    documents: list[str]
    top_k: int


@dataclass(frozen=True)
class RerankResult:
    """Result of reranking operation with ranked indices and scores."""

    ranked_indices: list[int]
    relevance_scores: list[float]


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


class RerankProvider(Protocol):
    """Interface implemented by document reranking providers.
    
    Reranking providers accept a query and a list of candidate documents,
    then return a reordered list optimized for relevance. This is typically
    used as a second-stage refinement after initial vector similarity search.
    
    The provider receives ONLY query text and document texts - no tenant IDs,
    credentials, or internal metadata should be transmitted.
    """

    async def rerank(
        self,
        request: RerankRequest,
    ) -> RerankResult:
        """Rerank documents by relevance to the query.
        
        Args:
            request: RerankRequest containing query, documents, and top_k limit.
            
        Returns:
            RerankResult with ranked_indices and relevance_scores.
            
        Raises:
            RetrievalError: When the reranking provider is unavailable.
        """
        ...