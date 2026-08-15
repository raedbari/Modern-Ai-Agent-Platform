"""Provider-independent reranking contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class RerankRequest:
    query: str
    documents: list[str]
    top_k: int


@dataclass(frozen=True)
class RerankResult:
    ranked_indices: list[int]
    relevance_scores: list[float]


class RerankProvider(Protocol):
    async def rerank(
        self,
        request: RerankRequest,
    ) -> RerankResult:
        """Rerank documents for a query."""
        ...
