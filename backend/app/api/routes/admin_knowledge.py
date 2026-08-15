"""Administrator endpoints for tenant-scoped knowledge data."""

from __future__ import annotations

from collections import defaultdict
from uuid import uuid4
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import (
    get_embedding_provider,
    require_admin_access,
    require_permission,
)
from backend.app.api.schemas.admin_knowledge import (
    DocumentAdminResponse,
    DocumentJobAdminResponse,
    IngestionJobAdminResponse,
    KnowledgeBaseAdminCreate,
    KnowledgeBaseAdminResponse,
    KnowledgeBaseAdminUpdate,
    KnowledgeBaseAgentAssignmentsUpdate,
)
from backend.app.ai.ports import EmbeddingProvider
from backend.app.auth.admin_context import AdminContext
from backend.app.core.client_ip import get_client_ip
from backend.app.core.config import Settings, get_settings
from backend.app.db.base import get_db
from backend.app.db.models import (
    AgentKnowledgeBase,
    ChunkModel,
    DocumentModel,
    IngestionJob,
    KnowledgeBaseModel,
)
from backend.app.domain.exceptions import (
    DocumentNotFoundError,
    DomainError,
    KnowledgeBaseNotFoundError,
    UnsupportedDocumentTypeError,
)
from backend.app.infrastructure.storage import LocalUploadStorage
from backend.app.operations.admin_lifecycle import (
    AdminResourceNotFoundError,
    require_agent,
    require_tenant,
)
from backend.app.operations.ingestion_runtime import (
    build_ingestion_service,
)
from backend.app.services.audit import AuditService
from backend.app.services.knowledge.ingestion_service import (
    IngestionRequest,
)
from backend.app.services.knowledge.job_service import (
    IngestionJobService,
)


router = APIRouter(
    prefix="/api/admin/tenants/{tenant_id}/knowledge-bases",
    tags=["admin-knowledge"],
    dependencies=[Depends(require_admin_access)],
)


def _not_found(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=detail,
    )


def _unprocessable(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail=detail,
    )


def _conflict(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=detail,
    )


async def _read_admin_upload(
    file: UploadFile,
    size_limit: int,
) -> bytes:
    content = await file.read(size_limit + 1)
    if len(content) > size_limit:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="The uploaded document exceeds the size limit.",
        )
    return content


def _document_status_value(value: object) -> str:
    return str(getattr(value, "value", value))


def _raise_admin_ingestion_error(exc: DomainError) -> None:
    if isinstance(
        exc,
        (KnowledgeBaseNotFoundError, DocumentNotFoundError),
    ):
        raise _not_found(str(exc)) from exc
    if isinstance(exc, UnsupportedDocumentTypeError):
        raise _unprocessable(str(exc)) from exc
    raise _unprocessable(
        "Document processing could not be queued."
    ) from exc


async def _audit_mutation(
    session: AsyncSession,
    *,
    context: AdminContext | None,
    request: Request,
    settings: Settings,
    event_type: str,
    target_type: str,
    target_id: str,
    detail: dict | None = None,
) -> None:
    await AuditService.write(
        session,
        event_type=event_type,
        outcome="success",
        admin_id=context.admin_id if context is not None else None,
        target_type=target_type,
        target_id=target_id,
        client_ip=get_client_ip(request, settings),
        detail=detail,
    )


async def _validate_agent_ids(
    session: AsyncSession,
    *,
    tenant_id: str,
    agent_ids: list[str],
) -> None:
    for agent_id in agent_ids:
        try:
            await require_agent(
                session,
                tenant_id=tenant_id,
                agent_id=agent_id,
            )
        except AdminResourceNotFoundError as exc:
            raise _not_found(str(exc)) from exc


async def _require_knowledge_base(
    session: AsyncSession,
    *,
    tenant_id: str,
    knowledge_base_id: str,
) -> KnowledgeBaseModel:
    item = await session.scalar(
        select(KnowledgeBaseModel).where(
            KnowledgeBaseModel.tenant_id == tenant_id,
            KnowledgeBaseModel.id == knowledge_base_id,
        )
    )

    if item is None:
        raise _not_found(
            "Knowledge base not found."
        )

    return item


