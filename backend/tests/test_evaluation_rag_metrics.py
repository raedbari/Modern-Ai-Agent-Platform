"""
Tests for RAG metrics in evaluation system.

Verifies:
- RAGMetrics dataclass structure and validation
- EvaluationCaseResult includes rag_metrics field
- Metrics capture retrieval, reranking, and citation data
- Prompt version tracking in evaluation results
"""
import pytest
from app.evaluation.models import RAGMetrics, EvaluationCaseResult


class TestRAGMetricsStructure:
    """Test suite for RAGMetrics dataclass."""
    
    def test_rag_metrics_all_fields_present(self):
        """Verify RAGMetrics has all required fields."""
        metrics = RAGMetrics(
            retrieval_hit=True,
            retrieval_count=5,
            top_similarity_score=0.92,
            rerank_position_change=2,
            has_citations=True,
            citation_count=3,
            answer_status="answered"
        )
        
        assert metrics.retrieval_hit is True
        assert metrics.retrieval_count == 5
        assert metrics.top_similarity_score == 0.92
        assert metrics.rerank_position_change == 2
        assert metrics.has_citations is True
        assert metrics.citation_count == 3
        assert metrics.answer_status == "answered"
        
    def test_rag_metrics_optional_fields(self):
        """Verify optional fields can be None."""
        metrics = RAGMetrics(
            retrieval_hit=False,
            retrieval_count=0,
            top_similarity_score=None,
            rerank_position_change=None,
            has_citations=False,
            citation_count=0,
            answer_status="no_results"
        )
        
        assert metrics.retrieval_hit is False
        assert metrics.top_similarity_score is None
        assert metrics.rerank_position_change is None
        
    def test_rag_metrics_answer_status_values(self):
        """Verify answer_status accepts expected values."""
        valid_statuses = [
            "answered",
            "no_results",
            "insufficient_evidence",
            "refused",
            "error"
        ]
        
        for status in valid_statuses:
            metrics = RAGMetrics(
                retrieval_hit=(status == "answered"),
                retrieval_count=1 if status == "answered" else 0,
                top_similarity_score=0.8 if status == "answered" else None,
                rerank_position_change=None,
                has_citations=(status == "answered"),
                citation_count=1 if status == "answered" else 0,
                answer_status=status
            )
            assert metrics.answer_status == status


class TestRAGMetricsScenarios:
    """Test RAG metrics for different scenarios."""
    
    def test_successful_retrieval_with_rerank(self):
        """Test metrics when retrieval succeeds and rerank improves results."""
        metrics = RAGMetrics(
            retrieval_hit=True,
            retrieval_count=10,
            top_similarity_score=0.88,
            rerank_position_change=3,  # Top result moved up 3 positions
            has_citations=True,
            citation_count=2,
            answer_status="answered"
        )
        
        assert metrics.retrieval_hit
        assert metrics.rerank_position_change > 0
        assert metrics.has_citations
        
    def test_retrieval_miss(self):
        """Test metrics when retrieval finds no relevant documents."""
        metrics = RAGMetrics(
            retrieval_hit=False,
            retrieval_count=0,
            top_similarity_score=None,
            rerank_position_change=None,
            has_citations=False,
            citation_count=0,
            answer_status="no_results"
        )
        
        assert not metrics.retrieval_hit
        assert metrics.retrieval_count == 0
        assert metrics.citation_count == 0
        
    def test_retrieval_without_rerank(self):
        """Test metrics when retrieval succeeds but rerank not used."""
        metrics = RAGMetrics(
            retrieval_hit=True,
            retrieval_count=5,
            top_similarity_score=0.75,
            rerank_position_change=None,  # Rerank not used
            has_citations=True,
            citation_count=1,
            answer_status="answered"
        )
        
        assert metrics.retrieval_hit
        assert metrics.rerank_position_change is None
        assert metrics.has_citations
        
    def test_insufficient_evidence(self):
        """Test metrics when documents retrieved but insufficient."""
        metrics = RAGMetrics(
            retrieval_hit=True,
            retrieval_count=2,
            top_similarity_score=0.45,  # Low similarity
            rerank_position_change=0,
            has_citations=False,
            citation_count=0,
            answer_status="insufficient_evidence"
        )
        
        assert metrics.retrieval_hit
        assert metrics.top_similarity_score < 0.6
        assert not metrics.has_citations


