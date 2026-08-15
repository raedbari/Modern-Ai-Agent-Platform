"""Data contracts for AI evaluation scenarios."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime

class EvaluationExpectations(BaseModel):
    """Conditions used later to evaluate a generated response."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    expected_language: Literal["ar", "en", "de"] | None = None
    required_substrings: list[str] = Field(default_factory=list)
    forbidden_substrings: list[str] = Field(default_factory=list)
    max_latency_ms: int | None = Field(default=None, gt=0)


class EvaluationCase(BaseModel):
    """One independent evaluation scenario."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    case_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    agent_id: str = Field(min_length=1)
    user_input: str = Field(min_length=1)
    expectations: EvaluationExpectations = Field(
        default_factory=EvaluationExpectations
    )
    tags: list[str] = Field(default_factory=list)

class RAGMetrics(BaseModel):
    """RAG-specific metrics for retrieval quality (Sprint 1)."""

    model_config = ConfigDict(frozen=True)

    retrieval_hit: bool | None = None  # Was any evidence retrieved?
    retrieval_count: int = Field(default=0, ge=0)  # Number of chunks retrieved
    top_similarity_score: float | None = Field(default=None, ge=0.0, le=1.0)
    rerank_position_change: int | None = None  # Position shift after reranking
    has_citations: bool = False  # Does response include [S1], [S2] citations?
    citation_count: int = Field(default=0, ge=0)
    answer_status: str | None = None  # grounded | generated | insufficient_knowledge | temporarily_unavailable


class EvaluationChecks(BaseModel):
    """Deterministic checks performed against one generated response."""

    model_config = ConfigDict(frozen=True)

    language_matches: bool | None = None
    required_substrings_present: bool = True
    forbidden_substrings_absent: bool = True
    latency_within_limit: bool | None = None


class EvaluationCaseResult(BaseModel):
    """Normalized result of executing one evaluation case."""

    model_config = ConfigDict(frozen=True)

    case_id: str
    tenant_id: str
    agent_id: str
    status: Literal["passed", "failed", "error"]

    response_content: str | None = None
    model: str | None = None
    finish_reason: str | None = None

    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)
    latency_ms: float = Field(ge=0)

    checks: EvaluationChecks
    rag_metrics: RAGMetrics | None = None  # NEW: RAG-specific metrics
    prompt_version: str | None = None  # NEW: Track prompt version
    error_code: Literal["generation_failed"] | None = None

class EvaluationSummary(BaseModel):
    """Aggregated metrics for one evaluation run."""

    model_config = ConfigDict(frozen=True)

    total_cases: int = Field(ge=0)
    passed_cases: int = Field(ge=0)
    failed_cases: int = Field(ge=0)
    error_cases: int = Field(ge=0)
    pass_rate_percent: float = Field(ge=0, le=100)
    total_prompt_tokens: int = Field(ge=0)
    total_completion_tokens: int = Field(ge=0)
    average_latency_ms: float = Field(ge=0)


class EvaluationReport(BaseModel):
    """Complete serializable report for one evaluation run."""

    model_config = ConfigDict(frozen=True)

    created_at: datetime
    summary: EvaluationSummary
    results: list[EvaluationCaseResult]