async def _require_assigned_agent(
    session: AsyncSession,
    *,
    tenant_id: str,
    knowledge_base_id: str,
    agent_id: str,
) -> None:
    try:
        await require_agent(
            session,
            tenant_id=tenant_id,
            agent_id=agent_id,
        )
    except AdminResourceNotFoundError as exc:
        raise _not_found(str(exc)) from exc

    assignment = await session.scalar(
        select(AgentKnowledgeBase).where(
            AgentKnowledgeBase.tenant_id == tenant_id,
            AgentKnowledgeBase.knowledge_base_id == knowledge_base_id,
            AgentKnowledgeBase.agent_id == agent_id,
        )
    )
    if assignment is None:
        raise _not_found(
            "Agent is not assigned to this knowledge base."
        )


async def _require_document(
    session: AsyncSession,
    *,
    tenant_id: str,
    knowledge_base_id: str,
    document_id: str,
) -> DocumentModel:
    document = await session.scalar(
        select(DocumentModel).where(
            DocumentModel.tenant_id == tenant_id,
            DocumentModel.knowledge_base_id == knowledge_base_id,
            DocumentModel.id == document_id,
        )
    )
    if document is None:
        raise _not_found("Document not found.")
    return document


def _document_job_response(
    *,
    document_id: str,
    document_status: object,
    job: IngestionJob | None = None,
    duplicate: bool = False,
) -> DocumentJobAdminResponse:
    return DocumentJobAdminResponse(
        document_id=document_id,
        document_status=_document_status_value(document_status),
        duplicate=duplicate,
        job=_job_response(job) if job is not None else None,
    )


def _job_response(
    job: IngestionJob,
) -> IngestionJobAdminResponse:
    return IngestionJobAdminResponse(
        id=job.id,
        tenant_id=job.tenant_id,
        agent_id=job.agent_id,
        knowledge_base_id=job.knowledge_base_id,
        document_id=job.document_id,
        status=job.status,
        attempts=job.attempts,
        max_attempts=job.max_attempts,
        available_at=job.available_at,
        last_error=job.last_error,
        created_at=job.created_at,
        updated_at=job.updated_at,
        completed_at=job.completed_at,
    )


