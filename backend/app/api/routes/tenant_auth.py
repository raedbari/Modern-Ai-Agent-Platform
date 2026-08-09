"""Tenant authentication API endpoints."""
from __future__ import annotations

from typing import Annotated
from backend.app.api.dependencies import require_user_jwt

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import get_db, get_settings, require_tenant_user_jwt
from backend.app.api.schemas.tenant_auth import (
    TenantApplicationStatus,
    TenantAuthErrorResponse,
    TenantLoginRequest,
    TenantLoginResponse,
    TenantLogoutRequest,
    TenantMembershipContext,
    TenantRefreshRequest,
    TenantUserProfileResponse,
)
from backend.app.auth.tenant_context import TenantUserContext, UserContext
from backend.app.core.config import Settings
from backend.app.db.models import Tenant, TenantApplication, TenantMembership, User
from backend.app.operations.tenant_auth_ops import (
    InactiveUserError,
    InvalidCredentialsError,
    NoActiveMembershipError,
    ReplayDetectedError,
    SessionNotFoundError,
    UnverifiedEmailError,
    authenticate_tenant_user,
    revoke_session,
    rotate_refresh_token,
)

router = APIRouter(
    prefix="/api/v1/tenant-auth",
    tags=["Tenant Authentication"],
)


def _get_client_ip(request: Request) -> str | None:
    """Extract client IP from request headers or connection."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def _get_user_agent(request: Request) -> str | None:
    """Extract user agent from request headers."""
    return request.headers.get("User-Agent")


@router.post(
    "/login",
    response_model=TenantLoginResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": TenantAuthErrorResponse},
        429: {"model": TenantAuthErrorResponse},
    },
)
async def login(
    payload: TenantLoginRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TenantLoginResponse:
    """Authenticate a verified customer, even while approval is pending."""
    client_ip = _get_client_ip(request)
    user_agent = _get_user_agent(request)

    try:
        access_token, refresh_token = await authenticate_tenant_user(
            session,
            email=payload.email,
            plain_password=payload.password,
            settings=settings,
            client_ip=client_ip,
            user_agent=user_agent,
        )
        await session.commit()

        from backend.app.auth.tenant_jwt import decode_access_token
        token_payload = decode_access_token(access_token, settings)
        tenant_id = token_payload.get("tenant_id")
        role = None
        if isinstance(tenant_id, str) and tenant_id:
            membership = await session.scalar(
                select(TenantMembership).where(
                    TenantMembership.user_id == token_payload["sub"],
                    TenantMembership.tenant_id == tenant_id,
                    TenantMembership.status == "active",
                )
            )
            role = membership.role if membership else None

        return TenantLoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="Bearer",
            expires_in=settings.jwt_access_token_expire_minutes * 60,
            user_id=token_payload["sub"],
            tenant_id=tenant_id if isinstance(tenant_id, str) else None,
            role=role,
        )
    except (InvalidCredentialsError, UnverifiedEmailError, InactiveUserError) as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

@router.post(
    "/refresh",
    response_model=TenantLoginResponse,
    status_code=status.HTTP_200_OK,
    responses={
        401: {"model": TenantAuthErrorResponse},
    },
)
async def refresh(
    payload: TenantRefreshRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> TenantLoginResponse:
    """Rotate refresh token for customer identity sessions."""
    client_ip = _get_client_ip(request)
    user_agent = _get_user_agent(request)

    try:
        access_token, new_refresh_token = await rotate_refresh_token(
            session,
            raw_refresh_token=payload.refresh_token,
            settings=settings,
            client_ip=client_ip,
            user_agent=user_agent,
        )
        await session.commit()

        from backend.app.auth.tenant_jwt import decode_access_token
        token_payload = decode_access_token(access_token, settings)
        tenant_id = token_payload.get("tenant_id")
        role = None
        if isinstance(tenant_id, str) and tenant_id:
            membership = await session.scalar(
                select(TenantMembership).where(
                    TenantMembership.user_id == token_payload["sub"],
                    TenantMembership.tenant_id == tenant_id,
                    TenantMembership.status == "active",
                )
            )
            role = membership.role if membership else None

        return TenantLoginResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="Bearer",
            expires_in=settings.jwt_access_token_expire_minutes * 60,
            user_id=token_payload["sub"],
            tenant_id=tenant_id if isinstance(tenant_id, str) else None,
            role=role,
        )
    except (SessionNotFoundError, ReplayDetectedError, InactiveUserError) as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

@router.post(
    "/logout",
    status_code=status.HTTP_200_OK,
)
async def logout(
    payload: TenantLogoutRequest,
    ctx: Annotated[UserContext, Depends(require_user_jwt)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Revoke the current customer refresh session."""
    await revoke_session(
        session,
        raw_refresh_token=payload.refresh_token,
        user_id=ctx.user_id,
        family_id=ctx.session_family_id,
    )
    await session.commit()
    return {"detail": "Logged out successfully."}

@router.get(
    "/me",
    response_model=TenantUserProfileResponse,
    status_code=status.HTTP_200_OK,
)
async def me(
    ctx: Annotated[UserContext, Depends(require_user_jwt)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TenantUserProfileResponse:
    """Return customer identity plus current application/membership state."""
    user = await session.get(User, ctx.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    application = None
    app_record = await session.scalar(
        select(TenantApplication)
        .where(
            TenantApplication.user_id == user.id,
            TenantApplication.status.in_(
                ["under_review", "changes_requested", "approved", "rejected"]
            ),
        )
        .order_by(TenantApplication.created_at.desc())
        .limit(1)
    )
    if app_record is not None:
        application = TenantApplicationStatus(
            application_id=app_record.id,
            company_name=app_record.company_name,
            status=app_record.status,
            submitted_at=app_record.created_at,
        )

    membership_context = None
    membership_rows = (
        await session.execute(
            select(TenantMembership, Tenant)
            .join(Tenant, Tenant.id == TenantMembership.tenant_id)
            .where(
                TenantMembership.user_id == user.id,
                TenantMembership.status == "active",
                Tenant.is_active.is_(True),
            )
            .order_by(TenantMembership.created_at.asc())
            .limit(2)
        )
    ).all()
    if len(membership_rows) == 1:
        membership, tenant = membership_rows[0]
        membership_context = TenantMembershipContext(
            tenant_id=tenant.id,
            tenant_name=tenant.name,
            membership_id=membership.id,
            role=membership.role,
            status=membership.status,
            created_at=membership.created_at,
        )

    return TenantUserProfileResponse(
        user_id=user.id,
        email=user.email,
        display_name=user.display_name,
        is_active=user.is_active,
        email_verified_at=user.email_verified_at,
        created_at=user.created_at,
        last_login_at=user.last_login_at,
        application=application,
        membership=membership_context,
    )
