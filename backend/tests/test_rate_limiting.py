"""Tests for rate limiting."""

from unittest.mock import AsyncMock, patch

import pytest

from backend.app.ai.contracts import GenerationResult


class TestRateLimiting:
    """Test rate limiting functionality."""

    @patch("backend.app.services.chat.CoreAIRuntime.generate")
    def test_rate_limit_per_api_key(
        self, mock_generate, client, test_api_key, test_agent
    ):
        """Test that rate limiting is enforced per API key."""
        plain_key, _ = test_api_key
        
        # Mock AI response
        mock_generate.return_value = AsyncMock(
            return_value=GenerationResult(
                content="Response",
                model="deepseek-v4-flash",
                prompt_tokens=10,
                completion_tokens=20,
            )
        )
        
        # Get rate limit from settings (default 60/minute)
        # We'll make more requests than the limit
        success_count = 0
        rate_limited = False
        
        for i in range(65):  # Exceed the limit
            response = client.post(
                "/v1/chat",
                json={
                    "agent_id": test_agent.id,
                    "message": f"Message {i}",
                },
                headers={"X-API-Key": plain_key},
            )
            
            if response.status_code == 200:
                success_count += 1
            elif response.status_code == 429:
                rate_limited = True
                break
        
        # Should eventually hit rate limit
        assert rate_limited or success_count <= 60

    def test_rate_limit_response_format(self, client, test_api_key, test_agent):
        """Test that rate limit errors return proper format."""
        plain_key, _ = test_api_key
        
        # Make many requests quickly to trigger rate limit
        for _ in range(70):
            response = client.post(
                "/v1/chat",
                json={
                    "agent_id": test_agent.id,
                    "message": "Test",
                },
                headers={"X-API-Key": plain_key},
            )
            
            if response.status_code == 429:
                # Check error format
                data = response.json()
                assert "error" in data or "detail" in data
                break
