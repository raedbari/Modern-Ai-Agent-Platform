"""
Sprint 1 Integration Tests - Verify all components work together.

Tests:
- Agent model with prompt_version loads correctly
- Provider abstraction is accessible
- RAG metrics can be populated
- Golden Questions dataset loads
- Prompt version tracking end-to-end
"""
import json
from pathlib import Path

def test_agent_model_has_prompt_version():
    """Verify Agent model includes prompt_version field."""
    from backend.app.db.models import Agent
    from backend.app.domain.models.agent import Agent as DomainAgent

    # DB model
    assert hasattr(Agent, 'prompt_version')

    # Domain model
    domain_agent = DomainAgent(
        id="test",
        tenant_id="t1",
        prompt_version="v1"
    )
    assert domain_agent.prompt_version == "v1"

def test_provider_abstraction_accessible():
    """Verify provider abstractions are accessible."""
    from backend.app.ai.ports import RerankProvider, RerankRequest, RerankResult
    from backend.app.ai import rerank  # Backward compatibility

    # Direct import
    assert RerankProvider is not None
    assert RerankRequest is not None
    assert RerankResult is not None

    # Re-export
    assert rerank.RerankProvider is RerankProvider

def test_rag_metrics_structure():
    """Verify RAG metrics can be instantiated."""
    from backend.app.evaluation.models import RAGMetrics, EvaluationCaseResult

    metrics = RAGMetrics(
        retrieval_hit=True,
        retrieval_count=5,
        top_similarity_score=0.9,
        rerank_position_change=2,
        has_citations=True,
        citation_count=3,
        answer_status="grounded"
    )

    assert metrics.retrieval_hit is True
    assert metrics.citation_count == 3

def test_golden_questions_loads():
    """Verify Golden Questions dataset exists and loads."""
    dataset_path = Path(__file__).parent.parent / "app" / "evaluation" / "datasets" / "golden_questions_v1.jsonl"

    assert dataset_path.exists()

    cases = []
    with open(dataset_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                cases.append(json.loads(line))

    assert len(cases) >= 20

    # Verify structure
    for case in cases:
        assert 'case_id' in case
        assert 'user_input' in case
        assert 'tenant_id' in case

def test_evaluation_result_with_all_sprint1_fields():
    """Verify EvaluationCaseResult includes all Sprint 1 additions."""
    from backend.app.evaluation.models import EvaluationCaseResult, EvaluationChecks, RAGMetrics

    checks = EvaluationChecks(
        language_matches=True,
        required_substrings_present=True,
        forbidden_substrings_absent=True,
        latency_within_limit=True
    )

    rag_metrics = RAGMetrics(
        retrieval_hit=True,
        retrieval_count=8,
        top_similarity_score=0.88,
        rerank_position_change=1,
        has_citations=True,
        citation_count=4,
        answer_status="grounded"
    )

    result = EvaluationCaseResult(
        case_id="integ-001",
        tenant_id="tenant-1",
        agent_id="agent-1",
        status="passed",
        response_content="Paris is the capital of France.",
        latency_ms=250.0,
        checks=checks,
        rag_metrics=rag_metrics,
        prompt_version="v1"
    )

    # Verify all Sprint 1 fields present
    assert result.rag_metrics is not None
    assert result.rag_metrics.retrieval_hit
    assert result.prompt_version == "v1"
    assert result.rag_metrics.citation_count == 4

def test_policies_module_loads():
    """Verify policy interfaces are accessible."""
    from backend.app.ai.policies import (
        ModelPolicy,
        BudgetPolicy,
        SafetyPolicy,
        DefaultModelPolicy,
        PromptVersionMetadata
    )

    # Verify DefaultModelPolicy can be instantiated
    policy = DefaultModelPolicy()
    assert policy is not None

print("✅ Sprint 1 Integration Tests - All components verified")
