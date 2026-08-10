"""Authenticated, tenant- and agent-scoped Knowledge API."""

from __future__ import annotations

import logging
from typing import Annotated, NoReturn
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import (
    get_embedding_provider,
    require_knowledge_context,
)
from backend.app.api.schemas.knowledge import (
    DocumentIngestionResponse,
    DocumentJobResponse,
    DocumentResponse,
    KnowledgeBaseCreate,
    KnowledgeBaseResponse,
    KnowledgeBaseUpdate,
)
from backend.app.ai.ports import EmbeddingProvider
from backend.app.auth.context import ChatExecutionContext
from backend.app.core.config import Settings, get_settings
from backend.app.db.base import get_db
from backend.app.db.models import IngestionJob
from backend.app.domain.exceptions import (
    ChunkingError,
    DocumentNotFoundError,
    DomainError,
    EmbeddingError,
    KnowledgeBaseNotFoundError,
    ParseError,
    UnsupportedDocumentTypeError,
)
from backend.app.domain.models.document import Document
from backend.app.domain.models.enums import DocumentProcessingStatus
from backend.app.domain.models.knowledge_base import KnowledgeBase
from backend.app.infrastructure.database.repositories import (
    SQLAlchemyDocumentRepository,
    SQLAlchemyKnowledgeBaseRepository,
)
from backend.app.infrastructure.storage import LocalUploadStorage
from backend.app.operations.ingestion_runtime import build_ingestion_service
from backend.app.services.knowledge.ingestion_service import (
    IngestionRequest,
    IngestionResult,
)
from backend.app.services.audit import AuditService
from backend.app.services.knowledge.job_service import IngestionJobService

router = APIRouter(prefix="/api/knowledge-bases", tags=["knowledge"])
LOGGER = logging.getLogger(__name__)


def _knowledge_response(item: KnowledgeBase) -> KnowledgeBaseResponse:
    return KnowledgeBaseResponse(
        id=item.id,
        name=item.name,
        description=item.description,
        status=item.status,
    )


def _document_response(item: Document) -> DocumentResponse:
    return DocumentResponse(
        id=item.id,
        knowledge_base_id=item.knowledge_base_id,
        original_filename=item.original_filename,
        source_name=item.source_name,
        mime_type=item.mime_type,
        file_size_bytes=item.file_size_bytes,
        status=item.status,
        failure_reason=item.failure_reason,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


async def _require_assigned_knowledge_base(
    repository: SQLAlchemyKnowledgeBaseRepository,
    context: ChatExecutionContext,
    knowledge_base_id: str,
) -> KnowledgeBase:
    item = await repository.get_by_id(
        knowledge_base_id=knowledge_base_id,
        tenant_id=context.tenant_id,
    )
    assigned = await repository.is_assigned_to_agent(
        knowledge_base_id=knowledge_base_id,
        tenant_id=context.tenant_id,
        agent_id=context.agent_id,
    )
    if item is None or not assigned:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        )
    return item


async def _read_upload(file: UploadFile, size_limit: int) -> bytes:
    content = await file.read(size_limit + 1)
    if len(content) > size_limit:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="The uploaded document exceeds the size limit",
        )
    return content


def _ingestion_response(result: IngestionResult) -> DocumentIngestionResponse:
    document = _document_response(result.document)
    return DocumentIngestionResponse(
        **document.model_dump(),
        chunks_persisted=result.chunks_persisted,
        duplicate=result.duplicate,
    )


def _job_response(
    *,
    document: Document,
    job=None,
    duplicate: bool = False,
) -> DocumentJobResponse:
    if job is None:
        return DocumentJobResponse(
            job_id=None,
            document=_document_response(document),
            status="duplicate",
            attempts=0,
            max_attempts=0,
            last_error=None,
            duplicate=True,
            created_at=None,
            updated_at=None,
            completed_at=None,
        )
    return DocumentJobResponse(
        job_id=job.id,
        document=_document_response(document),
        status=job.status,
        attempts=job.attempts,
        max_attempts=job.max_attempts,
        last_error=job.last_error,
        duplicate=duplicate,
        created_at=job.created_at,
        updated_at=job.updated_at,
        completed_at=job.completed_at,
    )


