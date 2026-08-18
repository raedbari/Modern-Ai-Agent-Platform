"""Platform Admin endpoints for real Evaluation executions."""

from __future__ import annotations

import logging
from typing import Annotated, Any, cast
from uuid import uuid4

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
)

from backend.app.ai.chat_workflow import ChatWorkflow
from backend.app.api.dependencies import (
    get_core_ai_runtime,
    get_rerank_provider,
    get_telemetry_sink,
    require_admin_access,
    require_permission,
)
from backend.app.api.schemas.admin_evaluation import (
    EvaluationDatasetSummaryResponse,
    EvaluationRunCreateRequest,
    EvaluationRunResponse,
)
from backend.app.auth.admin_context import AdminContext
from backend.app.auth.context import ChatExecutionContext
from backend.app.core.config import Settings, get_settings
from backend.app.db.base import get_db
from backend.app.db.models import Agent, EvaluationRunRecord, Tenant
from backend.app.evaluation.catalog import (
    get_evaluation_dataset,
    list_evaluation_datasets,
)
from backend.app.evaluation.loader import EvaluationDatasetError
from backend.app.evaluation.models import (
    EvaluationCaseResult,
    EvaluationDataset,
    EvaluationRunConfiguration,
    EvaluationSummary,
    RunStatus,
)
from backend.app.evaluation.persistence import (
    create_running_evaluation,
    list_evaluation_runs,
    mark_evaluation_failed,
    persist_evaluation_result,
)
from backend.app.evaluation.runner import EvaluationRunner
from backend.app.infrastructure.database.repositories import (
    SQLAlchemyChunkRepository,
    SQLAlchemyKnowledgeBaseRepository,
)
from backend.app.services.chat import GenerationRuntime
from backend.app.services.knowledge.retrieval_service import RetrievalService
from backend.app.telemetry import TelemetrySink


LOGGER = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/admin/evaluation",
    tags=["admin-evaluation"],
    dependencies=[Depends(require_admin_access)],
)


def _dataset_not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Evaluation dataset not found",
    )


def _run_response(row: EvaluationRunRecord) -> EvaluationRunResponse:
    return EvaluationRunResponse(
        run_id=row.run_id,
        tenant_id=row.tenant_id,
        agent_id=row.agent_id,
        configuration=EvaluationRunConfiguration.model_validate(
            row.configuration_json
        ),
        started_at=row.started_at,
        completed_at=row.completed_at,
        status=cast(RunStatus, row.status),
        results=[
            EvaluationCaseResult.model_validate(item)
            for item in row.results_json
        ],
        summary=EvaluationSummary.model_validate(row.summary_json),
        failure_reason=row.failure_reason,
    )


async def _execute_evaluation_run(
    *,
    session_factory: async_sessionmaker[AsyncSession],
    run_id: str,
    dataset: EvaluationDataset,
    configuration: EvaluationRunConfiguration,
    execution_context: ChatExecutionContext,
    runtime: GenerationRuntime,
    rerank_provider: Any,
    telemetry_sink: TelemetrySink,
    settings: Settings,
) -> None:
    """Execute after the response using a fresh database unit of work."""

    async with session_factory() as session:
        try:
            retrieval = RetrievalService(
                embedding_provider=runtime,
                chunk_repository=SQLAlchemyChunkRepository(
                    session,
                    embedding_dimension=settings.embedding_dimension,
                ),
                kb_repository=SQLAlchemyKnowledgeBaseRepository(session),
                rerank_provider=rerank_provider,
                retrieval_candidate_count=settings.retrieval_candidate_count,
            )
            workflow = ChatWorkflow(
                runtime,
                retrieval=retrieval,
                retrieval_top_k=settings.retrieval_top_k,
                retrieval_min_similarity=settings.retrieval_min_similarity,
                max_context_chars=settings.rag_max_context_chars,
                telemetry_sink=telemetry_sink,
            )
            selected_cases = [
                case.model_copy(
                    update={
                        "tenant_id": execution_context.tenant_id,
                        "agent_id": execution_context.agent_id,
                    }
                )
                for case in dataset.records
            ]
            run = await EvaluationRunner(
                workflow,
                configuration,
                execution_context=execution_context,
            ).run(selected_cases, run_id=run_id)
            await persist_evaluation_result(session, run)
            await session.commit()
        except Exception:
            LOGGER.exception("Evaluation run %s failed", run_id)
            await session.rollback()
            try:
                await mark_evaluation_failed(session, run_id)
                await session.commit()
            except Exception:
                await session.rollback()
                LOGGER.exception(
                    "Could not persist failure state for evaluation run %s",
                    run_id,
                )


