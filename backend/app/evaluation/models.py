"""Versioned, reusable data contracts for Agent Runtime evaluation."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MeasurementStatus = Literal["measured", "not_measured"]
RunStatus = Literal["running", "completed", "failed"]


class EvaluationExpectations(BaseModel):
    """Conditions used later to evaluate a generated response."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    expected_language: Literal["ar", "en", "de"] | None = None
    required_substrings: list[str] = Field(default_factory=list)
    forbidden_substrings: list[str] = Field(default_factory=list)
    expected_answer: str | None = None
    expected_facts: list[str] = Field(default_factory=list)
    expected_source_ids: list[str] = Field(default_factory=list)
    allowed_variations: list[str] = Field(default_factory=list)
    forbidden_claims: list[str] = Field(default_factory=list)
    answerable: bool | None = None
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
    category: str = "general"
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    language: Literal["ar", "en", "de"] | None = None
    dialect: str | None = None
    expectations: EvaluationExpectations = Field(
        default_factory=EvaluationExpectations
    )
    tags: list[str] = Field(default_factory=list)


class EvaluationDataset(BaseModel):
    """Metadata and records for one immutable dataset version."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1)
    owner: str = Field(min_length=1)
    domain: str = Field(min_length=1)
    version: str = Field(min_length=1)
    status: Literal["draft", "active", "retired"]
    classification: str = Field(min_length=1)
    records: list[EvaluationCase] = Field(min_length=1)


class EvaluationRunConfiguration(BaseModel):
    """Versions required to reproduce an evaluation run."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    dataset_name: str
    dataset_version: str
    agent_version: str
    prompt_version: str
    knowledge_version: str | None = None
    model_provider: str
    model_name: str


class RAGMetrics(BaseModel):
    """RAG-specific metrics for retrieval quality (Sprint 1)."""

    model_config = ConfigDict(frozen=True)

    retrieval_hit: bool | None = None  # Was any evidence retrieved?
    retrieval_count: int = Field(default=0, ge=0)
    top_similarity_score: float | None = Field(default=None, ge=0.0, le=1.0)
    rerank_position_change: int | None = None  # Position shift after reranking
    expected_source_position: int | None = Field(default=None, ge=1)
    rerank_count: int | None = Field(default=None, ge=0)
    has_citations: bool = False  # Does response include [S1], [S2] citations?
    citation_count: int = Field(default=0, ge=0)
    answer_status: Literal[
        "grounded",
        "generated",
        "insufficient_knowledge",
        "temporarily_unavailable",
        "answered",
        "no_results",
        "insufficient_evidence",
        "refused",
        "error",
    ] | None = None
    top_k_source_presence: bool | None = None
    groundedness: bool | None = None
    correct_refusal: bool | None = None
    citation_accuracy: bool | None = None
    failure: bool = False
    retrieval_status: MeasurementStatus = "not_measured"
    rerank_status: MeasurementStatus = "not_measured"
    groundedness_status: MeasurementStatus = "not_measured"
    citation_status: MeasurementStatus = "not_measured"
    token_usage_status: MeasurementStatus = "measured"
    estimated_cost: float | None = Field(default=None, ge=0)
    estimated_cost_status: MeasurementStatus = "not_measured"
    supplied_source_ids: list[str] = Field(default_factory=list)
    cited_source_ids: list[str] = Field(default_factory=list)
    invalid_citation_ids: list[str] = Field(default_factory=list)
    correctly_cited_expected_source_ids: list[str] = Field(default_factory=list)


class EvaluationChecks(BaseModel):
    """Deterministic checks performed against one generated response."""

    model_config = ConfigDict(frozen=True)

    language_matches: bool | None = None
    required_substrings_present: bool = True
    forbidden_substrings_absent: bool = True
    latency_within_limit: bool | None = None
    expected_facts_present: bool | None = None
    forbidden_claims_absent: bool | None = None


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
    knowledge_version: str | None = None
    model_provider: str | None = None
    answer_status: str | None = None
    error_code: Literal["generation_failed", "pipeline_failed"] | None = None


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
    retrieval_hit_rate_percent: float | None = Field(default=None, ge=0, le=100)
    expected_source_rate_percent: float | None = Field(default=None, ge=0, le=100)
    correct_refusal_rate_percent: float | None = Field(default=None, ge=0, le=100)
    citation_accuracy_rate_percent: float | None = Field(default=None, ge=0, le=100)
    failure_rate_percent: float = Field(default=0, ge=0, le=100)


class EvaluationReport(BaseModel):
    """Complete serializable report for one evaluation run."""

    model_config = ConfigDict(frozen=True)

    created_at: datetime
    configuration: EvaluationRunConfiguration | None = None
    summary: EvaluationSummary
    results: list[EvaluationCaseResult]


class EvaluationRun(BaseModel):
    """One minimal, reproducible execution of a versioned dataset."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    configuration: EvaluationRunConfiguration
    started_at: datetime
    completed_at: datetime | None = None
    status: RunStatus
    results: list[EvaluationCaseResult]
    summary: EvaluationSummary


class ExperimentComparison(BaseModel):
    """Minimal versioned A/B comparison record for future experiments."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    experiment_id: str
    dataset_name: str
    dataset_version: str
    configuration_a: EvaluationRunConfiguration
    configuration_b: EvaluationRunConfiguration
    metrics_a: dict[str, float | int | bool | None]
    metrics_b: dict[str, float | int | bool | None]
