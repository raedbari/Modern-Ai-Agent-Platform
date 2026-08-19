"""Behavior tests for full-RAG evaluation through production orchestration."""

from __future__ import annotations

import pytest

from backend.app.ai.chat_workflow import ChatWorkflow
from backend.app.ai.contracts import GenerationResult
from backend.app.ai.runtime import CoreAIRuntime
from backend.app.auth.context import ChatExecutionContext
from backend.app.evaluation.loader import load_evaluation_dataset
from backend.app.evaluation.models import EvaluationRunConfiguration
from backend.app.evaluation.runner import EvaluationRunner
from backend.app.services.knowledge.retrieval_service import RetrievalService
from backend.tests.evaluation.deterministic_rag import (
    DeterministicEmbeddingProvider,
    DeterministicGenerationProvider,
    DeterministicRerankProvider,
    InMemoryTelemetrySink,
    TenantScopedFixtureRepositories,
    dataset_directory,
)


def _stack(generation_provider=None, execution_context=None):
    embedding = DeterministicEmbeddingProvider()
    generation = generation_provider or DeterministicGenerationProvider()
    rerank = DeterministicRerankProvider()
    repositories = TenantScopedFixtureRepositories()
    telemetry = InMemoryTelemetrySink()
    runtime = CoreAIRuntime(
        generation_provider=generation,
        embedding_provider=embedding,
    )
    retrieval = RetrievalService(
        embedding_provider=runtime,
        chunk_repository=repositories,
        kb_repository=repositories,
        rerank_provider=rerank,
        retrieval_candidate_count=20,
    )
    workflow = ChatWorkflow(
        runtime,
        retrieval=retrieval,
        retrieval_top_k=5,
        retrieval_min_similarity=0.1,
        telemetry_sink=telemetry,
    )
    configuration = EvaluationRunConfiguration(
        dataset_name="golden-questions",
        dataset_version="v1",
        agent_version="eval-agent-config-v1",
        prompt_version="prompt-v7",
        knowledge_version="fixture-context-v1",
        model_provider="deterministic",
        model_name="deterministic-generation-v1",
    )
    runner = EvaluationRunner(
        workflow,
        configuration,
        execution_context=execution_context,
    )
    dataset = load_evaluation_dataset(
        dataset_directory() / "golden_questions_v1.jsonl",
        dataset_directory() / "golden_questions_v1.json",
    )
    return runner, dataset, generation, embedding, rerank, repositories, telemetry


@pytest.mark.asyncio
async def test_all_twenty_cases_execute_through_real_rag_workflow() -> None:
    runner, dataset, generation, embedding, rerank, repositories, telemetry = _stack()

    run = await runner.run(dataset.records, run_id="run-controlled-v1")

    assert len(dataset.records) == 20
    assert len(run.results) == 20
    assert all(result.status == "passed" for result in run.results)
    assert run.status == "completed"
    assert run.run_id == "run-controlled-v1"
    assert run.configuration.dataset_version == "v1"
    assert run.configuration.prompt_version == "prompt-v7"
    assert run.configuration.knowledge_version == "fixture-context-v1"
    assert run.started_at <= run.completed_at
    assert run.summary.total_cases == 20
    assert run.summary.failure_rate_percent == 0
    assert run.summary.expected_source_rate_percent == 100
    assert run.summary.correct_refusal_rate_percent == 100
    assert run.summary.citation_accuracy_rate_percent == 100
    assert embedding.requests
    assert rerank.requests
    assert generation.requests
    assert repositories.search_calls
    assert len(telemetry.events) == 20


@pytest.mark.asyncio
async def test_metrics_are_computed_from_workflow_execution() -> None:
    runner, dataset, *_ = _stack()
    case = next(case for case in dataset.records if case.case_id == "gq-013-multi-source")

    result = await runner.run_case(case)

    metrics = result.rag_metrics
    assert metrics is not None
    assert metrics.retrieval_status == "measured"
    assert metrics.retrieval_hit is True
    assert metrics.retrieval_count >= 2
    assert metrics.rerank_status == "measured"
    assert metrics.rerank_count == 5
    assert metrics.expected_source_position is not None
    assert metrics.top_k_source_presence is True
    assert metrics.groundedness is True
    assert metrics.groundedness_status == "measured"
    assert metrics.has_citations is True
    assert metrics.citation_accuracy is True
    assert set(metrics.correctly_cited_expected_source_ids) == {
        "doc-a-shipping",
        "doc-a-tracking",
    }
    assert metrics.failure is False
    assert result.latency_ms >= 0


@pytest.mark.asyncio
async def test_unanswerable_case_computes_correct_refusal() -> None:
    runner, dataset, *_ = _stack()
    case = next(case for case in dataset.records if case.case_id == "gq-015-future-initiative")

    result = await runner.run_case(case)

    assert result.answer_status == "insufficient_knowledge"
    assert result.rag_metrics is not None
    assert result.rag_metrics.correct_refusal is True
    assert result.rag_metrics.groundedness_status == "not_measured"


