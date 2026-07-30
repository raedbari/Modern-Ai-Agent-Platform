"""Tenant-scoped chat orchestration and persistence."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.ai.contracts import (
    ChatMessage,
    GenerationRequest,
    GenerationResult,
    RuntimeContext,
)
from backend.app.auth.context import ChatExecutionContext
from backend.app.db.models import Conversation, Message


class GenerationRuntime(Protocol):
    """The generation capability required by the chat service."""

    async def generate(
        self,
        request: GenerationRequest,
    ) -> GenerationResult:
        """Generate an assistant response."""
        ...


class ConversationNotFoundError(Exception):
    """Raised without revealing whether another tenant owns the identifier."""


class EmptyGenerationError(Exception):
    """Raised when a provider returns no usable assistant text."""


@dataclass(frozen=True, slots=True)
class ChatResult:
    conversation_id: str
    message_id: str
    reply: str
    model: str
    finish_reason: str | None
    prompt_tokens: int
    completion_tokens: int


class ChatService:
    """Load tenant history, call the runtime, and persist both messages."""

    def __init__(self, runtime: GenerationRuntime) -> None:
        self._runtime = runtime

    async def execute(
        self,
        session: AsyncSession,
        context: ChatExecutionContext,
        message: str,
        conversation_id: str | None,
    ) -> ChatResult:
        """Execute one atomic, tenant-scoped chat turn."""

        try:
            conversation, history = await self._load_or_create_conversation(
                session=session,
                context=context,
                conversation_id=conversation_id,
            )

            request_messages: list[ChatMessage] = []
            if context.system_prompt and context.system_prompt.strip():
                request_messages.append(
                    ChatMessage(
                        role="system",
                        content=context.system_prompt,
                    )
                )

            request_messages.extend(
                ChatMessage(role=stored.role, content=stored.content)
                for stored in history
                if (
                    stored.role in {"system", "user", "assistant"}
                    and stored.content.strip()
                )
            )
            request_messages.append(
                ChatMessage(role="user", content=message)
            )

            user_created_at = datetime.now(timezone.utc)
            if history:
                latest_history_at = max(
                    stored.created_at
                    if stored.created_at.tzinfo is not None
                    else stored.created_at.replace(tzinfo=timezone.utc)
                    for stored in history
                )
                user_created_at = max(
                    user_created_at,
                    latest_history_at + timedelta(microseconds=1),
                )

            user_message = Message(
                id=str(uuid4()),
                tenant_id=context.tenant_id,
                conversation_id=conversation.id,
                role="user",
                content=message,
                created_at=user_created_at,
            )
            session.add(user_message)

            generation = await self._runtime.generate(
                GenerationRequest(
                    context=RuntimeContext(
                        tenant_id=context.tenant_id,
                        agent_id=context.agent_id,
                    ),
                    messages=request_messages,
                )
            )
            assistant_content = generation.content.strip()
            if not assistant_content:
                raise EmptyGenerationError(
                    "Generation provider returned empty text"
                )

            assistant_message = Message(
                id=str(uuid4()),
                tenant_id=context.tenant_id,
                conversation_id=conversation.id,
                role="assistant",
                content=assistant_content,
                created_at=max(
                    datetime.now(timezone.utc),
                    user_created_at + timedelta(microseconds=1),
                ),
            )
            session.add(assistant_message)
            conversation.updated_at = assistant_message.created_at
            await session.commit()
        except Exception:
            await session.rollback()
            raise

        return ChatResult(
            conversation_id=conversation.id,
            message_id=assistant_message.id,
            reply=assistant_content,
            model=generation.model,
            finish_reason=generation.finish_reason,
            prompt_tokens=generation.prompt_tokens,
            completion_tokens=generation.completion_tokens,
        )

    @staticmethod
    async def _load_or_create_conversation(
        session: AsyncSession,
        context: ChatExecutionContext,
        conversation_id: str | None,
    ) -> tuple[Conversation, list[Message]]:
        if conversation_id is None:
            conversation = Conversation(
                id=str(uuid4()),
                tenant_id=context.tenant_id,
                agent_id=context.agent_id,
            )
            session.add(conversation)
            return conversation, []

        conversation = await session.scalar(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.tenant_id == context.tenant_id,
                Conversation.agent_id == context.agent_id,
            )
        )
        if conversation is None:
            raise ConversationNotFoundError

        history = list(
            (
                await session.scalars(
                    select(Message)
                    .where(
                        Message.tenant_id == context.tenant_id,
                        Message.conversation_id == conversation.id,
                    )
                    .order_by(Message.created_at, Message.id)
                )
            ).all()
        )
        return conversation, history