async def _delete_stored_uploads(
    storage: LocalUploadStorage,
    storage_keys: list[str],
) -> None:
    """Best-effort cleanup after the database transaction is committed."""

    for storage_key in storage_keys:
        try:
            await storage.delete(storage_key)
        except Exception:
            LOGGER.exception(
                "Could not delete retained upload object %s",
                storage_key,
            )


def _raise_ingestion_http_error(
    exc: DomainError,
) -> NoReturn:
    """Map domain-safe ingestion failures to public API errors."""

    if isinstance(exc, KnowledgeBaseNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found",
        ) from exc

    if isinstance(exc, DocumentNotFoundError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        ) from exc

    if isinstance(exc, EmbeddingError):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                "Embedding provider could not process "
                "the document"
            ),
        ) from exc

    if isinstance(
        exc,
        (
            UnsupportedDocumentTypeError,
            ParseError,
            ChunkingError,
        ),
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail="Document processing failed",
    ) from exc


async def _commit_failed_ingestion(
    session: AsyncSession,
    exc: DomainError,
) -> NoReturn:
    """Commit a failed state already written by legacy ingestion flows."""

    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    _raise_ingestion_http_error(exc)


async def _record_processing_failure(
    *,
    session: AsyncSession,
    context: ChatExecutionContext,
    knowledge_base_id: str,
    document_id: str,
    mark_document_failed: bool,
) -> None:
    """Persist a safe failure state and audit in one short transaction."""

    await session.rollback()

    if mark_document_failed:
        await SQLAlchemyDocumentRepository(
            session
        ).update_processing_status(
            document_id=document_id,
            tenant_id=context.tenant_id,
            status=DocumentProcessingStatus.FAILED,
            failure_reason="Document processing failed.",
        )

    await AuditService.write(
        session,
        event_type="knowledge_document_processing_failed",
        outcome="failure",
        admin_id=None,
        target_type="knowledge_document",
        target_id=document_id,
        detail={
            "tenant_id": context.tenant_id,
            "agent_id": context.agent_id,
            "knowledge_base_id": knowledge_base_id,
        },
    )

    await session.commit()