@router.get(
    "/datasets",
    response_model=list[EvaluationDatasetSummaryResponse],
    dependencies=[Depends(require_permission("evaluation:read"))],
)
async def get_datasets() -> list[EvaluationDatasetSummaryResponse]:
    return [
        EvaluationDatasetSummaryResponse(
            name=item.name,
            owner=item.owner,
            domain=item.domain,
            version=item.version,
            status=item.status,
            classification=item.classification,
            case_count=len(item.records),
        )
        for item in list_evaluation_datasets()
    ]


@router.get(
    "/datasets/{name}/{version}",
    response_model=EvaluationDataset,
    dependencies=[Depends(require_permission("evaluation:read"))],
)
async def get_dataset(name: str, version: str) -> EvaluationDataset:
    try:
        return get_evaluation_dataset(name, version)
    except EvaluationDatasetError as exc:
        raise _dataset_not_found() from exc


@router.post(
    "/runs",
    response_model=EvaluationRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_permission("evaluation:write"))],
)
async def start_evaluation_run(
    payload: EvaluationRunCreateRequest,
    background_tasks: BackgroundTasks,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    context: Annotated[AdminContext | None, Depends(require_admin_access)],
    runtime: Annotated[GenerationRuntime, Depends(get_core_ai_runtime)],
    telemetry_sink: Annotated[TelemetrySink, Depends(get_telemetry_sink)],
    rerank_provider=Depends(get_rerank_provider),
) -> EvaluationRunResponse:
    try:
        dataset = get_evaluation_dataset(
            payload.dataset_name,
            payload.dataset_version,
        )
    except EvaluationDatasetError as exc:
        raise _dataset_not_found() from exc

    row = (
        await session.execute(
            select(Agent, Tenant)
            .join(Tenant, Tenant.id == Agent.tenant_id)
            .where(
                Agent.id == payload.agent_id,
                Agent.tenant_id == payload.tenant_id,
                Agent.is_active.is_(True),
                Tenant.is_active.is_(True),
            )
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active evaluation agent not found",
        )
    agent, _tenant = row

    configuration = EvaluationRunConfiguration(
        dataset_name=dataset.name,
        dataset_version=dataset.version,
        agent_version=agent.updated_at.isoformat(),
        prompt_version=agent.prompt_version,
        knowledge_version=None,
        model_provider="deepseek",
        model_name=settings.deepseek_model,
    )
    execution_context = ChatExecutionContext(
        tenant_id=agent.tenant_id,
        agent_id=agent.id,
        system_prompt=agent.system_prompt,
        prompt_version=agent.prompt_version,
        knowledge_mode=agent.knowledge_mode,
        contact_message=agent.contact_message,
        model_provider="deepseek",
    )
    run_id = str(uuid4())
    record = await create_running_evaluation(
        session,
        run_id=run_id,
        admin_id=context.admin_id if context is not None else None,
        tenant_id=agent.tenant_id,
        agent_id=agent.id,
        configuration=configuration,
    )
    await session.commit()
    await session.refresh(record)

    bind = session.bind
    if bind is None:
        raise RuntimeError("Evaluation session is not bound to an engine")
    session_factory = async_sessionmaker(
        bind=bind,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    background_tasks.add_task(
        _execute_evaluation_run,
        session_factory=session_factory,
        run_id=run_id,
        dataset=dataset,
        configuration=configuration,
        execution_context=execution_context,
        runtime=runtime,
        rerank_provider=rerank_provider,
        telemetry_sink=telemetry_sink,
        settings=settings,
    )
    return _run_response(record)


@router.get(
    "/runs",
    response_model=list[EvaluationRunResponse],
    dependencies=[Depends(require_permission("evaluation:read"))],
)
async def get_runs(
    session: Annotated[AsyncSession, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
) -> list[EvaluationRunResponse]:
    return [
        _run_response(item)
        for item in await list_evaluation_runs(session, limit=limit)
    ]


@router.get(
    "/runs/{run_id}",
    response_model=EvaluationRunResponse,
    dependencies=[Depends(require_permission("evaluation:read"))],
)
async def get_run(
    run_id: str,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> EvaluationRunResponse:
    row = await session.get(EvaluationRunRecord, run_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluation run not found",
        )
    return _run_response(row)
