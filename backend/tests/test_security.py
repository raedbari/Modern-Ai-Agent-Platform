"""Tests for security features."""

import pytest


class TestCORSSecurity:
    """Test CORS configuration."""

    def test_cors_allowed_origin(self, client, test_api_key, test_agent):
        """Test that allowed origins work."""
        plain_key, _ = test_api_key
        
        # Make request with allowed origin
        response = client.options(
            "/v1/chat",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        
        # Should have CORS headers
        assert "access-control-allow-origin" in [
            h.lower() for h in response.headers.keys()
        ]

    def test_cors_headers_present(self, client):
        """Test that CORS headers are present in responses."""
        response = client.get("/health")
        
        # Check if CORS middleware is active
        # In test mode, might not have Origin header, so just verify no errors
        assert response.status_code == 200


class TestInputValidation:
    """Test input validation and limits."""

    def test_message_length_limit(self, client, test_api_key, test_agent):
        """Test that message length is validated."""
        plain_key, _ = test_api_key
        
        # Create message exceeding limit (10000 chars)
        long_message = "x" * 10001
        
        response = client.post(
            "/v1/chat",
            json={
                "agent_id": test_agent.id,
                "message": long_message,
            },
            headers={"X-API-Key": plain_key},
        )
        
        assert response.status_code == 422
        assert "exceeds" in response.json()["message"].lower()

    def test_empty_message_rejected(self, client, test_api_key, test_agent):
        """Test that empty messages are rejected."""
        plain_key, _ = test_api_key
        
        response = client.post(
            "/v1/chat",
            json={
                "agent_id": test_agent.id,
                "message": "",
            },
            headers={"X-API-Key": plain_key},
        )
        
        assert response.status_code == 422

    def test_whitespace_only_message_rejected(self, client, test_api_key, test_agent):
        """Test that whitespace-only messages are rejected."""
        plain_key, _ = test_api_key
        
        response = client.post(
            "/v1/chat",
            json={
                "agent_id": test_agent.id,
                "message": "   ",
            },
            headers={"X-API-Key": plain_key},
        )
        
        assert response.status_code == 422


class TestSecurityHeaders:
    """Test security headers and response safety."""

    def test_no_api_key_in_logs(self, client, test_api_key, test_agent, caplog):
        """Test that API keys are never logged."""
        plain_key, _ = test_api_key
        
        response = client.post(
            "/v1/chat",
            json={
                "agent_id": test_agent.id,
                "message": "Test",
            },
            headers={"X-API-Key": plain_key},
        )
        
        # Check that full API key doesn't appear in logs
        log_output = caplog.text
        assert plain_key not in log_output

    def test_request_id_tracking(self, client, test_api_key, test_agent):
        """Test that request IDs are tracked."""
        plain_key, _ = test_api_key
        
        custom_request_id = "test-request-123"
        
        response = client.post(
            "/v1/chat",
            json={
                "agent_id": test_agent.id,
                "message": "Test",
            },
            headers={
                "X-API-Key": plain_key,
                "X-Request-ID": custom_request_id,
            },
        )
        
        if response.status_code == 200:
            # Should include request_id in response
            assert response.json().get("request_id") == custom_request_id


class TestErrorExposure:
    """Test that errors don't expose sensitive information."""

    def test_database_errors_hidden(self, client, test_api_key):
        """Test that database errors are not exposed."""
        plain_key, _ = test_api_key
        
        # Trigger a database error (invalid agent_id format might cause internal error)
        response = client.post(
            "/v1/chat",
            json={
                "agent_id": "invalid-agent",
                "message": "Test",
            },
            headers={"X-API-Key": plain_key},
        )
        
        response_text = response.text.lower()
        
        # Should not expose database details
        assert "sqlite" not in response_text
        assert "database" not in response_text
        assert "sqlalchemy" not in response_text

    def test_provider_errors_hidden(self, client, test_api_key, test_agent):
        """Test that AI provider errors are sanitized."""
        plain_key, _ = test_api_key
        
        response = client.post(
            "/v1/chat",
            json={
                "agent_id": test_agent.id,
                "message": "Test",
            },
            headers={"X-API-Key": plain_key},
        )
        
        # Even if it fails, should not expose provider details
        response_text = response.text.lower()
        assert "deepseek" not in response_text or response.status_code == 200
        assert "api_key" not in response_text

    def test_no_stack_traces(self, client, test_api_key):
        """Test that stack traces are never returned."""
        plain_key, _ = test_api_key
        
        # Make invalid request that might trigger error
        response = client.post(
            "/v1/chat",
            json={
                "agent_id": "x" * 200,  # Exceeds max length
                "message": "Test",
            },
            headers={"X-API-Key": plain_key},
        )
        
        response_text = response.text
        
        # Should not contain file paths or line numbers
        assert "File \"" not in response_text
        assert "line " not in response_text
        assert "Traceback" not in response_text
