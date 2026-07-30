"""Tests for chat API endpoints."""

from unittest.mock import AsyncMock, patch

import pytest

from backend.app.ai.contracts import GenerationResult
from backend.app.db.models import Conversation, Message


class TestChatEndpoint:
    """Test POST /v1/chat endpoint."""

    @patch("backend.app.services.chat.CoreAIRuntime.generate")
    def test_chat_success(self, mock_generate, client, test_api_key, test_agent):
        """Test successful chat request."""
        plain_key, _ = test_api_key
        
        # Mock AI response
        mock_generate.return_value = AsyncMock(
            return_value=GenerationResult(
                content="Hello! How can I help you?",
                model="deepseek-v4-flash",
                prompt_tokens=10,
                completion_tokens=20,
            )
        )
        
        response = client.post(
            "/v1/chat",
            json={
                "agent_id": test_agent.id,
                "message": "Hello",
            },
            headers={"X-API-Key": plain_key},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "conversation_id" in data
        assert "message" in data
        assert data["message"]["role"] == "assistant"
        assert data["message"]["content"] == "Hello! How can I help you?"

    def test_chat_agent_not_found(self, client, test_api_key):
        """Test chat with non-existent agent returns 404."""
        plain_key, _ = test_api_key
        
        response = client.post(
            "/v1/chat",
            json={
                "agent_id": "non-existent-agent",
                "message": "Hello",
            },
            headers={"X-API-Key": plain_key},
        )
        
        assert response.status_code == 404
        assert "Agent" in response.json()["message"]

    def test_chat_agent_belongs_to_another_client(
        self, client, test_api_key, another_agent
    ):
        """Test accessing agent from another client returns 404."""
        plain_key, _ = test_api_key
        
        response = client.post(
            "/v1/chat",
            json={
                "agent_id": another_agent.id,
                "message": "Hello",
            },
            headers={"X-API-Key": plain_key},
        )
        
        # Should return 404 to not leak existence
        assert response.status_code == 404

    def test_chat_message_too_long(self, client, test_api_key, test_agent):
        """Test message exceeding max length returns 422."""
        plain_key, _ = test_api_key
        
        # Create message longer than max_message_length (10000)
        long_message = "a" * 10001
        
        response = client.post(
            "/v1/chat",
            json={
                "agent_id": test_agent.id,
                "message": long_message,
            },
            headers={"X-API-Key": plain_key},
        )
        
        assert response.status_code == 422
        assert "exceeds maximum length" in response.json()["message"]

    @patch("backend.app.services.chat.CoreAIRuntime.generate")
    def test_chat_with_conversation_id(
        self, mock_generate, client, db, test_api_key, test_agent, test_client_record
    ):
        """Test continuing existing conversation."""
        plain_key, _ = test_api_key
        
        # Create existing conversation
        conversation = Conversation(
            id="test-conv-1",
            client_id=test_client_record.id,
            agent_id=test_agent.id,
        )
        db.add(conversation)
        db.commit()
        
        # Mock AI response
        mock_generate.return_value = AsyncMock(
            return_value=GenerationResult(
                content="Response",
                model="deepseek-v4-flash",
                prompt_tokens=10,
                completion_tokens=20,
            )
        )
        
        response = client.post(
            "/v1/chat",
            json={
                "agent_id": test_agent.id,
                "message": "Hello",
                "conversation_id": conversation.id,
            },
            headers={"X-API-Key": plain_key},
        )
        
        assert response.status_code == 200
        assert response.json()["conversation_id"] == conversation.id

    def test_chat_conversation_belongs_to_another_client(
        self, client, db, test_api_key, test_agent, another_client_record, another_agent
    ):
        """Test accessing conversation from another client returns 403."""
        plain_key, _ = test_api_key
        
        # Create conversation for another client
        conversation = Conversation(
            id="other-conv-1",
            client_id=another_client_record.id,
            agent_id=another_agent.id,
        )
        db.add(conversation)
        db.commit()
        
        response = client.post(
            "/v1/chat",
            json={
                "agent_id": test_agent.id,
                "message": "Hello",
                "conversation_id": conversation.id,
            },
            headers={"X-API-Key": plain_key},
        )
        
        assert response.status_code == 403

    @patch("backend.app.services.chat.CoreAIRuntime.generate")
    def test_chat_idempotency(
        self, mock_generate, client, test_api_key, test_agent
    ):
        """Test idempotency key prevents duplicate processing."""
        plain_key, _ = test_api_key
        
        # Mock AI response
        mock_generate.return_value = AsyncMock(
            return_value=GenerationResult(
                content="First response",
                model="deepseek-v4-flash",
                prompt_tokens=10,
                completion_tokens=20,
            )
        )
        
        idempotency_key = "test-idempotency-key-123"
        
        # First request
        response1 = client.post(
            "/v1/chat",
            json={
                "agent_id": test_agent.id,
                "message": "Hello",
                "idempotency_key": idempotency_key,
            },
            headers={"X-API-Key": plain_key},
        )
        
        assert response1.status_code == 200
        message_id_1 = response1.json()["message"]["id"]
        
        # Second request with same idempotency key
        response2 = client.post(
            "/v1/chat",
            json={
                "agent_id": test_agent.id,
                "message": "Hello again",  # Different message
                "idempotency_key": idempotency_key,
            },
            headers={"X-API-Key": plain_key},
        )
        
        assert response2.status_code == 200
        message_id_2 = response2.json()["message"]["id"]
        
        # Should return same message ID
        assert message_id_1 == message_id_2


class TestGetConversation:
    """Test GET /v1/conversations/{id} endpoint."""

    def test_get_conversation_success(
        self, client, db, test_api_key, test_agent, test_client_record
    ):
        """Test getting conversation details."""
        plain_key, _ = test_api_key
        
        # Create conversation
        conversation = Conversation(
            id="test-conv-1",
            client_id=test_client_record.id,
            agent_id=test_agent.id,
        )
        db.add(conversation)
        db.commit()
        
        response = client.get(
            f"/v1/conversations/{conversation.id}",
            headers={"X-API-Key": plain_key},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == conversation.id
        assert data["agent_id"] == test_agent.id

    def test_get_conversation_not_found(self, client, test_api_key):
        """Test getting non-existent conversation returns 404."""
        plain_key, _ = test_api_key
        
        response = client.get(
            "/v1/conversations/non-existent",
            headers={"X-API-Key": plain_key},
        )
        
        assert response.status_code == 404

    def test_get_conversation_belongs_to_another_client(
        self, client, db, test_api_key, another_client_record, another_agent
    ):
        """Test accessing conversation from another client returns 403."""
        plain_key, _ = test_api_key
        
        # Create conversation for another client
        conversation = Conversation(
            id="other-conv-1",
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


class TestGetConversationMessages:
    """Test GET /v1/conversations/{id}/messages endpoint."""

    def test_get_messages_success(
        self, client, db, test_api_key, test_agent, test_client_record
    ):
        """Test getting conversation messages."""
        plain_key, _ = test_api_key
        
        # Create conversation with messages
        conversation = Conversation(
            id="test-conv-1",
            client_id=test_client_record.id,
            agent_id=test_agent.id,
        )
        db.add(conversation)
        
        message1 = Message(
            id="msg-1",
            conversation_id=conversation.id,
            role="user",
            content="Hello",
        )
        message2 = Message(
            id="msg-2",
            conversation_id=conversation.id,
            role="assistant",
            content="Hi there!",
        )
        db.add_all([message1, message2])
        db.commit()
        
        response = client.get(
            f"/v1/conversations/{conversation.id}/messages",
            headers={"X-API-Key": plain_key},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["messages"]) == 2
        assert data["total"] == 2

    def test_get_messages_belongs_to_another_client(
        self, client, db, test_api_key, another_client_record, another_agent
    ):
        """Test accessing messages from another client returns 403."""
        plain_key, _ = test_api_key
        
        # Create conversation for another client
        conversation = Conversation(
            id="other-conv-1",
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


class TestErrorHandling:
    """Test error handling and response format."""

    def test_error_response_format(self, client):
        """Test that errors return standardized format."""
        response = client.post("/v1/chat", json={"agent_id": "test", "message": "hi"})
        
        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert "message" in data

    def test_no_traceback_in_response(self, client, test_api_key, test_agent):
        """Test that errors don't expose tracebacks."""
        plain_key, _ = test_api_key
        
        # Trigger an error
        response = client.post(
            "/v1/chat",
            json={
                "agent_id": "invalid",
                "message": "test",
            },
            headers={"X-API-Key": plain_key},
        )
        
        response_text = response.text.lower()
        
        # Should not contain traceback keywords
        assert "traceback" not in response_text
        assert "exception" not in response_text
        assert "sqlalchemy" not in response_text
        assert ".py" not in response_text
