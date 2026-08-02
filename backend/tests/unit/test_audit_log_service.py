"""Unit tests for audit log service sanitization logic.

These tests verify that sensitive data is properly redacted from
audit logs without requiring a database connection.
"""

import pytest

from backend.app.services.audit_log import (
    _is_sensitive_field,
    _sanitize_dict,
    _sanitize_changed_fields,
    _sanitize_metadata,
    REDACTED_VALUE,
)


class TestSensitiveFieldDetection:
    """Test detection of sensitive field names."""

    @pytest.mark.parametrize(
        "field_name,expected",
        [
            # Sensitive fields (should be True)
            ("password", True),
            ("Password", True),
            ("PASSWORD", True),
            ("user_password", True),
            ("password_hash", True),
            ("secret", True),
            ("client_secret", True),
            ("api_secret", True),
            ("token", True),
            ("access_token", True),
            ("refresh_token", True),
            ("api_key", True),
            ("key", True),
            ("private_key", True),
            ("public_key", True),
            ("digest", True),
            ("key_digest", True),
            ("authorization", True),
            ("Authorization", True),
            ("credential", True),
            ("credentials", True),
            # Non-sensitive fields (should be False)
            ("username", False),
            ("email", False),
            ("name", False),
            ("id", False),
            ("tenant_id", False),
            ("created_at", False),
            ("is_active", False),
        ],
    )
    def test_is_sensitive_field(self, field_name: str, expected: bool):
        """Test that sensitive field names are correctly identified."""
        assert _is_sensitive_field(field_name) == expected


class TestDictSanitization:
    """Test dictionary sanitization logic."""

    def test_sanitize_flat_dict_with_sensitive_fields(self):
        """Test sanitizing a flat dictionary with sensitive fields."""
        data = {
            "username": "admin@example.com",
            "password": "super_secret_123",
            "email": "admin@example.com",
            "api_key": "maap_abc123.xyz789",
        }
        
        result = _sanitize_dict(data)
        
        assert result["username"] == "admin@example.com"
        assert result["email"] == "admin@example.com"
        assert result["password"] == REDACTED_VALUE
        assert result["api_key"] == REDACTED_VALUE

    def test_sanitize_nested_dict(self):
        """Test sanitizing nested dictionaries."""
        data = {
            "user": {
                "username": "admin",
                "password": "secret123",
                "settings": {
                    "theme": "dark",
                    "api_token": "token_xyz",
                }
            },
            "tenant_id": "tenant-123",
        }
        
        result = _sanitize_dict(data)
        
        assert result["user"]["username"] == "admin"
        assert result["user"]["password"] == REDACTED_VALUE
        assert result["user"]["settings"]["theme"] == "dark"
        assert result["user"]["settings"]["api_token"] == REDACTED_VALUE
        assert result["tenant_id"] == "tenant-123"

    def test_sanitize_dict_with_lists(self):
        """Test sanitizing dictionaries containing lists."""
        data = {
            "users": [
                {"name": "user1", "password": "pass1"},
                {"name": "user2", "secret": "secret2"},
            ],
            "api_keys": ["key1", "key2"],
        }
        
        result = _sanitize_dict(data)
        
        assert result["users"][0]["name"] == "user1"
        assert result["users"][0]["password"] == REDACTED_VALUE
        assert result["users"][1]["name"] == "user2"
        assert result["users"][1]["secret"] == REDACTED_VALUE
        assert result["api_keys"] == ["key1", "key2"]  # List of strings unchanged

    def test_sanitize_none_dict(self):
        """Test that None input returns None."""
        assert _sanitize_dict(None) is None

    def test_sanitize_empty_dict(self):
        """Test sanitizing an empty dictionary."""
        assert _sanitize_dict({}) == {}

    def test_sanitize_authorization_header(self):
        """Test that Authorization headers are redacted."""
        data = {
            "headers": {
                "Content-Type": "application/json",
                "Authorization": "Bearer abc123xyz",
                "X-Request-ID": "req-123",
            }
        }
        
        result = _sanitize_dict(data)
        
        assert result["headers"]["Content-Type"] == "application/json"
        assert result["headers"]["Authorization"] == REDACTED_VALUE
        assert result["headers"]["X-Request-ID"] == "req-123"


