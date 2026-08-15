"""
Tests for Provider abstraction contracts in app.ai.ports.

Verifies:
- RerankProvider protocol is correctly defined
- RerankRequest/RerankResult dataclasses work as expected
- Backward compatibility with app.ai.rerank imports
- Mock implementations satisfy protocol requirements
"""
import pytest
from typing import Protocol
from app.ai.ports import RerankProvider, RerankRequest, RerankResult
from app.ai import rerank  # Test backward compatibility


class TestRerankProviderProtocol:
    """Test suite for RerankProvider protocol."""
    
    def test_rerank_provider_is_protocol(self):
        """Verify RerankProvider is defined as a Protocol."""
        assert issubclass(type(RerankProvider), type(Protocol))
        
    def test_rerank_provider_has_rerank_method(self):
        """Verify RerankProvider protocol requires rerank() method."""
        # Check protocol has the method signature
        assert hasattr(RerankProvider, 'rerank')
        
    def test_rerank_request_dataclass(self):
        """Verify RerankRequest dataclass structure."""
        request = RerankRequest(
            query="What is the capital of France?",
            documents=["Paris is the capital.", "London is nice.", "Berlin exists."],
            top_k=2
        )
        
        assert request.query == "What is the capital of France?"
        assert len(request.documents) == 3
        assert request.top_k == 2
        
    def test_rerank_result_dataclass(self):
        """Verify RerankResult dataclass structure."""
        result = RerankResult(
            ranked_indices=[0, 2, 1],
            scores=[0.95, 0.7, 0.3]
        )
        
        assert result.ranked_indices == [0, 2, 1]
        assert result.scores == [0.95, 0.7, 0.3]
        assert len(result.ranked_indices) == len(result.scores)


class MockRerankProvider:
    """Mock implementation to test protocol compliance."""
    
    async def rerank(self, request: RerankRequest) -> RerankResult:
        """Simple mock that returns documents in reverse order."""
        num_docs = len(request.documents)
        top_k = min(request.top_k, num_docs) if request.top_k else num_docs
        
        # Return reverse order with decreasing scores
        ranked_indices = list(range(num_docs - 1, -1, -1))[:top_k]
        scores = [1.0 - (i * 0.1) for i in range(top_k)]
        
        return RerankResult(
            ranked_indices=ranked_indices,
            scores=scores
        )


class TestRerankProviderImplementation:
    """Test suite for RerankProvider implementations."""
    
    @pytest.mark.asyncio
    async def test_mock_provider_satisfies_protocol(self):
        """Verify mock implementation satisfies RerankProvider protocol."""
        provider: RerankProvider = MockRerankProvider()
        
        request = RerankRequest(
            query="test query",
            documents=["doc1", "doc2", "doc3"],
            top_k=2
        )
        
        result = await provider.rerank(request)
        
        assert isinstance(result, RerankResult)
        assert len(result.ranked_indices) == 2
        assert len(result.scores) == 2
        assert all(isinstance(idx, int) for idx in result.ranked_indices)
        assert all(isinstance(score, (int, float)) for score in result.scores)
        
    @pytest.mark.asyncio
    async def test_mock_provider_respects_top_k(self):
        """Verify mock provider respects top_k parameter."""
        provider = MockRerankProvider()
        
        request = RerankRequest(
            query="test",
            documents=["a", "b", "c", "d", "e"],
            top_k=3
        )
        
        result = await provider.rerank(request)
        
        assert len(result.ranked_indices) == 3
        assert len(result.scores) == 3
        
    @pytest.mark.asyncio
    async def test_mock_provider_handles_empty_top_k(self):
        """Verify provider handles None top_k (return all)."""
        provider = MockRerankProvider()
        
        request = RerankRequest(
            query="test",
            documents=["a", "b", "c"],
            top_k=None
        )
        
        result = await provider.rerank(request)
        
        assert len(result.ranked_indices) == 3
        assert len(result.scores) == 3


class TestBackwardCompatibility:
    """Test backward compatibility with app.ai.rerank imports."""
    
    def test_rerank_module_exports_provider(self):
        """Verify RerankProvider can be imported from app.ai.rerank."""
        assert hasattr(rerank, 'RerankProvider')
        assert rerank.RerankProvider is RerankProvider
        
    def test_rerank_module_exports_request(self):
        """Verify RerankRequest can be imported from app.ai.rerank."""
        assert hasattr(rerank, 'RerankRequest')
        assert rerank.RerankRequest is RerankRequest
        
    def test_rerank_module_exports_result(self):
        """Verify RerankResult can be imported from app.ai.rerank."""
        assert hasattr(rerank, 'RerankResult')
        assert rerank.RerankResult is RerankResult
        
    def test_legacy_imports_work(self):
        """Verify legacy code using app.ai.rerank imports continues to work."""
        from app.ai.rerank import RerankProvider as LegacyProvider
        from app.ai.rerank import RerankRequest as LegacyRequest
        from app.ai.rerank import RerankResult as LegacyResult
        
        # Create instances using legacy imports
        request = LegacyRequest(
            query="test",
            documents=["doc1"],
            top_k=1
        )
        
        result = LegacyResult(
            ranked_indices=[0],
            scores=[0.9]
        )
        
        assert isinstance(request, RerankRequest)
        assert isinstance(result, RerankResult)


class TestProviderContractValidation:
    """Test that provider implementations meet contract requirements."""
    
    @pytest.mark.asyncio
    async def test_provider_returns_correct_result_type(self):
        """Verify provider returns RerankResult instance."""
        provider = MockRerankProvider()
        request = RerankRequest(query="test", documents=["a", "b"], top_k=2)
        
        result = await provider.rerank(request)
        
        assert isinstance(result, RerankResult)
        
    @pytest.mark.asyncio
    async def test_provider_indices_within_bounds(self):
        """Verify returned indices are within document bounds."""
        provider = MockRerankProvider()
        documents = ["doc1", "doc2", "doc3"]
        request = RerankRequest(query="test", documents=documents, top_k=2)
        
        result = await provider.rerank(request)
        
        for idx in result.ranked_indices:
            assert 0 <= idx < len(documents), f"Index {idx} out of bounds for {len(documents)} documents"
            
    @pytest.mark.asyncio
    async def test_provider_scores_are_numeric(self):
        """Verify scores are numeric values."""
        provider = MockRerankProvider()
        request = RerankRequest(query="test", documents=["a", "b"], top_k=2)
        
        result = await provider.rerank(request)
        
        for score in result.scores:
            assert isinstance(score, (int, float)), f"Score {score} is not numeric"
            
    @pytest.mark.asyncio
    async def test_provider_result_lengths_match(self):
        """Verify ranked_indices and scores have same length."""
        provider = MockRerankProvider()
        request = RerankRequest(query="test", documents=["a", "b", "c"], top_k=2)
        
        result = await provider.rerank(request)
        
        assert len(result.ranked_indices) == len(result.scores), \
            "ranked_indices and scores must have same length"
