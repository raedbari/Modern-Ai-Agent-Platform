"""Tests for evaluation report generation."""

import json

from backend.app.evaluation.models import (
    EvaluationCaseResult,
    EvaluationChecks,
)
from backend.app.evaluation.report import (
    build_evaluation_report,
    write_evaluation_report,
)


def _make_result(
    case_id: str,
    status: str,
    latency_ms: float,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
) -> EvaluationCaseResult:
    return EvaluationCaseResult(
        case_id=case_id,
        tenant_id="tenant-1",
        agent_id="agent-1",
        status=status,
        latency_ms=latency_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        checks=EvaluationChecks(),
        error_code=(
            "generation_failed"
            if status == "error"
            else None
        ),
    )


def test_builds_aggregated_report():
    results = [
        _make_result("case-1", "passed", 10, 5, 3),
        _make_result("case-2", "failed", 20, 7, 4),
        _make_result("case-3", "error", 30),
    ]

    report = build_evaluation_report(results)

    assert report.summary.total_cases == 3
    assert report.summary.passed_cases == 1
    assert report.summary.failed_cases == 1
    assert report.summary.error_cases == 1
    assert report.summary.pass_rate_percent == 33.33
    assert report.summary.total_prompt_tokens == 12
    assert report.summary.total_completion_tokens == 7
    assert report.summary.average_latency_ms == 20.0


def test_writes_report_as_json(tmp_path):
    report = build_evaluation_report(
        [_make_result("case-1", "passed", 12.5)]
    )
    output_path = tmp_path / "reports" / "result.json"

    returned_path = write_evaluation_report(
        report,
        output_path,
    )

    payload = json.loads(output_path.read_text(encoding="utf-8"))

    assert returned_path == output_path
    assert payload["summary"]["total_cases"] == 1
    assert payload["summary"]["passed_cases"] == 1
    assert payload["results"][0]["case_id"] == "case-1"
    assert payload["created_at"]