"""Tests for authentication and authorization."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from backend.app.auth.dependencies import get_authenticated_context
from backend.app.auth.security import hash_api_key, verify_api_key
from backend.app.db.models import ApiKey, Tenant
from backend.app.db.utils import create_api_key_for_tenant, generate_api_key


class TestSecurityFunctions:
    """Test security utility functions."""

    def test_generate_api_key_format(self):
        """Test that generated API keys have the correct format."""
        key = generate_api_key()
        assert key.startswith("maap_")
        assert len(key) == 69  # "maap_" + 64 hex characters

    def test_generate_api_key_uniqueness(self):
        """Test that generated keys are unique."""
        keys = {generate_api_key() for _ in range(100)}
        assert len(keys) == 100  # All should be unique

    def test_hash_and_verify_api_key(self):
        """Test hashing and verification of API keys."""
        plain_key = generate_api_key()
        hashed = hash_api_key(plain_key)
        
        # Hash should be different from plain key
        assert hashed != plain_key
        
        # Verification should succeed
        assert verify_api_key(plain_key, hashed)
        
        # Wrong key should fail
        wrong_key = generate_api_key()
        assert not verify_api_key(wrong_key, hashed)


class TestDatabaseKeyCreation:
    """Test database API key creation."""

    @pytest.mark.asyncio
    async def test_create_api_key_for_tenant(self, db_session, tenant1):
        """Test creating an API key for a tenant."""
        api_key, plain_key = await create_api_key_for_tenant(
            db_session, tenant1.id, "Test Key"
        )
        
        assert api_key.id is not None
        assert api_key.tenant_id == tenant1.id
        assert api_key.name == "Test Key"
        assert api_key.is_active is True
        assert api_key.key_hash != plain_key
        assert plain_key.startswith("maap_")
        
        # Verify the plain key matches the hash
        assert verify_api_key(plain_key, api_key.key_hash)

    @pytest.mark.asyncio
    async def test_create_api_key_with_expiry(self, db_session, tenant1):
        """Test creating an API key with expiration."""
        expires_at = datetime.now(timezone.utc) + timedelta(days=30)
        api_key, plain_key = await create_api_key_for_tenant(
            db_session, tenant1.id, "Expiring Key", expires_at=expires_at
        )
        
        assert api_key.expires_at is not None
        assert api_key.expires_at == expires_at


class TestAuthentication:
    """Test API key authentication."""

    @pytest.mark.asyncio
    async def test_valid_api_key_authentication(
        self, db_session, tenant1, api_key_tenant1
    ):
        """Test successful authentication with valid API key."""
        api_key, plain_key = api_key_tenant1
        
        context = await get_authenticated_context(plain_key, db_session)
        
        assert context.tenant_id == tenant1.id
        assert context.api_key_id == api_key.id
        assert context.api_key_name == api_key.name

    @pytest.mark.asyncio
    async def test_invalid_api_key_authentication(self, db_session):
        """Test authentication fails with invalid API key."""
        fake_key = "maap_" + "0" * 64
        
        with pytest.raises(HTTPException) as exc_info:
            await get_authenticated_context(fake_key, db_session)
        
        assert exc_info.value.status_code == 401
        assert "Invalid or expired API key" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_revoked_api_key_authentication(
        self, db_session, revoked_api_key
    ):
        """Test authentication fails with revoked API key."""
        _, plain_key = revoked_api_key
        
        with pytest.raises(HTTPException) as exc_info:
            await get_authenticated_context(plain_key, db_session)
        
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_expired_api_key_authentication(
        self, db_session, tenant1
    ):
        """Test authentication fails with expired API key."""
        # Create an expired key
        expires_at = datetime.now(timezone.utc) - timedelta(days=1)
        _, plain_key = await create_api_key_for_tenant(
            db_session, tenant1.id, "Expired Key", expires_at=expires_at
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await get_authenticated_context(plain_key, db_session)
        
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_inactive_tenant_authentication(
        self, db_session, inactive_tenant
    ):
        """Test authentication fails when tenant is inactive."""
        _, plain_key = await create_api_key_for_tenant(
            db_session, inactive_tenant.id, "Key for inactive tenant"
        )
        
        with pytest.raises(HTTPException) as exc_info:
            await get_authenticated_context(plain_key, db_session)
        
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_last_used_at_updated(
        self, db_session, tenant1, api_key_tenant1
    ):
        """Test that last_used_at is updated on successful authentication."""
        api_key, plain_key = api_key_tenant1
        
        # Initial last_used_at should be None
        assert api_key.last_used_at is None
        
        # Authenticate
        await get_authenticated_context(plain_key, db_session)
        
        # Refresh the api_key object
        await db_session.refresh(api_key)
        
        # last_used_at should now be set
        assert api_key.last_used_at is not None
        assert api_key.last_used_at <= datetime.now(timezone.utc)


class TestTenantIsolation:
    """Test multi-tenant isolation."""

    @pytest.mark.asyncio
    async def test_tenant1_cannot_access_tenant2_key(
        self, db_session, api_key_tenant1, api_key_tenant2
    ):
        """Test that tenant 1's key cannot authenticate as tenant 2."""
        _, plain_key_t1 = api_key_tenant1
        _, plain_key_t2 = api_key_tenant2
        
        # Authenticate with tenant 1 key
        context1 = await get_authenticated_context(plain_key_t1, db_session)
        assert context1.tenant_id == "tenant-1"
        
        # Authenticate with tenant 2 key
        context2 = await get_authenticated_context(plain_key_t2, db_session)
        assert context2.tenant_id == "tenant-2"
        
        # Keys should be completely separate
        assert context1.tenant_id != context2.tenant_id
        assert context1.api_key_id != context2.api_key_id

    @pytest.mark.asyncio
    async def test_keys_are_tenant_specific(
        self, db_session, tenant1, tenant2
    ):
        """Test that API keys are properly scoped to tenants."""
        # Create multiple keys for each tenant
        key1_t1, plain1_t1 = await create_api_key_for_tenant(
            db_session, tenant1.id, "T1 Key 1"
        )
        key2_t1, plain2_t1 = await create_api_key_for_tenant(
            db_session, tenant1.id, "T1 Key 2"
        )
        key1_t2, plain1_t2 = await create_api_key_for_tenant(
            db_session, tenant2.id, "T2 Key 1"
        )
        
        # All keys should authenticate to their respective tenants
        ctx1 = await get_authenticated_context(plain1_t1, db_session)
        ctx2 = await get_authenticated_context(plain2_t1, db_session)
        ctx3 = await get_authenticated_context(plain1_t2, db_session)
        
        assert ctx1.tenant_id == tenant1.id
        assert ctx2.tenant_id == tenant1.id
        assert ctx3.tenant_id == tenant2.id
