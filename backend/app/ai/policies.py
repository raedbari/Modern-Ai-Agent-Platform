"""Agent runtime policy interfaces and decision boundaries.

Sprint 1 establishes policy boundaries WITHOUT implementing complex routing.
Current behavior: single provider selected at startup via Settings.

Future implementations can inject policy objects to enable:
- Multi-provider routing based on tenant tier, cost, latency
- Dynamic model selection based on task complexity
- Fallback strategies on provider unavailability
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from backend.app.ai.contracts import RuntimeContext


class RoutingPriority(Enum):
    """Priority factors for model selection (design only)."""

    QUALITY = "quality"
    LATENCY = "latency"
    COST = "cost"
    AVAILABILITY = "availability"


@dataclass(frozen=True)
class RoutingRequirements:
    """Requirements for model selection (design only - Sprint 1).

    Future ModelPolicy implementations will use these requirements to
    select appropriate providers/models at runtime.
    """

    priority: RoutingPriority = RoutingPriority.QUALITY
    max_latency_ms: int | None = None
    max_cost_per_1k_tokens: float | None = None
    data_classification: str | None = None  # e.g., "pii", "public"


class ModelPolicy(Protocol):
    """Policy interface for model/provider selection (design only - Sprint 1).

    Current behavior: single provider configured at startup.

    Future implementations could:
    - Route by tenant tier (free → fast model, paid → quality model)
    - Fall back on provider failure
    - Load balance across multiple provider instances
    - Route based on data classification (PII → on-prem model)
    """

    def select_model_for_generation(
        self,
        context: RuntimeContext,
        requirements: RoutingRequirements,
    ) -> str:
        """Select model identifier for generation request.

        Returns:
            Model identifier (e.g., "deepseek-v4-flash", "gpt-4")
        """
        ...

    def should_use_reranking(
        self,
        context: RuntimeContext,
    ) -> bool:
        """Decide whether to use reranking for this request.

        Future implementations could:
        - Disable reranking for low-tier tenants to reduce cost
        - Enable reranking only for complex queries
        - Skip reranking if retrieval candidate count is low
        """
        ...


class KnowledgePolicy:
    """Policy for knowledge retrieval behavior.

    This is already implemented in Agent model as knowledge_mode:
    - "required": No evidence → no factual answer (safe fallback)
    - "preferred": Evidence available → use it; no evidence → model may answer
    - "disabled": No knowledge retrieval
    """

    pass


@dataclass(frozen=True)
class PromptVersionMetadata:
    """Metadata for prompt version tracking.

    Used by evaluation platform to correlate results with specific prompts.
    Enables A/B testing and prompt improvement tracking.
    """

    version: str  # e.g., "v1", "v2.1", "2024-01-15-experiment-3"
    description: str | None = None
    created_at: str | None = None  # ISO 8601 timestamp
    parent_version: str | None = None  # For tracking prompt evolution


class BudgetPolicy(Protocol):
    """Policy for token/cost budget management (design only - Sprint 1).

    Future implementations could:
    - Track token usage per tenant
    - Enforce daily/monthly limits
    - Alert on approaching budget thresholds
    - Throttle requests when budget exceeded
    """

    async def check_budget_available(
        self,
        context: RuntimeContext,
        estimated_tokens: int,
    ) -> bool:
        """Check if tenant has budget for estimated token usage."""
        ...

    async def record_usage(
        self,
        context: RuntimeContext,
        prompt_tokens: int,
        completion_tokens: int,
        estimated_cost: float,
    ) -> None:
        """Record actual token usage and cost."""
        ...


class SafetyPolicy(Protocol):
    """Policy for content safety and moderation (design only - Sprint 1).

    Future implementations could:
    - Pre-screen user queries for prohibited content
    - Post-screen generated responses for policy violations
    - Apply tenant-specific content filters
    - Log and audit flagged interactions
    """

    async def validate_user_input(
        self,
        context: RuntimeContext,
        user_message: str,
    ) -> tuple[bool, str | None]:
        """Validate user input meets safety requirements.

        Returns:
            (is_valid, rejection_reason_if_invalid)
        """
        ...

    async def validate_generated_output(
        self,
        context: RuntimeContext,
        generated_text: str,
    ) -> tuple[bool, str | None]:
        """Validate generated output meets safety requirements.

        Returns:
            (is_valid, rejection_reason_if_invalid)
        """
        ...


# Current simple implementation used by Sprint 1
class DefaultModelPolicy:
    """Default model policy: single provider, no routing (Sprint 1).

    This implementation simply returns configured values from Settings.
    Future implementations can replace this with sophisticated routing.
    """

    def __init__(self, default_model: str, enable_reranking: bool = True):
        self._default_model = default_model
        self._enable_reranking = enable_reranking

    def select_model_for_generation(
        self,
        context: RuntimeContext,
        requirements: RoutingRequirements,
    ) -> str:
        """Return the configured default model."""
        return self._default_model

    def should_use_reranking(self, context: RuntimeContext) -> bool:
        """Return the configured reranking setting."""
        return self._enable_reranking
