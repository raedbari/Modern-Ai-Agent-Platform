import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.admin_password import hash_admin_password
from backend.app.core.config import Settings
from backend.app.db.models import (
    EmailVerificationToken,
    LegalAcceptance,
    Tenant,
    TenantApplication,
    TenantMembership,
    User,
)
from backend.app.services.audit import AuditService

LEGAL_DOCUMENT_VERSIONS = {
    "terms_of_service": "terms-v1",
    "privacy_policy": "privacy-v1",
    "pricing_terms": "pricing-v1",
}

class OnboardingConflictError(RuntimeError):
    pass
class InvalidVerificationTokenError(RuntimeError):
    pass
class ApplicationNotFoundError(LookupError):
    pass
class ApplicationStateConflictError(RuntimeError):
    pass

def normalize_email(value: str) -> str:
    return value.strip().casefold()

def hash_token(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)

async def signup_customer(
    session: AsyncSession,
    *,
    name: str,
    email: str,
    company_name: str,
    password: str,
    requested_plan: str,
    settings: Settings,
    client_ip: str | None,
    user_agent: str | None,
) -> tuple[TenantApplication, str]:
    normalized = normalize_email(email)
    existing = await session.scalar(select(User.id).where(User.normalized_email == normalized))
    if existing is not None:
        raise OnboardingConflictError("An account already exists for this email.")

    now = datetime.now(timezone.utc)
    user = User(
        id=str(uuid4()),
        email=email.strip(),
        normalized_email=normalized,
        hashed_password=hash_admin_password(password, settings),
        display_name=name.strip(),
        is_active=True,
    )
    application = TenantApplication(
        id=str(uuid4()),
        user_id=user.id,
        company_name=company_name.strip(),
        requested_plan=requested_plan.strip().casefold(),
        status="email_pending",
        submitted_at=now,
    )
    session.add_all([user, application])
    await session.flush()

    for document_type, version in LEGAL_DOCUMENT_VERSIONS.items():
        session.add(
            LegalAcceptance(
                id=str(uuid4()),
                application_id=application.id,
                document_type=document_type,
                document_version=version,
                accepted_at=now,
                client_ip=client_ip,
                user_agent=user_agent,
            )
        )

    raw_token = "athka_verify_" + secrets.token_urlsafe(32)
    session.add(
        EmailVerificationToken(
            id=str(uuid4()),
            user_id=user.id,
            token_hash=hash_token(raw_token),
            expires_at=now + timedelta(hours=24),
            created_at=now,
        )
    )
    await session.flush()
    return application, raw_token

async def verify_email(session: AsyncSession, *, raw_token: str) -> TenantApplication:
    now = datetime.now(timezone.utc)
    token = await session.scalar(
        select(EmailVerificationToken)
        .where(EmailVerificationToken.token_hash == hash_token(raw_token))
        .with_for_update()
    )
    if token is None or token.used_at is not None or as_utc(token.expires_at) <= now:
        raise InvalidVerificationTokenError("Verification token is invalid or expired.")

    user = await session.get(User, token.user_id)
    if user is None or not user.is_active:
        raise InvalidVerificationTokenError("Verification token is invalid or expired.")

    application = await session.scalar(
        select(TenantApplication)
        .where(
            TenantApplication.user_id == user.id,
            TenantApplication.status == "email_pending",
        )
        .with_for_update()
    )
    if application is None:
        raise InvalidVerificationTokenError("Verification token is invalid or expired.")

    outstanding = list((await session.scalars(
        select(EmailVerificationToken).where(
            EmailVerificationToken.user_id == user.id,
            EmailVerificationToken.used_at.is_(None),
        )
    )).all())
    for item in outstanding:
        item.used_at = now

    user.email_verified_at = now
    application.status = "under_review"
    await session.flush()
    return application

async def list_applications(session: AsyncSession) -> list[tuple[TenantApplication, User]]:
    return list((await session.execute(
        select(TenantApplication, User)
        .join(User, User.id == TenantApplication.user_id)
        .order_by(TenantApplication.created_at.desc())
    )).all())

async def get_application(session: AsyncSession, application_id: str) -> tuple[TenantApplication, User]:
    row = (await session.execute(
        select(TenantApplication, User)
        .join(User, User.id == TenantApplication.user_id)
        .where(TenantApplication.id == application_id)
    )).one_or_none()
    if row is None:
        raise ApplicationNotFoundError("Tenant application not found.")
    return row

async def approve_application(
    session: AsyncSession,
    *,
    application_id: str,
    admin_id: str | None,
    review_note: str | None,
    client_ip: str | None,
) -> TenantApplication:
    application = await session.scalar(
        select(TenantApplication)
        .where(TenantApplication.id == application_id)
        .with_for_update()
    )
    if application is None:
        raise ApplicationNotFoundError("Tenant application not found.")
    if application.status != "under_review" or application.approved_tenant_id:
        raise ApplicationStateConflictError("Application cannot be approved in its current state.")

    user = await session.get(User, application.user_id)
    if user is None or not user.is_active or user.email_verified_at is None:
        raise ApplicationStateConflictError("Applicant must have an active verified account.")

    accepted = set((await session.scalars(
        select(LegalAcceptance.document_type).where(
            LegalAcceptance.application_id == application.id
        )
    )).all())
    if not set(LEGAL_DOCUMENT_VERSIONS).issubset(accepted):
        raise ApplicationStateConflictError("Required legal acceptances are incomplete.")

    tenant_id = str(uuid4())
    session.add(Tenant(id=tenant_id, name=application.company_name, is_active=True))
    session.add(TenantMembership(
        id=str(uuid4()),
        user_id=user.id,
        tenant_id=tenant_id,
        role="tenant_owner",
        status="active",
    ))
    application.status = "approved"
    application.approved_tenant_id = tenant_id
    application.reviewed_at = datetime.now(timezone.utc)
    application.reviewed_by = admin_id
    application.review_note = review_note.strip() if review_note else None

    await session.flush()
    await AuditService.write(
        session,
        event_type="tenant_application_approved",
        outcome="success",
        admin_id=admin_id,
        target_type="tenant_application",
        target_id=application.id,
        client_ip=client_ip,
        detail={"user_id": user.id, "tenant_id": tenant_id, "membership_role": "tenant_owner"},
    )
    await session.flush()
    return application
