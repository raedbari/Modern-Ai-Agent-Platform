"""Authenticated, tenant- and agent-scoped Knowledge API."""

from __future__ import annotations

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
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import (
    get_core_ai_runtime,
    require_chat_context,
)
from backend.app.api.schemas.knowledge import (
    DocumentIngestionResponse,
    DocumentResponse,
    KnowledgeBaseCreate,
    KnowledgeBaseResponse,
    KnowledgeBaseUpdate,
)
from backend.app.ai.ports import EmbeddingProvider
from backend.app.auth.context import ChatExecutionContext
from backend.app.core.config import Settings, get_settings
from backend.app.db.base import get_db
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
from backend.app.domain.models.knowledge_base import KnowledgeBase
from backend.app.infrastructure.database.repositories import (
    SQLAlchemyChunkRepository,
    SQLAlchemyDocumentRepository,
    SQLAlchemyKnowledgeBaseRepository,
)
from backend.app.infrastructure.parsers.factory import DefaultParserFactory
from backend.app.services.knowledge.chunking_service import ChunkingService
from backend.app.services.knowledge.embedding_service import EmbeddingService
from backend.app.services.knowledge.ingestion_service import (
    IngestionRequest,
    IngestionResult,
    IngestionService,
)

router = APIRouter(prefix="/api/knowledge-bases", tags=["knowledge"])


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


def _build_ingestion_service(
    *,
    session: AsyncSession,
    runtime: EmbeddingProvider,
    settings: Settings,
) -> IngestionService:
    return IngestionService(
        parser_factory=DefaultParserFactory(),
        chunking_service=ChunkingService(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        ),
        embedding_service=EmbeddingService(
            provider=runtime,
            batch_size=settings.embedding_batch_size,
            embedding_dimensions=settings.embedding_dimension,
        ),
        document_repository=SQLAlchemyDocumentRepository(session),
        chunk_repository=SQLAlchemyChunkRepository(
            session,
            embedding_dimension=settings.embedding_dimension,
        ),
        knowledge_base_repository=SQLAlchemyKnowledgeBaseRepository(session),
        max_upload_size_bytes=settings.max_upload_size_bytes,
        max_pdf_pages=settings.max_pdf_pages,
        allowed_extensions=settings.allowed_extensions,
        allowed_mime_types=settings.allowed_mime_types,
    )


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


async def _commit_failed_ingestion(
    session: AsyncSession,
    exc: DomainError,
) -> NoReturn:
    """Persist a safe FAILED status written by the ingestion service."""

    try:
        await session.commit()
    except Exception:
        await session.rollback()
        raise

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
            detail="Embedding provider could not process the document",
        ) from exc
    if isinstance(
        exc,
        (UnsupportedDocumentTypeError, ParseError, ChunkingError),
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
    raise HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        detail="Document processing failed",
    ) from exc


@router.post(
    "",
    response_model=KnowledgeBaseResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_knowledge_base(
    payload: KnowledgeBaseCreate,
    context: Annotated[
        ChatExecutionContext,
        Depends(require_chat_context),
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
        Depends(require_chat_context),
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
        Depends(require_chat_context),
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
        Depends(require_chat_context),
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
        Depends(require_chat_context),
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    repository = SQLAlchemyKnowledgeBaseRepository(session)
    await _require_assigned_knowledge_base(
        repository,
        context,
        knowledge_base_id,
    )
    await repository.delete_by_id(
        knowledge_base_id=knowledge_base_id,
        tenant_id=context.tenant_id,
    )
    await session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/{knowledge_base_id}/documents",
    response_model=list[DocumentResponse],
)
async def list_documents(
    knowledge_base_id: str,
    context: Annotated[
        ChatExecutionContext,
        Depends(require_chat_context),
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
        Depends(require_chat_context),
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
    runtime: Annotated[
        EmbeddingProvider,
        Depends(get_core_ai_runtime),
    ],
    settings: Annotated[Settings, Depends(get_settings)],
    source_name: Annotated[
        str,
        Form(min_length=1, max_length=512),
    ] = "upload",
) -> DocumentIngestionResponse:
    content = await _read_upload(file, settings.max_upload_size_bytes)
    service = _build_ingestion_service(
        session=session,
        runtime=runtime,
        settings=settings,
    )
    try:
        result = await service.ingest(
            IngestionRequest(
                content=content,
                filename=file.filename or "upload",
                mime_type=file.content_type or "application/octet-stream",
                tenant_id=context.tenant_id,
                agent_id=context.agent_id,
                knowledge_base_id=knowledge_base_id,
                source_name=source_name,
            )
        )
        await session.commit()
    except DomainError as exc:
        await _commit_failed_ingestion(session, exc)
    return _ingestion_response(result)


@router.get(
    "/{knowledge_base_id}/documents/{document_id}",
    response_model=DocumentResponse,
)
async def get_document(
    knowledge_base_id: str,
    document_id: str,
    context: Annotated[
        ChatExecutionContext,
        Depends(require_chat_context),
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
        Depends(require_chat_context),
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    await _require_assigned_knowledge_base(
        SQLAlchemyKnowledgeBaseRepository(session),
        context,
        knowledge_base_id,
    )
    deleted = await SQLAlchemyDocumentRepository(session).delete_by_id(
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
    await session.commit()
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
        Depends(require_chat_context),
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
    runtime: Annotated[
        EmbeddingProvider,
        Depends(get_core_ai_runtime),
    ],
    settings: Annotated[Settings, Depends(get_settings)],
    source_name: Annotated[
        str,
        Form(min_length=1, max_length=512),
    ] = "upload",
) -> DocumentIngestionResponse:
    content = await _read_upload(file, settings.max_upload_size_bytes)
    service = _build_ingestion_service(
        session=session,
        runtime=runtime,
        settings=settings,
    )
    try:
        result = await service.reindex(
            document_id=document_id,
            request=IngestionRequest(
                content=content,
                filename=file.filename or "upload",
                mime_type=file.content_type or "application/octet-stream",
                tenant_id=context.tenant_id,
                agent_id=context.agent_id,
                knowledge_base_id=knowledge_base_id,
                source_name=source_name,
            ),
        )
        await session.commit()
    except DomainError as exc:
        await _commit_failed_ingestion(session, exc)
    return _ingestion_response(result)
