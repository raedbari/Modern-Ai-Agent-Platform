"""Authenticated, tenant-scoped chat endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import (
    get_core_ai_runtime,
    require_chat_context,
)
from backend.app.api.schemas.chat import (
    ChatRequest,
    ChatResponse,
    TokenUsage,
)
from backend.app.auth.context import ChatExecutionContext
from backend.app.db.base import get_db
from backend.app.services.chat import (
    ChatService,
    ConversationNotFoundError,
    EmptyGenerationError,
    GenerationRuntime,
)

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
) -> ChatResponse:
    """Generate and persist one authenticated chat turn."""

    try:
        result = await ChatService(runtime).execute(
            session=session,
            context=context,
            message=payload.message,
            conversation_id=payload.conversation_id,
        )
    except ConversationNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        ) from exc
    except EmptyGenerationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Generation provider returned no response",
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
    )