async def _knowledge_base_responses(
    session: AsyncSession,
    *,
    tenant_id: str,
    knowledge_base_id: str | None = None,
    agent_id: str | None = None,
) -> list[KnowledgeBaseAdminResponse]:
    statement = (
        select(KnowledgeBaseModel)
        .where(
            KnowledgeBaseModel.tenant_id
            == tenant_id,
        )
        .order_by(
            KnowledgeBaseModel.created_at.desc(),
            KnowledgeBaseModel.id,
        )
    )

    if knowledge_base_id is not None:
        statement = statement.where(
            KnowledgeBaseModel.id
            == knowledge_base_id,
        )

    if agent_id is not None:
        statement = (
            statement.join(
                AgentKnowledgeBase,
                (
                    AgentKnowledgeBase.tenant_id
                    == KnowledgeBaseModel.tenant_id
                )
                & (
                    AgentKnowledgeBase.knowledge_base_id
                    == KnowledgeBaseModel.id
                ),
            )
            .where(
                AgentKnowledgeBase.agent_id
                == agent_id,
            )
            .distinct()
        )

    items = list(
        (
            await session.scalars(statement)
        ).all()
    )

    if not items:
        return []

    knowledge_base_ids = [
        item.id
        for item in items
    ]

    assignments: dict[str, list[str]] = (
        defaultdict(list)
    )

    assignment_rows = (
        await session.execute(
            select(
                AgentKnowledgeBase.knowledge_base_id,
                AgentKnowledgeBase.agent_id,
            )
            .where(
                AgentKnowledgeBase.tenant_id
                == tenant_id,
                AgentKnowledgeBase.knowledge_base_id.in_(
                    knowledge_base_ids
                ),
            )
            .order_by(
                AgentKnowledgeBase.knowledge_base_id,
                AgentKnowledgeBase.agent_id,
            )
        )
    ).all()

    for kb_id, assigned_agent_id in assignment_rows:
        assignments[kb_id].append(
            assigned_agent_id
        )

    document_counts: dict[
        str,
        dict[str, int],
    ] = defaultdict(
        lambda: defaultdict(int)
    )

    document_rows = (
        await session.execute(
            select(
                DocumentModel.knowledge_base_id,
                DocumentModel.status,
                func.count(DocumentModel.id),
            )
            .where(
                DocumentModel.tenant_id
                == tenant_id,
                DocumentModel.knowledge_base_id.in_(
                    knowledge_base_ids
                ),
            )
            .group_by(
                DocumentModel.knowledge_base_id,
                DocumentModel.status,
            )
        )
    ).all()

    for kb_id, document_status, count in document_rows:
        document_counts[kb_id][
            document_status
        ] = int(count)

    chunk_counts: dict[str, int] = {}

    chunk_rows = (
        await session.execute(
            select(
                ChunkModel.knowledge_base_id,
                func.count(ChunkModel.id),
            )
            .where(
                ChunkModel.tenant_id
                == tenant_id,
                ChunkModel.knowledge_base_id.in_(
                    knowledge_base_ids
                ),
            )
            .group_by(
                ChunkModel.knowledge_base_id,
            )
        )
    ).all()

    for kb_id, count in chunk_rows:
        chunk_counts[kb_id] = int(count)

    job_counts: dict[
        str,
        dict[str, int],
    ] = defaultdict(
        lambda: defaultdict(int)
    )

    job_rows = (
        await session.execute(
            select(
                IngestionJob.knowledge_base_id,
                IngestionJob.status,
                func.count(IngestionJob.id),
            )
            .where(
                IngestionJob.tenant_id
                == tenant_id,
                IngestionJob.knowledge_base_id.in_(
                    knowledge_base_ids
                ),
            )
            .group_by(
                IngestionJob.knowledge_base_id,
                IngestionJob.status,
            )
        )
    ).all()

    for kb_id, job_status, count in job_rows:
        job_counts[kb_id][job_status] = int(
            count
        )

    responses: list[
        KnowledgeBaseAdminResponse
    ] = []

    for item in items:
        current_documents = (
            document_counts[item.id]
        )

        responses.append(
            KnowledgeBaseAdminResponse(
                id=item.id,
                tenant_id=item.tenant_id,
                name=item.name,
                description=item.description,
                status=item.status,
                created_at=item.created_at,
                updated_at=item.updated_at,
                assigned_agent_ids=list(
                    assignments[item.id]
                ),
                document_count=sum(
                    current_documents.values()
                ),
                pending_document_count=(
                    current_documents["pending"]
                ),
                processing_document_count=(
                    current_documents["processing"]
                ),
                ready_document_count=(
                    current_documents["ready"]
                ),
                failed_document_count=(
                    current_documents["failed"]
                ),
                chunk_count=chunk_counts.get(
                    item.id,
                    0,
                ),
                pending_job_count=(
                    job_counts[item.id]["pending"]
                ),
                processing_job_count=(
                    job_counts[item.id]["processing"]
                ),
                failed_job_count=(
                    job_counts[item.id]["failed"]
                ),
            )
        )

    return responses


@router.get(
    "",
    response_model=list[
        KnowledgeBaseAdminResponse
    ],
    dependencies=[
        Depends(
            require_permission(
                "knowledge:read"
            )
        )
    ],
)
async def list_admin_knowledge_bases(
    tenant_id: str,
    session: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
    agent_id: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=128,
        ),
    ] = None,
) -> list[KnowledgeBaseAdminResponse]:
    try:
        await require_tenant(
            session,
            tenant_id,
        )

        if agent_id is not None:
            await require_agent(
                session,
                tenant_id=tenant_id,
                agent_id=agent_id,
            )
    except AdminResourceNotFoundError as exc:
        raise _not_found(str(exc)) from exc

    return await _knowledge_base_responses(
        session,
        tenant_id=tenant_id,
        agent_id=agent_id,
    )


@router.get(
    "/{knowledge_base_id}",
    response_model=KnowledgeBaseAdminResponse,
    dependencies=[
        Depends(
            require_permission(
                "knowledge:read"
            )
        )
    ],
)
async def read_admin_knowledge_base(
    tenant_id: str,
    knowledge_base_id: str,
    session: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
) -> KnowledgeBaseAdminResponse:
    try:
        await require_tenant(
            session,
            tenant_id,
        )
    except AdminResourceNotFoundError as exc:
        raise _not_found(str(exc)) from exc

    items = await _knowledge_base_responses(
        session,
        tenant_id=tenant_id,
        knowledge_base_id=knowledge_base_id,
    )

    if not items:
        raise _not_found(
            "Knowledge base not found."
        )

    return items[0]