class TestChangedFieldsSanitization:
    """Test changed fields sanitization."""

    def test_sanitize_changed_fields_with_password(self):
        """Test sanitizing password changes."""
        changed_fields = {
            "name": {
                "old": "Old Name",
                "new": "New Name",
            },
            "password": {
                "old": "old_password",
                "new": "new_password",
            },
        }
        
        result = _sanitize_changed_fields(changed_fields)
        
        assert result["name"]["old"] == "Old Name"
        assert result["name"]["new"] == "New Name"
        assert result["password"] == REDACTED_VALUE

    def test_sanitize_changed_fields_with_status(self):
        """Test sanitizing non-sensitive field changes."""
        changed_fields = {
            "is_active": {
                "old": True,
                "new": False,
            },
        }
        
        result = _sanitize_changed_fields(changed_fields)
        
        assert result["is_active"]["old"] is True
        assert result["is_active"]["new"] is False


class TestMetadataSanitization:
    """Test metadata sanitization."""

    def test_sanitize_metadata_with_mixed_content(self):
        """Test sanitizing metadata with both safe and sensitive data."""
        metadata = {
            "request_id": "req-123",
            "ip_address": "192.168.1.1",
            "user_agent": "Mozilla/5.0",
            "raw_api_key": "maap_123.abc",
            "operation": "delete_tenant",
        }
        
        result = _sanitize_metadata(metadata)
        
        assert result["request_id"] == "req-123"
        assert result["ip_address"] == "192.168.1.1"
        assert result["user_agent"] == "Mozilla/5.0"
        assert result["raw_api_key"] == REDACTED_VALUE
        assert result["operation"] == "delete_tenant"

    def test_sanitize_metadata_none(self):
        """Test that None metadata returns None."""
        assert _sanitize_metadata(None) is None


class TestComplexSanitizationScenarios:
    """Test complex real-world sanitization scenarios."""

    def test_sanitize_admin_credential_update(self):
        """Test sanitizing admin credential update event."""
        data = {
            "admin_id": "admin-123",
            "admin_email": "admin@example.com",
            "old_credentials": {
                "password_hash": "hash_abc",
                "api_key_digest": "digest_xyz",
            },
            "new_credentials": {
                "password_hash": "hash_def",
                "api_key_digest": "digest_uvw",
            },
        }
        
        result = _sanitize_dict(data)
        
        assert result["admin_id"] == "admin-123"
        assert result["admin_email"] == "admin@example.com"
        assert result["old_credentials"]["password_hash"] == REDACTED_VALUE
        assert result["old_credentials"]["api_key_digest"] == REDACTED_VALUE
        assert result["new_credentials"]["password_hash"] == REDACTED_VALUE
        assert result["new_credentials"]["api_key_digest"] == REDACTED_VALUE

    def test_sanitize_api_key_creation_metadata(self):
        """Test sanitizing API key creation metadata."""
        metadata = {
            "key_id": "key-123",
            "key_name": "Production API Key",
            "raw_key": "maap_abc123.xyz789secret",
            "created_by": "admin@example.com",
            "expires_at": "2025-12-31T23:59:59Z",
        }
        
        result = _sanitize_metadata(metadata)
        
        assert result["key_id"] == "key-123"
        assert result["key_name"] == "Production API Key"
        assert result["raw_key"] == REDACTED_VALUE
        assert result["created_by"] == "admin@example.com"
        assert result["expires_at"] == "2025-12-31T23:59:59Z"

    def test_sanitize_auth_failure_metadata(self):
        """Test sanitizing authentication failure metadata."""
        metadata = {
            "attempted_username": "admin",
            "attempted_password": "wrong_password",
            "ip_address": "10.0.0.1",
            "user_agent": "curl/7.68.0",
            "failure_reason": "invalid_credentials",
        }
        
        result = _sanitize_metadata(metadata)
        
        assert result["attempted_username"] == "admin"
        assert result["attempted_password"] == REDACTED_VALUE
        assert result["ip_address"] == "10.0.0.1"
        assert result["user_agent"] == "curl/7.68.0"
        assert result["failure_reason"] == "invalid_credentials"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