class TestEvaluationCaseResultIntegration:
    """Test RAG metrics integration with EvaluationCaseResult."""
    
    def test_evaluation_result_includes_rag_metrics(self):
        """Verify EvaluationCaseResult can hold RAG metrics."""
        rag_metrics = RAGMetrics(
            retrieval_hit=True,
            retrieval_count=8,
            top_similarity_score=0.91,
            rerank_position_change=1,
            has_citations=True,
            citation_count=4,
            answer_status="answered"
        )
        
        result = EvaluationCaseResult(
            case_id="test-001",
            status="passed",
            answer="Paris is the capital of France.",
            latency_ms=234.5,
            token_count=45,
            cost_usd=0.0012,
            rag_metrics=rag_metrics,
            prompt_version="v1"
        )
        
        assert result.rag_metrics is not None
        assert result.rag_metrics.retrieval_hit
        assert result.rag_metrics.citation_count == 4
        
    def test_evaluation_result_includes_prompt_version(self):
        """Verify EvaluationCaseResult tracks prompt version."""
        result = EvaluationCaseResult(
            case_id="test-002",
            status="passed",
            answer="Test answer",
            latency_ms=150.0,
            token_count=20,
            cost_usd=0.0005,
            rag_metrics=None,
            prompt_version="v2-experimental"
        )
        
        assert result.prompt_version == "v2-experimental"
        
    def test_evaluation_result_without_rag_metrics(self):
        """Verify EvaluationCaseResult works without RAG metrics (non-RAG agent)."""
        result = EvaluationCaseResult(
            case_id="test-003",
            status="passed",
            answer="Direct response",
            latency_ms=100.0,
            token_count=15,
            cost_usd=0.0003,
            rag_metrics=None,
            prompt_version="v1"
        )
        
        assert result.rag_metrics is None
        assert result.prompt_version == "v1"


class TestRAGMetricsValidation:
    """Test validation and edge cases for RAG metrics."""
    
    def test_zero_retrieval_count_with_hit(self):
        """Test edge case: retrieval_hit=True but retrieval_count=0."""
        # This shouldn't happen in practice, but test the data model
        metrics = RAGMetrics(
            retrieval_hit=True,
            retrieval_count=0,  # Inconsistent
            top_similarity_score=None,
            rerank_position_change=None,
            has_citations=False,
            citation_count=0,
            answer_status="error"
        )
        
        # Data model accepts it (validation happens at business logic level)
        assert metrics.retrieval_hit
        assert metrics.retrieval_count == 0
        
    def test_negative_rerank_position_change(self):
        """Test negative rerank position change (result moved down)."""
        metrics = RAGMetrics(
            retrieval_hit=True,
            retrieval_count=5,
            top_similarity_score=0.7,
            rerank_position_change=-2,  # Moved down 2 positions
            has_citations=True,
            citation_count=1,
            answer_status="answered"
        )
        
        assert metrics.rerank_position_change == -2
        
    def test_high_similarity_score(self):
        """Test very high similarity score."""
        metrics = RAGMetrics(
            retrieval_hit=True,
            retrieval_count=3,
            top_similarity_score=0.995,
            rerank_position_change=0,
            has_citations=True,
            citation_count=2,
            answer_status="answered"
        )
        
        assert metrics.top_similarity_score > 0.99
        
    def test_many_citations(self):
        """Test case with many citations."""
        metrics = RAGMetrics(
            retrieval_hit=True,
            retrieval_count=20,
            top_similarity_score=0.85,
            rerank_position_change=5,
            has_citations=True,
            citation_count=12,
            answer_status="answered"
        )
        
        assert metrics.citation_count > 10


class TestPromptVersionTracking:
    """Test prompt version tracking in evaluation results."""
    
    def test_different_prompt_versions(self):
        """Test evaluation results can track different prompt versions."""
        versions = ["v1", "v2", "v1.5-beta", "2024-01-15", "experimental"]
        
        for version in versions:
            result = EvaluationCaseResult(
                case_id=f"test-{version}",
                status="passed",
                answer="Test",
                latency_ms=100.0,
                token_count=10,
                cost_usd=0.0001,
                rag_metrics=None,
                prompt_version=version
            )
            
            assert result.prompt_version == version
            
    def test_prompt_version_with_rag_metrics(self):
        """Test prompt version tracking alongside RAG metrics."""
        rag_metrics = RAGMetrics(
            retrieval_hit=True,
            retrieval_count=5,
            top_similarity_score=0.8,
            rerank_position_change=1,
            has_citations=True,
            citation_count=2,
            answer_status="answered"
        )
        
        result = EvaluationCaseResult(
            case_id="test-version-rag",
            status="passed",
            answer="Test answer",
            latency_ms=200.0,
            token_count=30,
            cost_usd=0.0008,
            rag_metrics=rag_metrics,
            prompt_version="v2.1"
        )
        
        assert result.prompt_version == "v2.1"
        assert result.rag_metrics.retrieval_hit