@router.get(
    "/{knowledge_base_id}/documents",
    response_model=list[
        DocumentAdminResponse
    ],
    dependencies=[
        Depends(
            require_permission(
                "knowledge:read"
            )
        )
    ],
)
async def list_admin_documents(
    tenant_id: str,
    knowledge_base_id: str,
    session: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
) -> list[DocumentAdminResponse]:
    await _require_knowledge_base(
        session,
        tenant_id=tenant_id,
        knowledge_base_id=knowledge_base_id,
    )

    documents = list(
        (
            await session.scalars(
                select(DocumentModel)
                .where(
                    DocumentModel.tenant_id
                    == tenant_id,
                    DocumentModel.knowledge_base_id
                    == knowledge_base_id,
                )
                .order_by(
                    DocumentModel.created_at.desc(),
                    DocumentModel.id,
                )
            )
        ).all()
    )

    if not documents:
        return []

    document_ids = [
        document.id
        for document in documents
    ]

    chunk_counts: dict[str, int] = {}

    chunk_rows = (
        await session.execute(
            select(
                ChunkModel.document_id,
                func.count(ChunkModel.id),
            )
            .where(
                ChunkModel.tenant_id
                == tenant_id,
                ChunkModel.knowledge_base_id
                == knowledge_base_id,
                ChunkModel.document_id.in_(
                    document_ids
                ),
            )
            .group_by(
                ChunkModel.document_id,
            )
        )
    ).all()

    for document_id, count in chunk_rows:
        chunk_counts[document_id] = int(
            count
        )

    jobs = list(
        (
            await session.scalars(
                select(IngestionJob)
                .where(
                    IngestionJob.tenant_id
                    == tenant_id,
                    IngestionJob.knowledge_base_id
                    == knowledge_base_id,
                    IngestionJob.document_id.in_(
                        document_ids
                    ),
                )
                .order_by(
                    IngestionJob.created_at.desc(),
                    IngestionJob.id.desc(),
                )
            )
        ).all()
    )

    latest_jobs: dict[
        str,
        IngestionJob,
    ] = {}

    for job in jobs:
        latest_jobs.setdefault(
            job.document_id,
            job,
        )

    return [
        DocumentAdminResponse(
            id=document.id,
            tenant_id=document.tenant_id,
            knowledge_base_id=(
                document.knowledge_base_id
            ),
            agent_id=document.agent_id,
            original_filename=(
                document.original_filename
            ),
            source_name=document.source_name,
            mime_type=document.mime_type,
            file_size_bytes=(
                document.file_size_bytes
            ),
            status=document.status,
            failure_reason=(
                document.failure_reason
            ),
            created_at=document.created_at,
            updated_at=document.updated_at,
            chunk_count=chunk_counts.get(
                document.id,
                0,
            ),
            latest_job=(
                _job_response(
                    latest_jobs[document.id]
                )
                if document.id in latest_jobs
                else None
            ),
        )
        for document in documents
    ]


@router.get(
    "/{knowledge_base_id}/ingestion-jobs",
    response_model=list[
        IngestionJobAdminResponse
    ],
    dependencies=[
        Depends(
            require_permission(
                "knowledge:read"
            )
        )
    ],
)
async def list_admin_ingestion_jobs(
    tenant_id: str,
    knowledge_base_id: str,
    session: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=200,
        ),
    ] = 100,
) -> list[IngestionJobAdminResponse]:
    await _require_knowledge_base(
        session,
        tenant_id=tenant_id,
        knowledge_base_id=knowledge_base_id,
    )

    jobs = list(
        (
            await session.scalars(
                select(IngestionJob)
                .where(
                    IngestionJob.tenant_id
                    == tenant_id,
                    IngestionJob.knowledge_base_id
                    == knowledge_base_id,
                )
                .order_by(
                    IngestionJob.created_at.desc(),
                    IngestionJob.id.desc(),
                )
                .limit(limit)
            )
        ).all()
    )

    return [
        _job_response(job)
        for job in jobs
    ]


