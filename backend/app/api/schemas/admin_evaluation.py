"""Administrative Evaluation API contracts."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from backend.app.evaluation.models import (
    EvaluationCaseResult,
    EvaluationRunConfiguration,
    EvaluationSummary,
    RunStatus,
)


class EvaluationDatasetSummaryResponse(BaseModel):
    name: str
    owner: str
    domain: str
    version: str
    status: str
    classification: str
    case_count: int = Field(ge=1)


class EvaluationRunCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    dataset_name: str = Field(min_length=1, max_length=128)
    dataset_version: str = Field(min_length=1, max_length=64)
    tenant_id: str = Field(min_length=1, max_length=128)
    agent_id: str = Field(min_length=1, max_length=128)


class EvaluationRunResponse(BaseModel):
    run_id: str
    tenant_id: str
    agent_id: str
    configuration: EvaluationRunConfiguration
    started_at: datetime
    completed_at: datetime | None = None
    status: RunStatus
    results: list[EvaluationCaseResult]
    summary: EvaluationSummary
    failure_reason: str | None = None
