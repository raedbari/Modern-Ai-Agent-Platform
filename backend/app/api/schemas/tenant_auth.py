"""Pydantic schemas for tenant authentication API."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class TenantLoginRequest(BaseModel):
    """Login request for tenant users."""
    
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=1, description="User password")


class TenantLoginResponse(BaseModel):
    """Login response with access and refresh tokens."""
    
    access_token: str = Field(..., description="JWT access token")
    refresh_token: str = Field(..., description="Opaque refresh token")
    token_type: Literal["Bearer"] = Field(default="Bearer", description="Token type")
    expires_in: int = Field(..., description="Access token expiry in seconds")
    user_id: str = Field(..., description="User ID")
    tenant_id: str = Field(..., description="Tenant ID")
    role: str = Field(..., description="User role in tenant")


class TenantRefreshRequest(BaseModel):
    """Refresh token rotation request."""
    
    refresh_token: str = Field(..., min_length=1, description="Current refresh token")


class TenantLogoutRequest(BaseModel):
    """Logout request to revoke session."""
    
    refresh_token: str = Field(..., min_length=1, description="Refresh token to revoke")


class TenantApplicationStatus(BaseModel):
    """Tenant application status for pending users."""
    
    application_id: str = Field(..., description="Application ID")
    company_name: str = Field(..., description="Company name from application")
    status: Literal["under_review", "changes_requested"] = Field(..., description="Application status")
    submitted_at: datetime = Field(..., description="Application submission timestamp")


class TenantMembershipContext(BaseModel):
    """Active tenant membership information."""
    
    tenant_id: str = Field(..., description="Tenant ID")
    tenant_name: str = Field(..., description="Tenant name")
    membership_id: str = Field(..., description="Membership ID")
    role: str = Field(..., description="User role in tenant")
    status: Literal["active"] = Field(..., description="Membership status")
    created_at: datetime = Field(..., description="Membership creation timestamp")


class TenantUserProfileResponse(BaseModel):
    """User profile response with optional application and membership."""
    
    user_id: str = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    display_name: str | None = Field(None, description="User display name")
    is_active: bool = Field(..., description="User active status")
    email_verified_at: datetime | None = Field(None, description="Email verification timestamp")
    created_at: datetime = Field(..., description="Account creation timestamp")
    last_login_at: datetime | None = Field(None, description="Last login timestamp")
    
    # Optional fields based on user state
    application: TenantApplicationStatus | None = Field(None, description="Pending application if exists")
    membership: TenantMembershipContext | None = Field(None, description="Active membership if exists")


class TenantAuthErrorResponse(BaseModel):
    """Error response for authentication failures."""
    
    detail: str = Field(..., description="Error message")
    error_code: str | None = Field(None, description="Optional error code for client handling")