@router.post(
    "",
    response_model=KnowledgeBaseAdminResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("knowledge:write"))],
)
async def create_admin_knowledge_base(
    tenant_id: str,
    payload: KnowledgeBaseAdminCreate,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    context: Annotated[
        AdminContext | None,
        Depends(require_admin_access),
    ],
) -> KnowledgeBaseAdminResponse:
    try:
        await require_tenant(session, tenant_id)
        await _validate_agent_ids(
            session,
            tenant_id=tenant_id,
            agent_ids=payload.assigned_agent_ids,
        )

        knowledge_base = KnowledgeBaseModel(
            id=str(uuid4()),
            tenant_id=tenant_id,
            name=payload.name,
            description=payload.description,
            status=payload.status,
        )
        session.add(knowledge_base)
        await session.flush()

        for agent_id in payload.assigned_agent_ids:
            session.add(
                AgentKnowledgeBase(
                    tenant_id=tenant_id,
                    agent_id=agent_id,
                    knowledge_base_id=knowledge_base.id,
                )
            )

        await session.flush()
        await _audit_mutation(
            session,
            context=context,
            request=request,
            settings=settings,
            event_type="knowledge_base_created",
            target_type="knowledge_base",
            target_id=knowledge_base.id,
            detail={
                "tenant_id": tenant_id,
                "status": payload.status,
                "assigned_agent_ids": payload.assigned_agent_ids,
            },
        )
        await session.commit()

    except AdminResourceNotFoundError as exc:
        await session.rollback()
        raise _not_found(str(exc)) from exc

    items = await _knowledge_base_responses(
        session,
        tenant_id=tenant_id,
        knowledge_base_id=knowledge_base.id,
    )
    if not items:
        raise _not_found("Knowledge base not found.")
    return items[0]


@router.patch(
    "/{knowledge_base_id}",
    response_model=KnowledgeBaseAdminResponse,
    dependencies=[Depends(require_permission("knowledge:write"))],
)
async def update_admin_knowledge_base(
    tenant_id: str,
    knowledge_base_id: str,
    payload: KnowledgeBaseAdminUpdate,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    context: Annotated[
        AdminContext | None,
        Depends(require_admin_access),
    ],
) -> KnowledgeBaseAdminResponse:
    if not payload.has_changes():
        raise _unprocessable("At least one field is required.")

    knowledge_base = await _require_knowledge_base(
        session,
        tenant_id=tenant_id,
        knowledge_base_id=knowledge_base_id,
    )

    changed_fields = sorted(payload.model_fields_set)

    if payload.name is not None:
        knowledge_base.name = payload.name
    if payload.description is not None:
        knowledge_base.description = payload.description
    if payload.status is not None:
        knowledge_base.status = payload.status

    await session.flush()
    await _audit_mutation(
        session,
        context=context,
        request=request,
        settings=settings,
        event_type="knowledge_base_updated",
        target_type="knowledge_base",
        target_id=knowledge_base_id,
        detail={
            "tenant_id": tenant_id,
            "changed_fields": changed_fields,
        },
    )
    await session.commit()

    items = await _knowledge_base_responses(
        session,
        tenant_id=tenant_id,
        knowledge_base_id=knowledge_base_id,
    )
    if not items:
        raise _not_found("Knowledge base not found.")
    return items[0]


