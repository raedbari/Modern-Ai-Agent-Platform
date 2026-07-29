"""Tests for authentication and authorization."""

from datetime import datetime, timedelta, timezone

import pytest

from backend.app.auth.security import hash_api_key, is_api_key_expired, verify_api_key
from backend.app.db.models import ApiKey


class TestApiKeySecurity:
    """Test API key hashing and verification."""

    def test_hash_api_key(self):
        """Test that API key hashing works."""
        api_key = "test-key-12345"
        hashed = hash_api_key(api_key)
        
        assert hashed != api_key
        assert len(hashed) > 0

    def test_verify_api_key_success(self):
        """Test successful API key verification."""
        api_key = "test-key-12345"
        hashed = hash_api_key(api_key)
        
        assert verify_api_key(api_key, hashed) is True

    def test_verify_api_key_failure(self):
        """Test failed API key verification."""
        api_key = "test-key-12345"
        wrong_key = "wrong-key-12345"
        hashed = hash_api_key(api_key)
        
        assert verify_api_key(wrong_key, hashed) is False

    def test_is_api_key_expired_no_expiration(self):
        """Test that keys without expiration are not expired."""
        assert is_api_key_expired(None) is False

    def test_is_api_key_expired_future_expiration(self):
        """Test that keys with future expiration are not expired."""
        future = datetime.now(timezone.utc) + timedelta(days=30)
        assert is_api_key_expired(future) is False

    def test_is_api_key_expired_past_expiration(self):
        """Test that keys with past expiration are expired."""
        past = datetime.now(timezone.utc) - timedelta(days=1)
        assert is_api_key_expired(past) is True


class TestAuthenticationEndpoint:
    """Test authentication via API endpoints."""

    def test_missing_api_key(self, client):
        """Test request without API key returns 401."""
        response = client.post("/v1/chat", json={
            "agent_id": "test-agent",
            "message": "Hello",
        })
        
        assert response.status_code == 401
        assert "API key is required" in response.json()["message"]

    def test_invalid_api_key(self, client, test_client_record, test_agent):
        """Test request with invalid API key returns 401."""
        response = client.post(
            "/v1/chat",
            json={
                "agent_id": test_agent.id,
                "message": "Hello",
            },
            headers={"X-API-Key": "invalid-key"},
        )
        
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["message"]

    def test_expired_api_key(self, client, db, test_client_record, test_agent):
        """Test request with expired API key returns 401."""
        # Create expired key
        expired_key = "expired-key-12345"
        api_key = ApiKey(
            client_id=test_client_record.id,
            key_hash=hash_api_key(expired_key),
            is_active=True,
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        db.add(api_key)
        db.commit()
        
        response = client.post(
            "/v1/chat",
            json={
                "agent_id": test_agent.id,
                "message": "Hello",
            },
            headers={"X-API-Key": expired_key},
        )
        
        assert response.status_code == 401
        assert "expired" in response.json()["message"].lower()

    def test_inactive_api_key(self, client, db, test_client_record, test_agent):
        """Test request with inactive API key returns 401."""
        # Create inactive key
        inactive_key = "inactive-key-12345"
        api_key = ApiKey(
            client_id=test_client_record.id,
            key_hash=hash_api_key(inactive_key),
            is_active=False,
        )
        db.add(api_key)
        db.commit()
        
        response = client.post(
            "/v1/chat",
            json={
                "agent_id": test_agent.id,
                "message": "Hello",
            },
            headers={"X-API-Key": inactive_key},
        )
        
        assert response.status_code == 401

    def test_inactive_client(self, client, db, test_api_key, test_agent):
        """Test request for inactive client returns 403."""
        plain_key, _ = test_api_key
        
        # Deactivate client
        db_client = db.query(ApiKey).filter(ApiKey.key_hash == hash_api_key(plain_key)).first()
        from backend.app.db.models import Client
        client_record = db.query(Client).filter(Client.id == db_client.client_id).first()
        client_record.is_active = False
        db.commit()
        
        response = client.post(
            "/v1/chat",
            json={
                "agent_id": test_agent.id,
                "message": "Hello",
            },
            headers={"X-API-Key": plain_key},
        )
        
        assert response.status_code == 403
        assert "disabled" in response.json()["message"].lower()
