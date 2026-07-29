"""Build and persist AI evaluation reports."""

from datetime import datetime, timezone
from pathlib import Path

from backend.app.evaluation.models import (
    EvaluationCaseResult,
    EvaluationReport,
    EvaluationSummary,
)


class EvaluationReportError(RuntimeError):
    """Raised when an evaluation report cannot be written."""


def build_evaluation_report(
    results: list[EvaluationCaseResult],
) -> EvaluationReport:
    """Aggregate individual case results into one report."""

    total_cases = len(results)
    passed_cases = sum(result.status == "passed" for result in results)
    failed_cases = sum(result.status == "failed" for result in results)
    error_cases = sum(result.status == "error" for result in results)

    pass_rate_percent = (
        round((passed_cases / total_cases) * 100, 2)
        if total_cases
        else 0.0
    )

    average_latency_ms = (
        round(
            sum(result.latency_ms for result in results) / total_cases,
            2,
        )
        if total_cases
        else 0.0
    )

    summary = EvaluationSummary(
        total_cases=total_cases,
        passed_cases=passed_cases,
        failed_cases=failed_cases,
        error_cases=error_cases,
        pass_rate_percent=pass_rate_percent,
        total_prompt_tokens=sum(
            result.prompt_tokens for result in results
        ),
        total_completion_tokens=sum(
            result.completion_tokens for result in results
        ),
        average_latency_ms=average_latency_ms,
    )

    return EvaluationReport(
        created_at=datetime.now(timezone.utc),
        summary=summary,
        results=results,
    )


def write_evaluation_report(
    report: EvaluationReport,
    path: Path,
) -> Path:
    """Write a report as formatted UTF-8 JSON."""

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            report.model_dump_json(indent=2),
            encoding="utf-8",
        )
    except OSError as exc:
        raise EvaluationReportError(
            "Evaluation report could not be written"
        ) from exc

    return path