@router.post(
    "",
    response_model=KnowledgeBaseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_knowledge_base(
    payload: KnowledgeBaseCreate,
    context: Annotated[
        ChatExecutionContext,
        Depends(require_knowledge_context),
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> KnowledgeBaseResponse:
    repository = SQLAlchemyKnowledgeBaseRepository(session)
    item = await repository.create(
        KnowledgeBase(
            id=str(uuid4()),
            tenant_id=context.tenant_id,
            name=payload.name,
            description=payload.description,
        ),
        agent_id=context.agent_id,
    )
    await session.commit()
    return _knowledge_response(item)


@router.get("", response_model=list[KnowledgeBaseResponse])
async def list_knowledge_bases(
    context: Annotated[
        ChatExecutionContext,
        Depends(require_knowledge_context),
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[KnowledgeBaseResponse]:
    repository = SQLAlchemyKnowledgeBaseRepository(session)
    items = await repository.list_for_agent(
        agent_id=context.agent_id,
        tenant_id=context.tenant_id,
    )
    await session.commit()
    return [_knowledge_response(item) for item in items]


@router.get(
    "/{knowledge_base_id}",
    response_model=KnowledgeBaseResponse,
)
async def get_knowledge_base(
    knowledge_base_id: str,
    context: Annotated[
        ChatExecutionContext,
        Depends(require_knowledge_context),
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> KnowledgeBaseResponse:
    item = await _require_assigned_knowledge_base(
        SQLAlchemyKnowledgeBaseRepository(session),
        context,
        knowledge_base_id,
    )
    await session.commit()
    return _knowledge_response(item)


@router.patch(
    "/{knowledge_base_id}",
    response_model=KnowledgeBaseResponse,
)
async def update_knowledge_base(
    knowledge_base_id: str,
    payload: KnowledgeBaseUpdate,
    context: Annotated[
        ChatExecutionContext,
        Depends(require_knowledge_context),
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> KnowledgeBaseResponse:
    repository = SQLAlchemyKnowledgeBaseRepository(session)
    item = await _require_assigned_knowledge_base(
        repository,
        context,
        knowledge_base_id,
    )
    if not payload.has_changes():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="At least one field is required",
        )
    if payload.name is not None:
        item.name = payload.name
    if payload.description is not None:
        item.description = payload.description
    if payload.status is not None:
        item.status = payload.status
    item = await repository.update(item)
    await session.commit()
    return _knowledge_response(item)


@router.delete(
    "/{knowledge_base_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_knowledge_base(
    knowledge_base_id: str,
    context: Annotated[
        ChatExecutionContext,
        Depends(require_knowledge_context),
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    repository = SQLAlchemyKnowledgeBaseRepository(session)
    await _require_assigned_knowledge_base(
        repository,
        context,
        knowledge_base_id,
    )
    storage_keys = list(
        (
            await session.scalars(
                select(IngestionJob.storage_key).where(
                    IngestionJob.tenant_id == context.tenant_id,
                    IngestionJob.knowledge_base_id == knowledge_base_id,
                )
            )
        ).all()
    )
    await repository.delete_by_id(
        knowledge_base_id=knowledge_base_id,
        tenant_id=context.tenant_id,
    )
    await session.commit()
    await _delete_stored_uploads(
        LocalUploadStorage(settings.upload_storage_root),
        storage_keys,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{knowledge_base_id}/documents",
    response_model=list[DocumentResponse],
)
async def list_documents(
    knowledge_base_id: str,
    context: Annotated[
        ChatExecutionContext,
        Depends(require_knowledge_context),
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[DocumentResponse]:
    await _require_assigned_knowledge_base(
        SQLAlchemyKnowledgeBaseRepository(session),
        context,
        knowledge_base_id,
    )
    items = await SQLAlchemyDocumentRepository(
        session
    ).list_by_knowledge_base(
        knowledge_base_id=knowledge_base_id,
        tenant_id=context.tenant_id,
    )
    await session.commit()
    return [_document_response(item) for item in items]


@router.post(
    "/{knowledge_base_id}/documents",
    response_model=DocumentIngestionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    knowledge_base_id: str,
    file: Annotated[UploadFile, File()],
    context: Annotated[
        ChatExecutionContext,
        Depends(require_knowledge_context),
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
    runtime: Annotated[
        EmbeddingProvider,
        Depends(get_embedding_provider),
    ],
    settings: Annotated[Settings, Depends(get_settings)],
    source_name: Annotated[
        str,
        Form(min_length=1, max_length=512),
    ] = "upload",
) -> DocumentIngestionResponse:
    content = await _read_upload(
        file,
        settings.max_upload_size_bytes,
    )

    request = IngestionRequest(
        content=content,
        filename=file.filename or "upload",
        mime_type=(
            file.content_type
            or "application/octet-stream"
        ),
        tenant_id=context.tenant_id,
        agent_id=context.agent_id,
        knowledge_base_id=knowledge_base_id,
        source_name=source_name,
    )

    service = build_ingestion_service(
        session=session,
        runtime=runtime,
        settings=settings,
    )

    document_id: str | None = None

    try:
        # Persist only the pending document in the first short
        # transaction. Duplicate uploads retain their existing behavior.
        initial = await service.prepare(request)

        if initial.duplicate:
            await session.commit()
            return _ingestion_response(initial)

        document_id = initial.document.id
        await session.commit()

        # Parsing and embeddings execute with no active DB transaction.
        prepared = await service.prepare_reindex(
            document=initial.document,
            request=request,
        )

        # Final activation and audit commit atomically.
        result = await service.activate_prepared_reindex(
            document_id=document_id,
            request=request,
            prepared=prepared,
        )

        await AuditService.write(
            session,
            event_type="knowledge_document_activated",
            outcome="success",
            admin_id=None,
            target_type="knowledge_document",
            target_id=document_id,
            detail={
                "tenant_id": context.tenant_id,
                "agent_id": context.agent_id,
                "knowledge_base_id": knowledge_base_id,
                "chunks_persisted":
                    result.chunks_persisted,
            },
        )

        await session.commit()
        return _ingestion_response(result)

    except DomainError as exc:
        if document_id is not None:
            await _record_processing_failure(
                session=session,
                context=context,
                knowledge_base_id=knowledge_base_id,
                document_id=document_id,
                mark_document_failed=True,
            )
        else:
            await session.rollback()

        _raise_ingestion_http_error(exc)

    except Exception:
        await session.rollback()
        raise


@router.post(
    "/{knowledge_base_id}/document-jobs",
    response_model=DocumentJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def queue_document(
    knowledge_base_id: str,
    file: Annotated[UploadFile, File()],
    context: Annotated[
        ChatExecutionContext,
        Depends(require_knowledge_context),
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
    runtime: Annotated[
        EmbeddingProvider,
        Depends(get_embedding_provider),
    ],
    settings: Annotated[Settings, Depends(get_settings)],
    source_name: Annotated[
        str,
        Form(min_length=1, max_length=512),
    ] = "upload",
) -> DocumentJobResponse:
    """Retain a source upload and enqueue durable background ingestion."""

    content = await _read_upload(file, settings.max_upload_size_bytes)
    request = IngestionRequest(
        content=content,
        filename=file.filename or "upload",
        mime_type=file.content_type or "application/octet-stream",
        tenant_id=context.tenant_id,
        agent_id=context.agent_id,
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
    try:
        prepared = await service.prepare(request)
        if prepared.duplicate:
            await session.commit()
            return _job_response(
                document=prepared.document,
                duplicate=True,
            )

        # Persist the pending document before creating a job that references it.
        await session.flush()
        storage_key = await storage.store(
            tenant_id=context.tenant_id,
            document_id=prepared.document.id,
            content=content,
        )
        job = await IngestionJobService.enqueue(
            session,
            tenant_id=context.tenant_id,
            agent_id=context.agent_id,
            knowledge_base_id=knowledge_base_id,
            document_id=prepared.document.id,
            storage_key=storage_key,
            max_attempts=settings.ingestion_job_max_attempts,
            source_filename=request.filename,
            source_mime_type=request.mime_type,
            source_name=request.source_name,
        )
        await session.commit()
        return _job_response(document=prepared.document, job=job)
    except DomainError as exc:
        if storage_key is not None:
            await storage.delete(storage_key)
        await _commit_failed_ingestion(session, exc)
    except Exception:
        await session.rollback()
        if storage_key is not None:
            await storage.delete(storage_key)
        raise


@router.get(
    "/{knowledge_base_id}/document-jobs/{job_id}",
    response_model=DocumentJobResponse,
)
async def get_document_job(
    knowledge_base_id: str,
    job_id: str,
    context: Annotated[
        ChatExecutionContext,
        Depends(require_knowledge_context),
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentJobResponse:
    """Return one tenant- and agent-scoped ingestion job."""

    await _require_assigned_knowledge_base(
        SQLAlchemyKnowledgeBaseRepository(session),
        context,
        knowledge_base_id,
    )
    job = await IngestionJobService.get_scoped(
        session,
        job_id=job_id,
        tenant_id=context.tenant_id,
        agent_id=context.agent_id,
        knowledge_base_id=knowledge_base_id,
    )
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document job not found",
        )
    document = await SQLAlchemyDocumentRepository(session).get_by_id(
        document_id=job.document_id,
        tenant_id=context.tenant_id,
    )
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document job not found",
        )
    return _job_response(document=document, job=job)


@router.get(
    "/{knowledge_base_id}/documents/{document_id}",
    response_model=DocumentResponse,
)
async def get_document(
    knowledge_base_id: str,
    document_id: str,
    context: Annotated[
        ChatExecutionContext,
        Depends(require_knowledge_context),
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentResponse:
    await _require_assigned_knowledge_base(
        SQLAlchemyKnowledgeBaseRepository(session),
        context,
        knowledge_base_id,
    )
    item = await SQLAlchemyDocumentRepository(session).get_by_id(
        document_id=document_id,
        tenant_id=context.tenant_id,
    )
    if item is None or item.knowledge_base_id != knowledge_base_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    await session.commit()
    return _document_response(item)


@router.delete(
    "/{knowledge_base_id}/documents/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_document(
    knowledge_base_id: str,
    document_id: str,
    context: Annotated[
        ChatExecutionContext,
        Depends(require_knowledge_context),
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    await _require_assigned_knowledge_base(
        SQLAlchemyKnowledgeBaseRepository(session),
        context,
        knowledge_base_id,
    )

    document_repository = SQLAlchemyDocumentRepository(session)

    document = await document_repository.get_by_id(
        document_id=document_id,
        tenant_id=context.tenant_id,
    )

    if (
        document is None
        or document.knowledge_base_id != knowledge_base_id
        or document.agent_id != context.agent_id
    ):
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    storage_keys = list(
        (
            await session.scalars(
                select(IngestionJob.storage_key).where(
                    IngestionJob.tenant_id == context.tenant_id,
                    IngestionJob.agent_id == context.agent_id,
                    IngestionJob.knowledge_base_id
                    == knowledge_base_id,
                    IngestionJob.document_id == document_id,
                )
            )
        ).all()
    )

    deleted = await document_repository.delete_by_id(
        document_id=document_id,
        tenant_id=context.tenant_id,
        knowledge_base_id=knowledge_base_id,
    )

    if not deleted:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    await AuditService.write(
        session,
        event_type="knowledge_document_deleted",
        outcome="success",
        admin_id=None,
        target_type="knowledge_document",
        target_id=document_id,
        detail={
            "tenant_id": context.tenant_id,
            "agent_id": context.agent_id,
            "knowledge_base_id": knowledge_base_id,
        },
    )

    await session.commit()

    await _delete_stored_uploads(
        LocalUploadStorage(settings.upload_storage_root),
        storage_keys,
    )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{knowledge_base_id}/documents/{document_id}/reindex",
    response_model=DocumentIngestionResponse,
)
async def reindex_document(
    knowledge_base_id: str,
    document_id: str,
    file: Annotated[UploadFile, File()],
    context: Annotated[
        ChatExecutionContext,
        Depends(require_knowledge_context),
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
    runtime: Annotated[
        EmbeddingProvider,
        Depends(get_embedding_provider),
    ],
    settings: Annotated[Settings, Depends(get_settings)],
    source_name: Annotated[
        str,
        Form(min_length=1, max_length=512),
    ] = "upload",
) -> DocumentIngestionResponse:
    content = await _read_upload(
        file,
        settings.max_upload_size_bytes,
    )

    request = IngestionRequest(
        content=content,
        filename=file.filename or "upload",
        mime_type=(
            file.content_type
            or "application/octet-stream"
        ),
        tenant_id=context.tenant_id,
        agent_id=context.agent_id,
        knowledge_base_id=knowledge_base_id,
        source_name=source_name,
    )

    service = build_ingestion_service(
        session=session,
        runtime=runtime,
        settings=settings,
    )

    validated = False
    was_active = False

    try:
        document = await service.validate_reindex_target(
            document_id=document_id,
            request=request,
        )

        validated = True
        was_active = (
            document.status
            == DocumentProcessingStatus.READY
        )

        # End all validation reads before external processing.
        await session.rollback()

        prepared = await service.prepare_reindex(
            document=document,
            request=request,
        )

        result = await service.activate_prepared_reindex(
            document_id=document_id,
            request=request,
            prepared=prepared,
        )

        await AuditService.write(
            session,
            event_type=(
                "knowledge_document_replaced"
                if was_active
                else "knowledge_document_activated"
            ),
            outcome="success",
            admin_id=None,
            target_type="knowledge_document",
            target_id=document_id,
            detail={
                "tenant_id": context.tenant_id,
                "agent_id": context.agent_id,
                "knowledge_base_id": knowledge_base_id,
                "chunks_persisted":
                    result.chunks_persisted,
            },
        )

        await session.commit()
        return _ingestion_response(result)

    except DomainError as exc:
        if validated:
            await _record_processing_failure(
                session=session,
                context=context,
                knowledge_base_id=knowledge_base_id,
                document_id=document_id,
                # A failed replacement must preserve an old active
                # document. Non-active documents receive FAILED.
                mark_document_failed=not was_active,
            )
        else:
            await session.rollback()

        _raise_ingestion_http_error(exc)

    except Exception:
        await session.rollback()
        raise