@router.put(
    "/{knowledge_base_id}/agents",
    response_model=KnowledgeBaseAdminResponse,
    dependencies=[Depends(require_permission("knowledge:write"))],
)
async def replace_admin_knowledge_base_agents(
    tenant_id: str,
    knowledge_base_id: str,
    payload: KnowledgeBaseAgentAssignmentsUpdate,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    context: Annotated[
        AdminContext | None,
        Depends(require_admin_access),
    ],
) -> KnowledgeBaseAdminResponse:
    await _require_knowledge_base(
        session,
        tenant_id=tenant_id,
        knowledge_base_id=knowledge_base_id,
    )
    await _validate_agent_ids(
        session,
        tenant_id=tenant_id,
        agent_ids=payload.agent_ids,
    )

    await session.execute(
        delete(AgentKnowledgeBase).where(
            AgentKnowledgeBase.tenant_id == tenant_id,
            AgentKnowledgeBase.knowledge_base_id == knowledge_base_id,
        )
    )

    for agent_id in payload.agent_ids:
        session.add(
            AgentKnowledgeBase(
                tenant_id=tenant_id,
                agent_id=agent_id,
                knowledge_base_id=knowledge_base_id,
            )
        )

    await session.flush()
    await _audit_mutation(
        session,
        context=context,
        request=request,
        settings=settings,
        event_type="knowledge_base_agents_changed",
        target_type="knowledge_base",
        target_id=knowledge_base_id,
        detail={
            "tenant_id": tenant_id,
            "assigned_agent_ids": payload.agent_ids,
        },
    )
    await session.commit()

    items = await _knowledge_base_responses(
        session,
        tenant_id=tenant_id,
        knowledge_base_id=knowledge_base_id,
    )
    if not items:
        raise _not_found("Knowledge base not found.")
    return items[0]

@router.post(
    "/{knowledge_base_id}/documents",
    response_model=DocumentJobAdminResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_permission("knowledge:write"))],
)
async def queue_admin_document(
    tenant_id: str,
    knowledge_base_id: str,
    file: Annotated[UploadFile, File()],
    http_request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    runtime: Annotated[
        EmbeddingProvider,
        Depends(get_embedding_provider),
    ],
    settings: Annotated[Settings, Depends(get_settings)],
    context: Annotated[
        AdminContext | None,
        Depends(require_admin_access),
    ],
    agent_id: Annotated[
        str,
        Form(min_length=1, max_length=128),
    ],
    source_name: Annotated[
        str,
        Form(min_length=1, max_length=512),
    ] = "admin-upload",
) -> DocumentJobAdminResponse:
    """Retain and queue one new administrative document upload."""

    await _require_knowledge_base(
        session,
        tenant_id=tenant_id,
        knowledge_base_id=knowledge_base_id,
    )
    await _require_assigned_agent(
        session,
        tenant_id=tenant_id,
        knowledge_base_id=knowledge_base_id,
        agent_id=agent_id,
    )

    content = await _read_admin_upload(
        file,
        settings.max_upload_size_bytes,
    )
    ingestion_request = IngestionRequest(
        content=content,
        filename=file.filename or "upload",
        mime_type=file.content_type or "application/octet-stream",
        tenant_id=tenant_id,
        agent_id=agent_id,
        knowledge_base_id=knowledge_base_id,
        source_name=source_name,
    )
    service = build_ingestion_service(
        session=session,
        runtime=runtime,
        settings=settings,
    )
    storage = LocalUploadStorage(settings.upload_storage_root)
    storage_key: str | None = None
    job_id = str(uuid4())

    try:
        prepared = await service.prepare(ingestion_request)
        if prepared.duplicate:
            await session.rollback()
            return _document_job_response(
                document_id=prepared.document.id,
                document_status=prepared.document.status,
                duplicate=True,
            )

        await session.flush()
        storage_key = await storage.store(
            tenant_id=tenant_id,
            document_id=job_id,
            content=content,
        )
        job = await IngestionJobService.enqueue(
            session,
            tenant_id=tenant_id,
            agent_id=agent_id,
            knowledge_base_id=knowledge_base_id,
            document_id=prepared.document.id,
            storage_key=storage_key,
            max_attempts=settings.ingestion_job_max_attempts,
            source_filename=ingestion_request.filename,
            source_mime_type=ingestion_request.mime_type,
            source_name=ingestion_request.source_name,
            job_id=job_id,
        )
        await _audit_mutation(
            session,
            context=context,
            request=http_request,
            settings=settings,
            event_type="knowledge_document_upload_queued",
            target_type="knowledge_document",
            target_id=prepared.document.id,
            detail={
                "tenant_id": tenant_id,
                "agent_id": agent_id,
                "knowledge_base_id": knowledge_base_id,
                "job_id": job.id,
            },
        )
        await session.commit()
        return _document_job_response(
            document_id=prepared.document.id,
            document_status=prepared.document.status,
            job=job,
        )
    except DomainError as exc:
        await session.rollback()
        if storage_key is not None:
            await storage.delete(storage_key)
        _raise_admin_ingestion_error(exc)
    except IntegrityError as exc:
        await session.rollback()
        if storage_key is not None:
            await storage.delete(storage_key)
        raise _conflict(
            "An active ingestion job already exists."
        ) from exc
    except Exception:
        await session.rollback()
        if storage_key is not None:
            await storage.delete(storage_key)
        raise


