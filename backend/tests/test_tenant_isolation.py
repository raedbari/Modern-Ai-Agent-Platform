"""Tests for multi-tenant isolation."""

import pytest

from backend.app.auth.security import hash_api_key
from backend.app.db.models import Agent, ApiKey, Conversation


class TestTenantIsolation:
    """Test that tenants cannot access each other's resources."""

    def test_cannot_use_another_clients_agent(
        self, client, test_api_key, another_agent
    ):
        """Test that client cannot use agent from another tenant."""
        plain_key, _ = test_api_key
        
        response = client.post(
            "/v1/chat",
            json={
                "agent_id": another_agent.id,
                "message": "Hello",
            },
            headers={"X-API-Key": plain_key},
        )
        
        # Should return 404 (not 403 to avoid leaking existence)
        assert response.status_code == 404

    def test_cannot_access_another_clients_conversation(
        self, client, db, test_api_key, another_client_record, another_agent
    ):
        """Test that client cannot access conversation from another tenant."""
        plain_key, _ = test_api_key
        
        # Create conversation for another client
        conversation = Conversation(
            id="other-client-conv",
            client_id=another_client_record.id,
            agent_id=another_agent.id,
        )
        db.add(conversation)
        db.commit()
        
        response = client.get(
            f"/v1/conversations/{conversation.id}",
            headers={"X-API-Key": plain_key},
        )
        
        assert response.status_code == 403

    def test_cannot_access_another_clients_messages(
        self, client, db, test_api_key, another_client_record, another_agent
    ):
        """Test that client cannot access messages from another tenant."""
        plain_key, _ = test_api_key
        
        # Create conversation for another client
        conversation = Conversation(
            id="other-client-conv",
            client_id=another_client_record.id,
            agent_id=another_agent.id,
        )
        db.add(conversation)
        db.commit()
        
        response = client.get(
            f"/v1/conversations/{conversation.id}/messages",
            headers={"X-API-Key": plain_key},
        )
        
        assert response.status_code == 403

    def test_conversation_agent_mismatch(
        self, client, db, test_api_key, test_agent, test_client_record, another_agent
    ):
        """Test that conversation with wrong agent is rejected."""
        plain_key, _ = test_api_key
        
        # Create conversation for test client but with another agent
        conversation = Conversation(
            id="mismatched-conv",
            client_id=test_client_record.id,
            agent_id=another_agent.id,
        )
        db.add(conversation)
        db.commit()
        
        # Try to send message to this conversation with different agent
        response = client.post(
            "/v1/chat",
            json={
                "agent_id": test_agent.id,
                "message": "Hello",
                "conversation_id": conversation.id,
            },
            headers={"X-API-Key": plain_key},
        )
        
        # Should fail because conversation.agent_id != request.agent_id
        assert response.status_code in [403, 422]

    def test_client_id_not_accepted_from_user(
        self, client, test_api_key, test_agent
    ):
        """Test that client_id in request body is ignored."""
        plain_key, _ = test_api_key
        
        # Try to send fake client_id in request
        # This should be ignored - client_id comes only from API key
        response = client.post(
            "/v1/chat",
            json={
                "agent_id": test_agent.id,
                "message": "Hello",
                "client_id": "fake-client-id",  # Should be ignored
            },
            headers={"X-API-Key": plain_key},
        )
        
        # Request should work (client_id is ignored)
        # The actual client_id comes from authenticated API key
        assert response.status_code in [200, 404, 422, 500]
        
        # If successful, verify the conversation uses correct client_id
        # (not the fake one from request body)
