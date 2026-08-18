"""SQLAlchemy persistence adapter for existing Evaluation contracts."""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import EvaluationRunRecord
from backend.app.evaluation.models import (
    EvaluationRun,
    EvaluationRunConfiguration,
    EvaluationSummary,
)


def empty_evaluation_summary() -> EvaluationSummary:
    return EvaluationSummary(
        total_cases=0,
        passed_cases=0,
        failed_cases=0,
        error_cases=0,
        pass_rate_percent=0,
        total_prompt_tokens=0,
        total_completion_tokens=0,
        average_latency_ms=0,
        failure_rate_percent=0,
    )


async def create_running_evaluation(
    session: AsyncSession,
    *,
    run_id: str,
    admin_id: str | None,
    tenant_id: str,
    agent_id: str,
    configuration: EvaluationRunConfiguration,
) -> EvaluationRunRecord:
    row = EvaluationRunRecord(
        run_id=run_id,
        created_by_admin_id=(
            admin_id if admin_id and admin_id != "legacy" else None
        ),
        tenant_id=tenant_id,
        agent_id=agent_id,
        configuration_json=configuration.model_dump(mode="json"),
        started_at=datetime.now(timezone.utc),
        status="running",
        results_json=[],
        summary_json=empty_evaluation_summary().model_dump(mode="json"),
    )
    session.add(row)
    await session.flush()
    return row


async def persist_evaluation_result(
    session: AsyncSession,
    run: EvaluationRun,
) -> None:
    row = await session.get(EvaluationRunRecord, run.run_id)
    if row is None:
        raise LookupError("Evaluation run not found")
    row.status = run.status
    row.started_at = run.started_at
    row.completed_at = run.completed_at
    row.configuration_json = run.configuration.model_dump(mode="json")
    row.results_json = [
        result.model_dump(mode="json") for result in run.results
    ]
    row.summary_json = run.summary.model_dump(mode="json")
    row.failure_reason = None


async def mark_evaluation_failed(
    session: AsyncSession,
    run_id: str,
) -> None:
    row = await session.get(EvaluationRunRecord, run_id)
    if row is None:
        return
    row.status = "failed"
    row.completed_at = datetime.now(timezone.utc)
    row.failure_reason = "Evaluation execution failed."


async def list_evaluation_runs(
    session: AsyncSession,
    *,
    limit: int,
) -> list[EvaluationRunRecord]:
    return list(
        (
            await session.scalars(
                select(EvaluationRunRecord)
                .order_by(
                    EvaluationRunRecord.started_at.desc(),
                    EvaluationRunRecord.run_id.desc(),
                )
                .limit(limit)
            )
        ).all()
    )
