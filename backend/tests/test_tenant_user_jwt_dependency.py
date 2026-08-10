"""Tests for require_tenant_user_jwt FastAPI dependency exception mapping."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from backend.app.api.dependencies import require_tenant_user_jwt
from backend.app.auth.tenant_context import (
    InactiveTenantError,
    InactiveUserError,
    InvalidSessionError,
    InvalidTokenError,
    NoActiveMembershipError,
    TenantUserContext,
)
from backend.app.core.config import Settings


@pytest.mark.asyncio
async def test_require_tenant_user_jwt_missing_credentials():
    """Test that missing credentials returns 401."""
    request = Mock()
    credentials = None
    session = AsyncMock()
    settings = Settings(_env_file=None)
    
    with pytest.raises(HTTPException) as exc_info:
        await require_tenant_user_jwt(request, credentials, session, settings)
    
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Missing customer access token" in exc_info.value.detail


@pytest.mark.asyncio
async def test_require_tenant_user_jwt_empty_credentials():
    """Test that empty token string returns 401."""
    request = Mock()
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="   ")
    session = AsyncMock()
    settings = Settings(_env_file=None)
    
    with pytest.raises(HTTPException) as exc_info:
        await require_tenant_user_jwt(request, credentials, session, settings)
    
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Invalid customer access token" in exc_info.value.detail


@pytest.mark.asyncio
async def test_require_tenant_user_jwt_invalid_token_error_returns_401(monkeypatch):
    """Test that InvalidTokenError from validation returns 401."""
    from backend.app.auth import tenant_context
    
    async def mock_validate(*args, **kwargs):
        raise InvalidTokenError("JWT signature invalid")
    
    monkeypatch.setattr(tenant_context, "validate_tenant_user_context", mock_validate)
    
    request = Mock()
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="fake-token")
    session = AsyncMock()
    settings = Settings(_env_file=None)
    
    with pytest.raises(HTTPException) as exc_info:
        await require_tenant_user_jwt(request, credentials, session, settings)
    
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "JWT signature invalid" in exc_info.value.detail


@pytest.mark.asyncio
async def test_require_tenant_user_jwt_inactive_user_error_returns_401(monkeypatch):
    """Test that InactiveUserError from validation returns 401."""
    from backend.app.auth import tenant_context
    
    async def mock_validate(*args, **kwargs):
        raise InactiveUserError("User account is inactive")
    
    monkeypatch.setattr(tenant_context, "validate_tenant_user_context", mock_validate)
    
    request = Mock()
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="fake-token")
    session = AsyncMock()
    settings = Settings(_env_file=None)
    
    with pytest.raises(HTTPException) as exc_info:
        await require_tenant_user_jwt(request, credentials, session, settings)
    
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "User account is inactive" in exc_info.value.detail


@pytest.mark.asyncio
async def test_require_tenant_user_jwt_invalid_session_error_returns_401(monkeypatch):
    """Test that InvalidSessionError from validation returns 401."""
    from backend.app.auth import tenant_context
    
    async def mock_validate(*args, **kwargs):
        raise InvalidSessionError("Session has expired")
    
    monkeypatch.setattr(tenant_context, "validate_tenant_user_context", mock_validate)
    
    request = Mock()
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="fake-token")
    session = AsyncMock()
    settings = Settings(_env_file=None)
    
    with pytest.raises(HTTPException) as exc_info:
        await require_tenant_user_jwt(request, credentials, session, settings)
    
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "Session has expired" in exc_info.value.detail


@pytest.mark.asyncio
async def test_require_tenant_user_jwt_no_active_membership_error_returns_403(monkeypatch):
    """Test that NoActiveMembershipError from validation returns 403 (authorization failure)."""
    from backend.app.auth import tenant_context
    
    async def mock_validate(*args, **kwargs):
        raise NoActiveMembershipError("No active membership found")
    
    monkeypatch.setattr(tenant_context, "validate_tenant_user_context", mock_validate)
    
    request = Mock()
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="fake-token")
    session = AsyncMock()
    settings = Settings(_env_file=None)
    
    with pytest.raises(HTTPException) as exc_info:
        await require_tenant_user_jwt(request, credentials, session, settings)
    
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert "No active membership found" in exc_info.value.detail


@pytest.mark.asyncio
async def test_require_tenant_user_jwt_inactive_tenant_error_returns_403(monkeypatch):
    """Test that InactiveTenantError from validation returns 403 (authorization failure)."""
    from backend.app.auth import tenant_context
    
    async def mock_validate(*args, **kwargs):
        raise InactiveTenantError("Tenant is inactive")
    
    monkeypatch.setattr(tenant_context, "validate_tenant_user_context", mock_validate)
    
    request = Mock()
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="fake-token")
    session = AsyncMock()
    settings = Settings(_env_file=None)
    
    with pytest.raises(HTTPException) as exc_info:
        await require_tenant_user_jwt(request, credentials, session, settings)
    
    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert "Tenant is inactive" in exc_info.value.detail


@pytest.mark.asyncio
async def test_require_tenant_user_jwt_success_returns_context(monkeypatch):
    """Test that successful validation returns TenantUserContext."""
    from backend.app.auth import tenant_context
    
    expected_context = TenantUserContext(
        user_id=str(uuid.uuid4()),
        email="test@example.com",
        display_name="Test User",
        tenant_id=str(uuid.uuid4()),
        membership_id=str(uuid.uuid4()),
        role="tenant_admin",
        auth_method="jwt",
        session_family_id=str(uuid.uuid4()),
        jti=str(uuid.uuid4()),
    )
    
    async def mock_validate(*args, **kwargs):
        return expected_context
    
    monkeypatch.setattr(tenant_context, "validate_tenant_user_context", mock_validate)
    
    request = Mock()
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="fake-token")
    session = AsyncMock()
    settings = Settings(_env_file=None)
    
    result = await require_tenant_user_jwt(request, credentials, session, settings)
    
    assert result == expected_context
    assert result.user_id == expected_context.user_id
    assert result.tenant_id == expected_context.tenant_id
    assert result.role == "tenant_admin"