@router.post(
    "/{knowledge_base_id}/documents/{document_id}/replace",
    response_model=DocumentJobAdminResponse,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_permission("knowledge:write"))],
)
async def queue_admin_document_replacement(
    tenant_id: str,
    knowledge_base_id: str,
    document_id: str,
    file: Annotated[UploadFile, File()],
    http_request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    runtime: Annotated[
        EmbeddingProvider,
        Depends(get_embedding_provider),
    ],
    settings: Annotated[Settings, Depends(get_settings)],
    context: Annotated[
        AdminContext | None,
        Depends(require_admin_access),
    ],
    source_name: Annotated[
        str,
        Form(min_length=1, max_length=512),
    ] = "admin-replacement",
) -> DocumentJobAdminResponse:
    """Queue a replacement while preserving the active document."""

    await _require_knowledge_base(
        session,
        tenant_id=tenant_id,
        knowledge_base_id=knowledge_base_id,
    )
    document = await _require_document(
        session,
        tenant_id=tenant_id,
        knowledge_base_id=knowledge_base_id,
        document_id=document_id,
    )
    if document.agent_id is None:
        raise _conflict("Document is not assigned to an agent.")

    await _require_assigned_agent(
        session,
        tenant_id=tenant_id,
        knowledge_base_id=knowledge_base_id,
        agent_id=document.agent_id,
    )
    active_job = await IngestionJobService.get_active_for_document(
        session,
        tenant_id=tenant_id,
        document_id=document_id,
    )
    if active_job is not None:
        raise _conflict(
            "An active ingestion job already exists."
        )

    content = await _read_admin_upload(
        file,
        settings.max_upload_size_bytes,
    )
    ingestion_request = IngestionRequest(
        content=content,
        filename=file.filename or "upload",
        mime_type=file.content_type or "application/octet-stream",
        tenant_id=tenant_id,
        agent_id=document.agent_id,
        knowledge_base_id=knowledge_base_id,
        source_name=source_name,
    )
    service = build_ingestion_service(
        session=session,
        runtime=runtime,
        settings=settings,
    )
    storage = LocalUploadStorage(settings.upload_storage_root)
    storage_key: str | None = None
    job_id = str(uuid4())

    try:
        validated = await service.validate_reindex_target(
            document_id=document_id,
            request=ingestion_request,
        )
        preserved_status = validated.status
        await session.rollback()

        storage_key = await storage.store(
            tenant_id=tenant_id,
            document_id=job_id,
            content=content,
        )
        job = await IngestionJobService.enqueue(
            session,
            tenant_id=tenant_id,
            agent_id=ingestion_request.agent_id,
            knowledge_base_id=knowledge_base_id,
            document_id=document_id,
            storage_key=storage_key,
            max_attempts=settings.ingestion_job_max_attempts,
            source_filename=ingestion_request.filename,
            source_mime_type=ingestion_request.mime_type,
            source_name=ingestion_request.source_name,
            job_id=job_id,
        )
        await _audit_mutation(
            session,
            context=context,
            request=http_request,
            settings=settings,
            event_type="knowledge_document_replacement_queued",
            target_type="knowledge_document",
            target_id=document_id,
            detail={
                "tenant_id": tenant_id,
                "agent_id": ingestion_request.agent_id,
                "knowledge_base_id": knowledge_base_id,
                "job_id": job.id,
            },
        )
        await session.commit()
        return _document_job_response(
            document_id=document_id,
            document_status=preserved_status,
            job=job,
        )
    except DomainError as exc:
        await session.rollback()
        if storage_key is not None:
            await storage.delete(storage_key)
        _raise_admin_ingestion_error(exc)
    except IntegrityError as exc:
        await session.rollback()
        if storage_key is not None:
            await storage.delete(storage_key)
        raise _conflict(
            "An active ingestion job already exists."
        ) from exc
    except Exception:
        await session.rollback()
        if storage_key is not None:
            await storage.delete(storage_key)
        raise
