"""Build and persist AI evaluation reports."""

from datetime import datetime, timezone
from pathlib import Path

from backend.app.evaluation.models import (
    EvaluationCaseResult,
    EvaluationReport,
    EvaluationRunConfiguration,
    EvaluationSummary,
)


class EvaluationReportError(RuntimeError):
    """Raised when an evaluation report cannot be written."""


def build_evaluation_report(
    results: list[EvaluationCaseResult],
    configuration: EvaluationRunConfiguration | None = None,
) -> EvaluationReport:
    """Aggregate individual case results into one report."""

    summary = build_evaluation_summary(results)

    return EvaluationReport(
        created_at=datetime.now(timezone.utc),
        configuration=configuration,
        summary=summary,
        results=results,
    )


def build_evaluation_summary(
    results: list[EvaluationCaseResult],
) -> EvaluationSummary:
    """Aggregate execution-derived case results without inventing metrics."""

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
        retrieval_hit_rate_percent=_optional_rate(
            [
                result.rag_metrics.retrieval_hit
                for result in results
                if result.rag_metrics is not None
                and result.rag_metrics.retrieval_status == "measured"
            ]
        ),
        expected_source_rate_percent=_optional_rate(
            [
                result.rag_metrics.top_k_source_presence
                for result in results
                if result.rag_metrics is not None
                and result.rag_metrics.top_k_source_presence is not None
            ]
        ),
        correct_refusal_rate_percent=_optional_rate(
            [
                result.rag_metrics.correct_refusal
                for result in results
                if result.rag_metrics is not None
                and result.rag_metrics.correct_refusal is not None
            ]
        ),
        citation_accuracy_rate_percent=_optional_rate(
            [
                result.rag_metrics.citation_accuracy
                for result in results
                if result.rag_metrics is not None
                and result.rag_metrics.citation_accuracy is not None
            ]
        ),
        failure_rate_percent=(
            round((error_cases / total_cases) * 100, 2)
            if total_cases
            else 0.0
        ),
    )
    return summary


def _optional_rate(values: list[bool | None]) -> float | None:
    measured = [value for value in values if value is not None]
    if not measured:
        return None
    return round((sum(measured) / len(measured)) * 100, 2)


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
