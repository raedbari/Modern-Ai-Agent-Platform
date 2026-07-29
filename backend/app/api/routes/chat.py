"""Chat API endpoints."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from backend.app.ai.providers.deepseek import DeepSeekGenerationProvider
from backend.app.ai.providers.ollama import OllamaEmbeddingProvider
from backend.app.ai.runtime import CoreAIRuntime
from backend.app.api.schemas import (
    ChatRequest,
    ChatResponse,
    ConversationMessagesResponse,
    ConversationResponse,
    MessageResponse,
)
from backend.app.auth.dependencies import AuthenticatedClient
from backend.app.core.config import get_settings
from backend.app.core.logging import log_request
from backend.app.core.rate_limit import limiter
from backend.app.db.base import get_db

from backend.app.services.chat import ChatService

router = APIRouter(prefix="/v1", tags=["chat"])
settings = get_settings()


def get_chat_service(db: Session = Depends(get_db)) -> ChatService:
    """Dependency to create ChatService with initialized runtime."""
    # Initialize providers
    generation_provider = DeepSeekGenerationProvider(settings)
    embedding_provider = OllamaEmbeddingProvider(settings)
    
    # Create runtime
    runtime = CoreAIRuntime(
        generation_provider=generation_provider,
        embedding_provider=embedding_provider,
    )
    
    return ChatService(db=db, runtime=runtime)


@router.post("/chat", response_model=ChatResponse)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def send_message(
    request: Request,
    chat_request: ChatRequest,
    tenant: AuthenticatedClient,
    chat_service: ChatService = Depends(get_chat_service),
    x_request_id: Annotated[str | None, Header()] = None,
) -> ChatResponse:
    """
    Send a message to an AI agent and receive a response.
    
    This endpoint:
    1. Validates API key and extracts tenant context
    2. Validates agent belongs to tenant
    3. Creates or continues conversation
    4. Passes request to LangGraph via Core AI Runtime
    5. Returns structured response
    
    Rate limited per API key.
    Supports idempotency via Idempotency-Key header.
    """
    # Generate or use provided request ID
    request_id = x_request_id or str(uuid.uuid4())
    
    # Log request (without message content)
    log_request(
        request_id=request_id,
        client_id=tenant.client_id,
        endpoint="/v1/chat",
        method="POST",
        agent_id=chat_request.agent_id,
        conversation_id=chat_request.conversation_id,
        has_idempotency_key=chat_request.idempotency_key is not None,
    )
    
    # Process message through service
    conversation, assistant_message = await chat_service.process_message(
        client_id=tenant.client_id,
        agent_id=chat_request.agent_id,
        message_content=chat_request.message,
        conversation_id=chat_request.conversation_id,
        user_identifier=chat_request.user_identifier,
        idempotency_key=chat_request.idempotency_key,
        temperature=chat_request.temperature,
        max_tokens=chat_request.max_tokens,
    )
    
    return ChatResponse(
        conversation_id=conversation.id,
        message=MessageResponse(
            id=assistant_message.id,
            role=assistant_message.role,
            content=assistant_message.content,
            created_at=assistant_message.created_at,
        ),
        request_id=request_id,
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationResponse)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def get_conversation(
    request: Request,
    conversation_id: str,
    tenant: AuthenticatedClient,
    chat_service: ChatService = Depends(get_chat_service),
    x_request_id: Annotated[str | None, Header()] = None,
) -> ConversationResponse:
    """
    Get conversation details by ID.
    
    Validates tenant ownership before returning data.
    """
    request_id = x_request_id or str(uuid.uuid4())
    
    log_request(
        request_id=request_id,
        client_id=tenant.client_id,
        endpoint=f"/v1/conversations/{conversation_id}",
        method="GET",
    )
    
    conversation = chat_service.get_conversation(
        client_id=tenant.client_id,
        conversation_id=conversation_id,
    )
    
    # Count messages
    message_count = len(conversation.messages)
    
    return ConversationResponse(
        id=conversation.id,
        client_id=conversation.client_id,
        agent_id=conversation.agent_id,
        user_identifier=conversation.user_identifier,
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
        message_count=message_count,
    )


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=ConversationMessagesResponse,
)
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def get_conversation_messages(
    request: Request,
    conversation_id: str,
    tenant: AuthenticatedClient,
    chat_service: ChatService = Depends(get_chat_service),
    x_request_id: Annotated[str | None, Header()] = None,
) -> ConversationMessagesResponse:
    """
    Get all messages in a conversation.
    
    Validates tenant ownership before returning data.
    """
    request_id = x_request_id or str(uuid.uuid4())
    
    log_request(
        request_id=request_id,
        client_id=tenant.client_id,
        endpoint=f"/v1/conversations/{conversation_id}/messages",
        method="GET",
    )
    
    messages = chat_service.get_conversation_messages(
        client_id=tenant.client_id,
        conversation_id=conversation_id,
    )
    
    return ConversationMessagesResponse(
        conversation_id=conversation_id,
        messages=[
            MessageResponse(
                id=msg.id,
                role=msg.role,
                content=msg.content,
                created_at=msg.created_at,
            )
            for msg in messages
        ],
        total=len(messages),
    )
