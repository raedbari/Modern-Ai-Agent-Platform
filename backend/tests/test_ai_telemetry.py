"""Tests for Agent Runtime use of the shared Platform telemetry boundary."""

from unittest.mock import AsyncMock

import pytest

from backend.app.ai.chat_workflow import ChatWorkflow
from backend.app.ai.contracts import GenerationResult
from backend.app.ai.runtime import CoreAIRuntime
from backend.app.auth.context import ChatExecutionContext
from backend.app.telemetry import InMemoryTelemetrySink


def _context() -> ChatExecutionContext:
    return ChatExecutionContext(
        tenant_id="tenant-1",
        agent_id="agent-1",
        system_prompt=None,
        product_id="athkachatbots",
        request_id="request-1",
        conversation_id="conversation-1",
        prompt_version="v2",
        knowledge_version="knowledge-7",
        model_provider="deepseek",
    )


def _workflow(generation, sink) -> ChatWorkflow:
    runtime = CoreAIRuntime(
        generation_provider=generation,
        embedding_provider=AsyncMock(),
    )
    return ChatWorkflow(runtime, telemetry_sink=sink)


@pytest.mark.asyncio
async def test_workflow_emits_one_versioned_canonical_event() -> None:
    generation = AsyncMock()
    generation.generate.return_value = GenerationResult(
        content="Hello",
        model="deepseek-chat",
        prompt_tokens=5,
        completion_tokens=2,
    )
    sink = InMemoryTelemetrySink()

    await _workflow(generation, sink).execute(
        context=_context(),
        message="Hello",
    )

    assert len(sink.events) == 1
    event = sink.events[0]
    assert event.request_id == "request-1"
    assert event.tenant_id == "tenant-1"
    assert event.product_id == "athkachatbots"
    assert event.agent_id == "agent-1"
    assert event.conversation_id == "conversation-1"
    assert event.prompt_version == "v2"
    assert event.knowledge_version == "knowledge-7"
    assert event.provider == "deepseek"
    assert event.model == "deepseek-chat"
    assert event.retrieval_count == 0
    assert event.rerank_count is None
    assert event.source_count == 0
    assert event.answer_status == "generated"
    assert event.input_tokens == 5
    assert event.output_tokens == 2
    assert event.latency_ms >= 0
    assert event.error_type is None


class FailingSink:
    def emit(self, _event) -> None:
        raise RuntimeError("observability unavailable")


@pytest.mark.asyncio
async def test_shared_sink_failure_does_not_fail_workflow() -> None:
    generation = AsyncMock()
    generation.generate.return_value = GenerationResult(
        content="Hello",
        model="test-model",
    )

    result = await _workflow(generation, FailingSink()).execute(
        context=_context(),
        message="Hello",
    )

    assert result.reply == "Hello"


@pytest.mark.asyncio
async def test_workflow_emits_one_sanitized_failure_event() -> None:
    generation = AsyncMock()
    generation.generate.side_effect = RuntimeError("secret provider detail")
    sink = InMemoryTelemetrySink()

    with pytest.raises(RuntimeError):
        await _workflow(generation, sink).execute(
            context=_context(),
            message="private customer prompt",
        )

    assert len(sink.events) == 1
    event = sink.events[0]
    assert event.answer_status == "failed"
    assert event.error_type == "RuntimeError"
    serialized = event.model_dump_json()
    assert "secret provider detail" not in serialized
    assert "private customer prompt" not in serialized
