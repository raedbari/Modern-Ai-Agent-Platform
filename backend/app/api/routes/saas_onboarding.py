
from backend.app.operations.saas_onboarding import (
    reject_application,
    request_application_changes,
    resend_verification,
)

from backend.app.api.schemas.saas_onboarding import (
    ResendVerificationRequest,
    ResendVerificationResponse,
    ReviewNoteRequest,
)
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import require_admin_access, require_permission
from backend.app.api.schemas.saas_onboarding import (
    ApprovalRequest,
    ResendVerificationRequest,
    ResendVerificationResponse,
    ReviewNoteRequest,
    SignupRequest,
    SignupResponse,
    TenantApplicationResponse,
    VerifyEmailRequest,
    VerifyEmailResponse,
)
from backend.app.auth.admin_context import AdminContext
from backend.app.core.client_ip import get_client_ip
from backend.app.core.config import Settings, get_settings
from backend.app.db.base import get_db
from backend.app.operations.saas_onboarding import (
    ApplicationNotFoundError,
    ApplicationStateConflictError,
    InvalidVerificationTokenError,
    OnboardingConflictError,
    approve_application,
    get_application,
    reject_application,
    request_application_changes,
    resend_verification,
    list_applications,
    signup_customer,
    verify_email,
)

router = APIRouter(tags=["saas-onboarding"])

def response_row(row) -> TenantApplicationResponse:
    application, user = row
    return TenantApplicationResponse(
        id=application.id,
        user_id=user.id,
        applicant_name=user.display_name,
        applicant_email=user.email,
        email_verified=user.email_verified_at is not None,
        company_name=application.company_name,
        requested_plan=application.requested_plan,
        status=application.status,
        submitted_at=application.submitted_at,
        reviewed_at=application.reviewed_at,
        reviewed_by=application.reviewed_by,
        review_note=application.review_note,
        approved_tenant_id=application.approved_tenant_id,
        created_at=application.created_at,
        updated_at=application.updated_at,
    )