@pytest.mark.asyncio
async def test_scope_is_preserved_and_cross_tenant_evidence_never_reaches_rerank() -> None:
    runner, dataset, _, embedding, rerank, repositories, _ = _stack()
    case = next(
        case for case in dataset.records
        if case.case_id == "gq-017-tenant-secret-negative"
    )

    result = await runner.run_case(case)

    assert result.tenant_id == "eval-tenant-a"
    assert result.agent_id == "eval-agent-a"
    assert repositories.scope_calls == [("eval-tenant-a", "eval-agent-a")]
    assert all(call["tenant_id"] == "eval-tenant-a" for call in repositories.search_calls)
    assert all(call["agent_id"] == "eval-agent-a" for call in repositories.search_calls)
    assert embedding.requests[0].context.tenant_id == "eval-tenant-a"
    assert embedding.requests[0].context.agent_id == "eval-agent-a"
    assert rerank.requests[0].query == case.user_input
    assert all("blue-orchid" not in document for document in rerank.requests[0].documents)
    assert result.rag_metrics is not None
    assert "doc-b-secret" not in result.rag_metrics.supplied_source_ids
    assert result.rag_metrics.correct_refusal is True


@pytest.mark.asyncio
async def test_prompt_provider_model_and_optional_knowledge_context_propagate() -> None:
    runner, dataset, generation, _, _, _, telemetry = _stack()
    case = dataset.records[0]

    result = await runner.run_case(case)

    request = generation.requests[0]
    assert request.context.prompt_version == "prompt-v7"
    assert request.context.knowledge_version == "fixture-context-v1"
    assert result.prompt_version == "prompt-v7"
    assert result.knowledge_version == "fixture-context-v1"
    assert result.model_provider == "deterministic"
    assert result.model == "deterministic-generation-v1"
    event = telemetry.events[0]
    assert event.prompt_version == "prompt-v7"
    assert event.knowledge_version == "fixture-context-v1"
    assert event.provider == "deterministic"
    assert event.model == "deterministic-generation-v1"
    assert event.retrieval_count is not None and event.retrieval_count > 0
    assert event.rerank_count == 5
    assert event.source_count == 5
    assert event.answer_status == "grounded"
    assert event.input_tokens == 17
    assert event.output_tokens == 9
    assert event.latency_ms is not None and event.latency_ms >= 0
    assert event.error_type is None


@pytest.mark.asyncio
async def test_selected_agent_execution_context_is_used_when_provided() -> None:
    selected_context = ChatExecutionContext(
        tenant_id="placeholder-tenant",
        agent_id="placeholder-agent",
        system_prompt="Selected production agent instructions.",
        prompt_version="ignored-by-runner-configuration",
        knowledge_mode="required",
    )
    runner, dataset, generation, *_ = _stack(
        execution_context=selected_context,
    )

    result = await runner.run_case(dataset.records[0])

    request = generation.requests[0]
    assert request.messages[0].content == "Selected production agent instructions."
    assert request.context.tenant_id == "eval-tenant-a"
    assert request.context.agent_id == "eval-agent-a"
    assert request.context.prompt_version == "prompt-v7"
    assert result.tenant_id == "eval-tenant-a"


class InvalidCitationGenerationProvider(DeterministicGenerationProvider):
    async def generate(self, request):
        self.requests.append(request)
        return GenerationResult(
            content="Refunds are accepted within 14 days with a receipt. [S99]",
            model="deterministic-generation-v1",
        )


@pytest.mark.asyncio
async def test_invalid_citation_is_distinct_from_supplied_and_cited_sources() -> None:
    provider = InvalidCitationGenerationProvider()
    runner, dataset, *_ = _stack(provider)

    result = await runner.run_case(dataset.records[0])

    metrics = result.rag_metrics
    assert metrics is not None
    assert "doc-a-refund" in metrics.supplied_source_ids
    assert metrics.cited_source_ids == []
    assert metrics.invalid_citation_ids == ["S99"]
    assert metrics.citation_accuracy is False
    assert result.status == "failed"


class FailingGenerationProvider(DeterministicGenerationProvider):
    async def generate(self, request):
        raise RuntimeError("deterministic provider failure")


@pytest.mark.asyncio
async def test_full_pipeline_failure_is_recorded_without_error_details() -> None:
    runner, dataset, _, _, _, _, telemetry = _stack(FailingGenerationProvider())

    result = await runner.run_case(dataset.records[0])

    assert result.status == "error"
    assert result.error_code == "pipeline_failed"
    assert result.rag_metrics is not None
    assert result.rag_metrics.failure is True
    assert "deterministic provider failure" not in result.model_dump_json()
    assert telemetry.events[0].answer_status == "failed"
    assert telemetry.events[0].error_type == "RuntimeError"
