"""Pydantic schemas for the admin authentication API."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


AdminRole = Literal["super_admin", "operator", "auditor"]


class LoginRequest(BaseModel):
    """Credentials submitted to the login endpoint."""

    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1)


class LoginResponse(BaseModel):
    """Tokens returned on successful authentication."""

    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int = Field(
        description="Access token lifetime in seconds.",
        gt=0,
    )
    admin_id: str
    role: str


class AdminProfileResponse(BaseModel):
    """Public profile returned by GET /api/admin/auth/me."""

    admin_id: str
    username: str
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None


class RefreshRequest(BaseModel):
    """Refresh token submitted to the refresh endpoint."""

    refresh_token: str = Field(min_length=1)


class LogoutRequest(BaseModel):
    """Refresh token submitted to the logout endpoint."""

    refresh_token: str = Field(min_length=1)


class ChangePasswordRequest(BaseModel):
    """Payload for POST /api/admin/auth/change-password."""

    current_password: str = Field(min_length=1)
    new_password: str = Field(
        min_length=12,
        description=(
            "Minimum 12 characters, at least one uppercase letter, "
            "one digit, and one special character."
        ),
    )


class CreateAdminRequest(BaseModel):
    """Payload for POST /api/admin/admins (super_admin only)."""

    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=12)
    role: AdminRole = "operator"


class AdminUserResponse(BaseModel):
    """Admin account metadata returned by management endpoints."""

    admin_id: str
    username: str
    role: str
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None


class RevokeAdminSessionsResponse(BaseModel):
    """Returned after force-revoking all sessions for one admin."""

    revoked_count: int = Field(ge=0)