@router.post("/api/saas/signup", response_model=SignupResponse, status_code=201)
async def signup(
    payload: SignupRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SignupResponse:
    try:
        application, raw_token = await signup_customer(
            session,
            name=payload.name,
            email=payload.email,
            company_name=payload.company_name,
            password=payload.password,
            requested_plan=payload.requested_plan,
            settings=settings,
            client_ip=get_client_ip(request, settings),
            user_agent=request.headers.get("User-Agent", "")[:512] or None,
        )
        await session.commit()
    except OnboardingConflictError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Signup conflict.") from exc

    return SignupResponse(
        status=application.status,
        verification_token=(raw_token if settings.environment in {"development", "test"} else None),
    )

@router.post("/api/saas/verify-email", response_model=VerifyEmailResponse)
async def verify_email_route(
    payload: VerifyEmailRequest,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> VerifyEmailResponse:
    try:
        application = await verify_email(session, raw_token=payload.token)
        await session.commit()
    except InvalidVerificationTokenError as exc:
        await session.rollback()
        raise HTTPException(status_code=400, detail="Verification token is invalid or expired.") from exc
    return VerifyEmailResponse(email_verified=True, status=application.status)

@router.get(
    "/api/admin/tenant-applications",
    response_model=list[TenantApplicationResponse],
    dependencies=[Depends(require_admin_access), Depends(require_permission("tenants:read"))],
)
async def admin_list_applications(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[TenantApplicationResponse]:
    return [response_row(row) for row in await list_applications(session)]

@router.post(
    "/api/admin/tenant-applications/{application_id}/approve",
    response_model=TenantApplicationResponse,
    dependencies=[Depends(require_permission("tenants:write"))],
)
async def admin_approve_application(
    application_id: str,
    payload: ApprovalRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    context: Annotated[AdminContext | None, Depends(require_admin_access)],
) -> TenantApplicationResponse:
    try:
        await approve_application(
            session,
            application_id=application_id,
            admin_id=context.admin_id if context is not None else None,
            review_note=payload.review_note,
            client_ip=get_client_ip(request, settings),
        )
        await session.commit()
        row = await get_application(session, application_id)
    except ApplicationNotFoundError as exc:
        await session.rollback()
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ApplicationStateConflictError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Approval conflict.") from exc
    return response_row(row)


@router.post(
    "/api/saas/resend-verification",
    response_model=ResendVerificationResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def resend_verification_route(
    payload: ResendVerificationRequest,
    session: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
    settings: Annotated[
        Settings,
        Depends(get_settings),
    ],
) -> ResendVerificationResponse:

    raw_token = await resend_verification(
        session,
        email=payload.email,
    )

    await session.commit()

    return ResendVerificationResponse(
        verification_token=(
            raw_token
            if (
                raw_token is not None
                and settings.environment
                in {"development", "test"}
            )
            else None
        )
    )


@router.post(
    "/api/admin/tenant-applications/"
    "{application_id}/request-changes",
    response_model=TenantApplicationResponse,
    dependencies=[
        Depends(require_permission("tenants:write"))
    ],
)
async def admin_request_changes(
    application_id: str,
    payload: ReviewNoteRequest,
    request: Request,
    session: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
    settings: Annotated[
        Settings,
        Depends(get_settings),
    ],
    context: Annotated[
        AdminContext | None,
        Depends(require_admin_access),
    ],
) -> TenantApplicationResponse:

    try:
        await request_application_changes(
            session,
            application_id=application_id,
            admin_id=(
                context.admin_id
                if context is not None
                else None
            ),
            review_note=payload.review_note,
            client_ip=get_client_ip(
                request,
                settings,
            ),
        )

        await session.commit()

        row = await get_application(
            session,
            application_id,
        )

    except ApplicationNotFoundError as exc:
        await session.rollback()

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except ApplicationStateConflictError as exc:
        await session.rollback()

        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    return response_row(row)


@router.post(
    "/api/admin/tenant-applications/"
    "{application_id}/reject",
    response_model=TenantApplicationResponse,
    dependencies=[
        Depends(require_permission("tenants:write"))
    ],
)
async def admin_reject_application(
    application_id: str,
    payload: ReviewNoteRequest,
    request: Request,
    session: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
    settings: Annotated[
        Settings,
        Depends(get_settings),
    ],
    context: Annotated[
        AdminContext | None,
        Depends(require_admin_access),
    ],
) -> TenantApplicationResponse:

    try:
        await reject_application(
            session,
            application_id=application_id,
            admin_id=(
                context.admin_id
                if context is not None
                else None
            ),
            review_note=payload.review_note,
            client_ip=get_client_ip(
                request,
                settings,
            ),
        )

        await session.commit()

        row = await get_application(
            session,
            application_id,
        )

    except ApplicationNotFoundError as exc:
        await session.rollback()

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except ApplicationStateConflictError as exc:
        await session.rollback()

        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    return response_row(row)


@router.post(
    "/api/admin/tenant-applications/{application_id}/request-changes",
    response_model=TenantApplicationResponse,
    dependencies=[Depends(require_permission("tenants:write"))],
)
async def admin_request_changes(
    application_id: str,
    payload: ReviewNoteRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    context: Annotated[
        AdminContext | None,
        Depends(require_admin_access),
    ],
) -> TenantApplicationResponse:
    try:
        await request_application_changes(
            session,
            application_id=application_id,
            admin_id=(
                context.admin_id
                if context is not None
                else None
            ),
            review_note=payload.review_note,
            client_ip=get_client_ip(request, settings),
        )

        await session.commit()

        row = await get_application(
            session,
            application_id,
        )

    except ApplicationNotFoundError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except ApplicationStateConflictError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    return response_row(row)


@router.post(
    "/api/admin/tenant-applications/{application_id}/reject",
    response_model=TenantApplicationResponse,
    dependencies=[Depends(require_permission("tenants:write"))],
)
async def admin_reject_application(
    application_id: str,
    payload: ReviewNoteRequest,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    context: Annotated[
        AdminContext | None,
        Depends(require_admin_access),
    ],
) -> TenantApplicationResponse:
    try:
        await reject_application(
            session,
            application_id=application_id,
            admin_id=(
                context.admin_id
                if context is not None
                else None
            ),
            review_note=payload.review_note,
            client_ip=get_client_ip(request, settings),
        )

        await session.commit()

        row = await get_application(
            session,
            application_id,
        )

    except ApplicationNotFoundError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except ApplicationStateConflictError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=409,
            detail=str(exc),
        ) from exc

    return response_row(row)
