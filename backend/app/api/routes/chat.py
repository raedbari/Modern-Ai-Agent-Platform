"""Authenticated, tenant-scoped chat endpoint."""

from typing import Annotated

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import (
    get_core_ai_runtime,
    get_rerank_provider,
    get_telemetry_sink,
    require_chat_context,
)
from backend.app.api.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ChatSource,
    TokenUsage,
)
from backend.app.auth.context import ChatExecutionContext
from backend.app.core.config import Settings, get_settings
from backend.app.db.base import get_db
from backend.app.infrastructure.database.repositories import (
    SQLAlchemyChunkRepository,
    SQLAlchemyKnowledgeBaseRepository,
)
from backend.app.services.chat import (
    ChatService,
    ConversationNotFoundError,
    EmptyGenerationError,
    GenerationRuntime,
)
from backend.app.services.knowledge.retrieval_service import RetrievalService
from backend.app.telemetry import TelemetrySink

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponse, status_code=200)
async def chat(
    payload: ChatRequest,
    context: Annotated[
        ChatExecutionContext,
        Depends(require_chat_context),
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
    runtime: Annotated[
        GenerationRuntime,
        Depends(get_core_ai_runtime),
    ],
    settings: Annotated[Settings, Depends(get_settings)],
    response: Response,
    rerank_provider=Depends(get_rerank_provider),
    telemetry_sink: TelemetrySink = Depends(get_telemetry_sink),
    x_request_id: Annotated[str | None, Header()] = None,
) -> ChatResponse:
    """Generate and persist one authenticated chat turn."""

    request_id = _request_id(x_request_id)
    response.headers["X-Request-ID"] = request_id
    try:
        retrieval = RetrievalService(
            embedding_provider=runtime,
            chunk_repository=SQLAlchemyChunkRepository(
                session,
                embedding_dimension=settings.embedding_dimension,
            ),
            kb_repository=SQLAlchemyKnowledgeBaseRepository(session),
            rerank_provider=rerank_provider,
            retrieval_candidate_count=(
                settings.retrieval_candidate_count
            ),
        )
        result = await ChatService(
            runtime,
            retrieval=retrieval,
            retrieval_top_k=settings.retrieval_top_k,
            retrieval_min_similarity=settings.retrieval_min_similarity,
            max_context_chars=settings.rag_max_context_chars,
            telemetry_sink=telemetry_sink,
            provider="deepseek",
        ).execute(
            session=session,
            context=context,
            message=payload.message,
            conversation_id=payload.conversation_id,
            request_id=request_id,
        )
    except ConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
            headers={"X-Request-ID": request_id},
        ) from exc
    except EmptyGenerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Generation provider returned no response",
            headers={"X-Request-ID": request_id},
        ) from exc

    return ChatResponse(
        conversation_id=result.conversation_id,
        message_id=result.message_id,
        reply=result.reply,
        model=result.model,
        finish_reason=result.finish_reason,
        usage=TokenUsage(
            prompt=result.prompt_tokens,
            completion=result.completion_tokens,
        ),
        answer_status=result.answer_status,
        sources=[
            ChatSource(
                citation_id=source.citation_id,
                source_name=source.source_name,
                document_id=source.document_id,
                page_number=source.page_number,
                similarity_score=source.similarity_score,
            )
            for source in result.sources
        ],
    )


def _request_id(candidate: str | None) -> str:
    """Accept canonical UUID correlation IDs; replace unsafe input."""

    if candidate is not None:
        try:
            return str(UUID(candidate))
        except (ValueError, AttributeError):
            pass
    return str(uuid4())
