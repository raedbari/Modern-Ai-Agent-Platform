"""Tests for the reusable tenant-aware LangGraph chat workflow."""

from unittest.mock import AsyncMock

import pytest

from backend.app.ai.chat_workflow import (
    CHAT_WORKFLOW_GRAPH,
    ChatWorkflow,
)
from backend.app.ai.contracts import GenerationResult
from backend.app.auth.context import ChatExecutionContext
from backend.app.domain.models.chunk import Chunk
from backend.app.domain.ports.retrieval import (
    RetrievalQuery,
    RetrievedChunk,
)


class TenantAwareRetrieval:
    def __init__(self) -> None:
        self.queries: list[RetrievalQuery] = []

    async def retrieve(
        self,
        query: RetrievalQuery,
    ) -> list[RetrievedChunk]:
        self.queries.append(query)
        return [
            RetrievedChunk(
                chunk=Chunk(
                    id=f"chunk-{query.tenant_id}",
                    tenant_id=query.tenant_id,
                    agent_id=query.agent_id,
                    knowledge_base_id=f"kb-{query.tenant_id}",
                    document_id=f"doc-{query.tenant_id}",
                    source_name=f"{query.tenant_id}.txt",
                    page_number=0,
                    chunk_index=0,
                    content=f"Verified policy for {query.tenant_id}.",
                    content_hash=f"hash-{query.tenant_id}",
                ),
                similarity_score=0.9,
            )
        ]


def _context(
    tenant_id: str,
    agent_id: str,
    system_prompt: str,
) -> ChatExecutionContext:
    return ChatExecutionContext(
        tenant_id=tenant_id,
        agent_id=agent_id,
        system_prompt=system_prompt,
        knowledge_mode="required",
        contact_message=f"Contact {tenant_id}.",
    )


def test_chat_workflow_has_real_conditional_graph() -> None:
    graph = CHAT_WORKFLOW_GRAPH.get_graph()

    assert set(graph.nodes) == {
        "__start__",
        "retrieve",
        "prepare_prompt",
        "generate",
        "contact_fallback",
        "__end__",
    }
    assert {
        (edge.source, edge.target, edge.conditional)
        for edge in graph.edges
    } >= {
        ("__start__", "retrieve", False),
        ("retrieve", "prepare_prompt", False),
        ("prepare_prompt", "generate", True),
        ("prepare_prompt", "contact_fallback", True),
        ("generate", "__end__", False),
        ("contact_fallback", "__end__", False),
    }


@pytest.mark.asyncio
async def test_one_compiled_graph_keeps_tenant_runtime_context_isolated() -> None:
    generation = AsyncMock()
    generation.generate.side_effect = [
        GenerationResult(content="A [S1]", model="test-model"),
        GenerationResult(content="B [S1]", model="test-model"),
    ]
    retrieval = TenantAwareRetrieval()
    workflow = ChatWorkflow(generation, retrieval=retrieval)

    result_a = await workflow.execute(
        context=_context("tenant-a", "chatbot-a", "Instructions A"),
        message="Question A",
    )
    result_b = await workflow.execute(
        context=_context("tenant-b", "chatbot-b", "Instructions B"),
        message="Question B",
    )

    assert result_a.reply == "A [S1]"
    assert result_b.reply == "B [S1]"
    assert [
        (query.tenant_id, query.agent_id)
        for query in retrieval.queries
    ] == [
        ("tenant-a", "chatbot-a"),
        ("tenant-b", "chatbot-b"),
    ]

    request_a = generation.generate.await_args_list[0].args[0]
    request_b = generation.generate.await_args_list[1].args[0]
    assert request_a.context.tenant_id == "tenant-a"
    assert request_a.context.agent_id == "chatbot-a"
    assert request_a.messages[0].content == "Instructions A"
    assert "tenant-a.txt" in request_a.messages[1].content
    assert "tenant-b" not in request_a.messages[1].content
    assert request_b.context.tenant_id == "tenant-b"
    assert request_b.context.agent_id == "chatbot-b"
    assert request_b.messages[0].content == "Instructions B"
    assert "tenant-b.txt" in request_b.messages[1].content
    assert "tenant-a" not in request_b.messages[1].content


@pytest.mark.asyncio
@pytest.mark.parametrize("content", ["Unsupported", "Unsupported [S99]"])
async def test_grounded_generation_requires_valid_citations(content: str) -> None:
    generation = AsyncMock()
    generation.generate.return_value = GenerationResult(
        content=content,
        model="test-model",
        prompt_tokens=4,
        completion_tokens=2,
    )

    result = await ChatWorkflow(
        generation,
        retrieval=TenantAwareRetrieval(),
    ).execute(
        context=_context("tenant-a", "chatbot-a", "Instructions"),
        message="Question",
    )

    assert result.answer_status == "insufficient_knowledge"
    assert result.model == "platform-fallback"
    assert result.finish_reason == "invalid_citations"
    assert result.sources == ()
