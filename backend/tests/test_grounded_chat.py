"""Evidence-first chat orchestration tests."""

from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.app.ai.chat_workflow import INSUFFICIENT_EVIDENCE_SENTINEL
from backend.app.ai.contracts import GenerationResult
from backend.app.auth.context import ChatExecutionContext
from backend.app.db.base import Base
from backend.app.db.models import Agent, Message, Tenant
from backend.app.domain.exceptions import RetrievalError
from backend.app.domain.models.chunk import Chunk
from backend.app.domain.ports.retrieval import (
    RetrievalQuery,
    RetrievedChunk,
)
from backend.app.services.chat import ChatService


class StubRetrieval:
    def __init__(
        self,
        results: list[RetrievedChunk] | None = None,
        error: Exception | None = None,
    ) -> None:
        self.results = results or []
        self.error = error
        self.queries: list[RetrievalQuery] = []

    async def retrieve(
        self,
        query: RetrievalQuery,
    ) -> list[RetrievedChunk]:
        self.queries.append(query)
        if self.error is not None:
            raise self.error
        return list(self.results)


def _retrieved_chunk(
    *,
    content: str = "Refunds are accepted within 14 days.",
    score: float = 0.91,
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk=Chunk(
            id="chunk-a",
            tenant_id="tenant-a",
            agent_id="agent-a",
            knowledge_base_id="kb-a",
            document_id="document-a",
            source_name="refund-policy.pdf",
            page_number=1,
            chunk_index=0,
            content=content,
            content_hash="hash-a",
        ),
        similarity_score=score,
    )


async def _database(database_path: Path):
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with sessions() as session:
        session.add_all(
            [
                Tenant(id="tenant-a", name="Tenant A"),
                Agent(
                    id="agent-a",
                    tenant_id="tenant-a",
                    name="Agent A",
                ),
            ]
        )
        await session.commit()
    return engine, sessions


def _runtime() -> AsyncMock:
    runtime = AsyncMock()
    runtime.generate.return_value = GenerationResult(
        content="Refunds are accepted within 14 days [S1].",
        model="test-model",
        finish_reason="stop",
        prompt_tokens=20,
        completion_tokens=8,
    )
    return runtime


def _context(
    *,
    knowledge_mode: str = "required",
    contact_message: str | None = None,
) -> ChatExecutionContext:
    return ChatExecutionContext(
        tenant_id="tenant-a",
        agent_id="agent-a",
        system_prompt="Be precise.",
        knowledge_mode=knowledge_mode,
        contact_message=contact_message,
    )


