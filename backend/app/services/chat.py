"""Tenant-scoped, evidence-first chat orchestration and persistence."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.ai.chat_workflow import (
    AnswerStatus,
    ChatSource,
    ChatWorkflow,
    EmptyGenerationError,
    GenerationRuntime,
)
from backend.app.ai.contracts import (
    ChatMessage,
)
from backend.app.auth.context import ChatExecutionContext
from backend.app.db.models import Conversation, Message
from backend.app.domain.ports.retrieval import RetrievalPort
from backend.app.telemetry import StructuredLoggingTelemetrySink, TelemetrySink


class ConversationNotFoundError(Exception):
    """Raised without revealing whether another tenant owns the identifier."""


@dataclass(frozen=True, slots=True)
class ChatResult:
    request_id: str
    conversation_id: str
    message_id: str
    reply: str
    model: str
    finish_reason: str | None
    prompt_tokens: int
    completion_tokens: int
    answer_status: AnswerStatus
    sources: tuple[ChatSource, ...]


class ChatService:
    """Retrieve evidence, generate or fall back, and persist one chat turn."""

    def __init__(
        self,
        runtime: GenerationRuntime,
        *,
        retrieval: RetrievalPort | None = None,
        retrieval_top_k: int = 5,
        retrieval_min_similarity: float = 0.5,
        max_context_chars: int = 12000,
        telemetry_sink: TelemetrySink | None = None,
        product_id: str = "athkachatbots",
        provider: str | None = None,
    ) -> None:
        self._workflow = ChatWorkflow(
            runtime,
            retrieval=retrieval,
            retrieval_top_k=retrieval_top_k,
            retrieval_min_similarity=retrieval_min_similarity,
            max_context_chars=max_context_chars,
            telemetry_sink=(
                telemetry_sink or StructuredLoggingTelemetrySink()
            ),
        )
        self._product_id = product_id
        self._provider = provider

    async def execute(
        self,
        session: AsyncSession,
        context: ChatExecutionContext,
        message: str,
        conversation_id: str | None,
        request_id: str | None = None,
    ) -> ChatResult:
        """Execute one atomic, tenant-scoped, evidence-first chat turn."""

        correlation_id = request_id or str(uuid4())
        try:
            conversation, history = await self._load_or_create_conversation(
                session=session,
                context=context,
                conversation_id=conversation_id,
            )
            workflow_context = replace(
                context,
                request_id=correlation_id,
                product_id=self._product_id,
                conversation_id=conversation.id,
                model_provider=self._provider,
            )
            workflow_result = await self._workflow.execute(
                context=workflow_context,
                message=message,
                history=tuple(
                    ChatMessage(
                        role=stored.role,
                        content=stored.content,
                    )
                    for stored in history
                    if (
                        stored.role in {"system", "user", "assistant"}
                        and stored.content.strip()
                    )
                ),
            )

            user_created_at = self._next_user_timestamp(history)
            user_message = Message(
                id=str(uuid4()),
                tenant_id=context.tenant_id,
                conversation_id=conversation.id,
                role="user",
                content=message,
            )
            user_message.created_at = user_created_at
            session.add(user_message)

            assistant_message = Message(
                id=str(uuid4()),
                tenant_id=context.tenant_id,
                conversation_id=conversation.id,
                role="assistant",
                content=workflow_result.reply,
                metadata_json={
                    "answer_status": workflow_result.answer_status,
                    "prompt_version": context.prompt_version,
                    "knowledge_version": context.knowledge_version,
                    "model": workflow_result.model,
                    "sources": [
                        source.as_metadata()
                        for source in workflow_result.sources
                    ],
                },
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
            request_id=correlation_id,
            conversation_id=conversation.id,
            message_id=assistant_message.id,
            reply=workflow_result.reply,
            model=workflow_result.model,
            finish_reason=workflow_result.finish_reason,
            prompt_tokens=workflow_result.prompt_tokens,
            completion_tokens=workflow_result.completion_tokens,
            answer_status=workflow_result.answer_status,
            sources=workflow_result.sources,
        )

    @staticmethod
    def _next_user_timestamp(history: list[Message]) -> datetime:
        user_created_at = datetime.now(timezone.utc)
        if not history:
            return user_created_at

        latest_history_at = max(
            stored.created_at
            if stored.created_at.tzinfo is not None
            else stored.created_at.replace(tzinfo=timezone.utc)
            for stored in history
        )
        return max(
            user_created_at,
            latest_history_at + timedelta(microseconds=1),
        )

    @staticmethod
    async def _load_or_create_conversation(
        session: AsyncSession,
        context: ChatExecutionContext,
        conversation_id: str | None,
    ) -> tuple[Conversation, list[Message]]:
        if conversation_id is None:
            metadata_json = None
            if context.auth_method == "widget":
                if context.session_id is None:
                    raise ConversationNotFoundError
                metadata_json = {
                    "auth_source": "widget",
                    "widget_session_id": context.session_id,
                    "public_widget_id": context.public_widget_id,
                }
            conversation = Conversation(
                id=str(uuid4()),
                tenant_id=context.tenant_id,
                agent_id=context.agent_id,
                metadata_json=metadata_json,
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

        if context.auth_method == "widget":
            metadata = conversation.metadata_json or {}
            if (
                context.session_id is None
                or metadata.get("auth_source") != "widget"
                or metadata.get("widget_session_id") != context.session_id
                or metadata.get("public_widget_id")
                != context.public_widget_id
            ):
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