@pytest.mark.asyncio
async def test_required_mode_generates_with_bounded_verified_sources(
    tmp_path: Path,
) -> None:
    engine, sessions = await _database(tmp_path / "grounded.sqlite3")
    runtime = _runtime()
    retrieval = StubRetrieval([_retrieved_chunk()])
    try:
        async with sessions() as session:
            result = await ChatService(
                runtime,
                retrieval=retrieval,
                max_context_chars=1000,
            ).execute(
                session=session,
                context=_context(),
                message="What is the refund policy?",
                conversation_id=None,
            )

        assert result.answer_status == "grounded"
        assert len(result.sources) == 1
        assert result.sources[0].citation_id == "S1"
        assert result.sources[0].page_number == 2
        assert retrieval.queries[0].tenant_id == "tenant-a"
        assert retrieval.queries[0].agent_id == "agent-a"

        generation_request = runtime.generate.await_args.args[0]
        assert [item.role for item in generation_request.messages] == [
            "system",
            "system",
            "user",
        ]
        evidence_prompt = generation_request.messages[1].content
        assert "untrusted data" in evidence_prompt
        assert "[S1]" in evidence_prompt
        assert "Refunds are accepted within 14 days." in evidence_prompt

        async with sessions() as session:
            assistant = await session.scalar(
                select(Message).where(Message.role == "assistant")
            )
        assert assistant is not None
        assert assistant.metadata_json is not None
        assert assistant.metadata_json["answer_status"] == "grounded"
        assert assistant.metadata_json["sources"][0]["citation_id"] == "S1"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_required_mode_falls_back_without_calling_generation(
    tmp_path: Path,
) -> None:
    engine, sessions = await _database(tmp_path / "fallback.sqlite3")
    runtime = _runtime()
    retrieval = StubRetrieval([])
    try:
        async with sessions() as session:
            result = await ChatService(
                runtime,
                retrieval=retrieval,
            ).execute(
                session=session,
                context=_context(
                    contact_message=(
                        "لا أملك معلومة مؤكدة. تواصل مع الشركة على 012345678."
                    ),
                ),
                message="Give me an unsupported price.",
                conversation_id=None,
            )

        assert result.reply == (
            "لا أملك معلومة مؤكدة. تواصل مع الشركة على 012345678."
        )
        assert result.answer_status == "insufficient_knowledge"
        assert result.sources == ()
        assert result.model == "platform-fallback"
        runtime.generate.assert_not_awaited()

        async with sessions() as session:
            assistant = await session.scalar(
                select(Message).where(Message.role == "assistant")
            )
        assert assistant is not None
        assert assistant.metadata_json == {
            "answer_status": "insufficient_knowledge",
            "sources": [],
        }
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_required_mode_marks_retrieval_failure_as_temporary(
    tmp_path: Path,
) -> None:
    engine, sessions = await _database(tmp_path / "unavailable.sqlite3")
    runtime = _runtime()
    retrieval = StubRetrieval(error=RetrievalError("database failed"))
    try:
        async with sessions() as session:
            result = await ChatService(
                runtime,
                retrieval=retrieval,
            ).execute(
                session=session,
                context=_context(),
                message="Question",
                conversation_id=None,
            )

        assert result.answer_status == "temporarily_unavailable"
        assert "temporarily unavailable" in result.reply
        runtime.generate.assert_not_awaited()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_preferred_mode_can_generate_without_evidence(
    tmp_path: Path,
) -> None:
    engine, sessions = await _database(tmp_path / "preferred.sqlite3")
    runtime = _runtime()
    retrieval = StubRetrieval([])
    try:
        async with sessions() as session:
            result = await ChatService(
                runtime,
                retrieval=retrieval,
            ).execute(
                session=session,
                context=_context(knowledge_mode="preferred"),
                message="Hello",
                conversation_id=None,
            )

        assert result.answer_status == "generated"
        assert result.sources == ()
        runtime.generate.assert_awaited_once()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_disabled_mode_skips_retrieval(
    tmp_path: Path,
) -> None:
    engine, sessions = await _database(tmp_path / "disabled.sqlite3")
    runtime = _runtime()
    retrieval = StubRetrieval([_retrieved_chunk()])
    try:
        async with sessions() as session:
            result = await ChatService(
                runtime,
                retrieval=retrieval,
            ).execute(
                session=session,
                context=_context(knowledge_mode="disabled"),
                message="Hello",
                conversation_id=None,
            )

        assert result.answer_status == "generated"
        assert retrieval.queries == []
        runtime.generate.assert_awaited_once()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_repeated_fallback_uses_contact_message_without_workflow_state(
    tmp_path: Path,
) -> None:
    engine, sessions = await _database(tmp_path / "repeat-contact.sqlite3")
    runtime = _runtime()
    retrieval = StubRetrieval([])
    service = ChatService(runtime, retrieval=retrieval)
    context = _context(
        contact_message="للمساعدة تواصل عبر support@example.test."
    )
    try:
        async with sessions() as session:
            first = await service.execute(
                session=session,
                context=context,
                message="First unsupported question",
                conversation_id=None,
            )
        async with sessions() as session:
            second = await service.execute(
                session=session,
                context=context,
                message="Second unsupported question",
                conversation_id=first.conversation_id,
            )

        assert first.reply == "للمساعدة تواصل عبر support@example.test."
        assert second.reply == first.reply
        runtime.generate.assert_not_awaited()

        async with sessions() as session:
            assistant_messages = list(
                (
                    await session.scalars(
                        select(Message).where(Message.role == "assistant")
                    )
                ).all()
            )
        assert len(assistant_messages) == 2
        assert all(
            "handoff_id" not in (message.metadata_json or {})
            for message in assistant_messages
        )
    finally:
        await engine.dispose()

@pytest.mark.asyncio
async def test_required_mode_converts_insufficient_evidence_signal_to_fallback(
    tmp_path: Path,
) -> None:
    engine, sessions = await _database(
        tmp_path / "insufficient-signal.sqlite3"
    )
    runtime = _runtime()
    runtime.generate.return_value = GenerationResult(
        content=INSUFFICIENT_EVIDENCE_SENTINEL,
        model="test-model",
        finish_reason="stop",
        prompt_tokens=20,
        completion_tokens=1,
    )
    retrieval = StubRetrieval(
        [
            _retrieved_chunk(
                content=(
                    "This verified document discusses another service but "
                    "does not contain the answer requested by the user."
                ),
                score=0.72,
            )
        ]
    )
    try:
        async with sessions() as session:
            result = await ChatService(
                runtime,
                retrieval=retrieval,
            ).execute(
                session=session,
                context=_context(),
                message="Give me an unsupported code.",
                conversation_id=None,
            )

        assert result.answer_status == "insufficient_knowledge"
        assert result.sources == ()
        assert result.model == "platform-fallback"
        assert "enough verified information" in result.reply
        runtime.generate.assert_awaited_once()
    finally:
        await engine.dispose()

