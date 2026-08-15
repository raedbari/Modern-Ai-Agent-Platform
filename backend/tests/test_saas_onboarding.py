from pathlib import Path
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, event, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.app.api.dependencies import require_admin_access
from backend.app.core.config import Settings, get_settings
from backend.app.db.base import Base, get_db
from backend.app.db.models import (
    AdminAuditLog,
    AdminUser,
    EmailVerificationToken,
    LegalAcceptance,
    Tenant,
    TenantApplication,
    TenantMembership,
    User,
)
from backend.app.main import create_app

from backend.app.auth.tenant_context import (
    TenantAuthError,
    validate_tenant_user_context,
)

PASSWORD = "StrongSignup99!"

async def open_app(path: Path):
    engine = create_async_engine(f"sqlite+aiosqlite:///{path.as_posix()}")
    @event.listens_for(engine.sync_engine, "connect")
    def fk_on(conn, _rec):
        cur = conn.cursor(); cur.execute("PRAGMA foreign_keys=ON"); cur.close()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    app = create_app()
    async def override_db():
        async with sessions() as session:
            yield session
    settings = Settings(
        environment="test",
        jwt_secret_key=(
            "athka-test-only-jwt-secret-"
            "0123456789abcdef0123456789abcdef"
            "0123456789abcdef0123456789abcdef"
        ),
        argon2_time_cost=1,
        argon2_memory_cost=8192,
        argon2_parallelism=1,
        _env_file=None,
    )
    context = SimpleNamespace(admin_id="admin-a", username="reviewer", role="super_admin", auth_method="legacy")
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[require_admin_access] = lambda: context
    async with sessions() as session:
        session.add(AdminUser(id="admin-a", username="reviewer", hashed_password="unused", role="super_admin", is_active=True))
        await session.commit()
    return app, engine, sessions

async def signup_verify(client: AsyncClient, email: str = "owner@example.com"):
    signup = await client.post("/api/saas/signup", json={
        "name": "Owner",
        "email": email,
        "company_name": "Athka Customer",
        "password": PASSWORD,
        "requested_plan": "starter",
        "legal_accepted": True,
    })
    assert signup.status_code == 201, signup.text
    token = signup.json()["verification_token"]
    assert token
    verified = await client.post("/api/saas/verify-email", json={"token": token})
    assert verified.status_code == 200, verified.text
    assert verified.json()["status"] == "under_review"

@pytest.mark.asyncio
async def test_signup_does_not_create_tenant_and_token_is_hashed(tmp_path):
    app, engine, sessions = await open_app(tmp_path / "signup.db")
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/saas/signup", json={
                "name": "Owner",
                "email": "OWNER@EXAMPLE.COM",
                "company_name": "Athka Customer",
                "password": PASSWORD,
                "requested_plan": "starter",
                "legal_accepted": True,
            })
        assert response.status_code == 201, response.text
        raw = response.json()["verification_token"]
        async with sessions() as session:
            user = await session.scalar(select(User))
            token = await session.scalar(select(EmailVerificationToken))
            tenants = await session.scalar(select(func.count()).select_from(Tenant))
            legal = await session.scalar(select(func.count()).select_from(LegalAcceptance))
        assert user.normalized_email == "owner@example.com"
        assert user.hashed_password != PASSWORD
        assert token.token_hash != raw
        assert tenants == 0
        assert legal == 3
    finally:
        await engine.dispose()

@pytest.mark.asyncio
async def test_verify_moves_application_under_review(tmp_path):
    app, engine, sessions = await open_app(tmp_path / "verify.db")
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await signup_verify(client)
        async with sessions() as session:
            user = await session.scalar(select(User))
            application = await session.scalar(select(TenantApplication))
        assert user.email_verified_at is not None
        assert application.status == "under_review"
    finally:
        await engine.dispose()

@pytest.mark.asyncio
async def test_approval_creates_tenant_owner_and_audit(tmp_path):
    app, engine, sessions = await open_app(tmp_path / "approve.db")
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await signup_verify(client)
            listed = await client.get("/api/admin/tenant-applications")
            assert listed.status_code == 200, listed.text
            application_id = listed.json()[0]["id"]
            approved = await client.post(
                f"/api/admin/tenant-applications/{application_id}/approve",
                json={"review_note": "Approved."},
            )
            assert approved.status_code == 200, approved.text
            tenant_id = approved.json()["approved_tenant_id"]
        async with sessions() as session:
            tenant = await session.get(Tenant, tenant_id)
            membership = await session.scalar(select(TenantMembership).where(TenantMembership.tenant_id == tenant_id))
            audit = await session.scalar(select(AdminAuditLog).where(AdminAuditLog.event_type == "tenant_application_approved"))
        assert tenant is not None
        assert membership.role == "tenant_owner"
        assert membership.status == "active"
        assert audit is not None
        assert audit.detail["tenant_id"] == tenant_id
    finally:
        await engine.dispose()

@pytest.mark.asyncio
async def test_missing_legal_acceptance_rolls_back_approval(tmp_path):
    app, engine, sessions = await open_app(tmp_path / "rollback.db")
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            await signup_verify(client, "rollback@example.com")
            listed = await client.get("/api/admin/tenant-applications")
            application_id = listed.json()[0]["id"]
            async with sessions() as session:
                await session.execute(delete(LegalAcceptance)); await session.commit()
            response = await client.post(f"/api/admin/tenant-applications/{application_id}/approve", json={})
            assert response.status_code == 409
        async with sessions() as session:
            tenants = await session.scalar(select(func.count()).select_from(Tenant))
            memberships = await session.scalar(select(func.count()).select_from(TenantMembership))
            application = await session.get(TenantApplication, application_id)
        assert tenants == 0
        assert memberships == 0
        assert application.status == "under_review"
        assert application.approved_tenant_id is None
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_resend_invalidates_previous_token(
    tmp_path,
):
    app, engine, sessions = await open_app(
        tmp_path / "resend.db"
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:

            first = await client.post(
                "/api/saas/signup",
                json={
                    "name": "Owner",
                    "email": "resend@example.com",
                    "company_name": "Resend Company",
                    "password": PASSWORD,
                    "requested_plan": "starter",
                    "legal_accepted": True,
                },
            )

            old_token = first.json()[
                "verification_token"
            ]

            resent = await client.post(
                "/api/saas/resend-verification",
                json={
                    "email": "resend@example.com"
                },
            )

            assert resent.status_code == 202

            new_token = resent.json()[
                "verification_token"
            ]

            assert new_token
            assert new_token != old_token

            old_result = await client.post(
                "/api/saas/verify-email",
                json={"token": old_token},
            )

            assert old_result.status_code == 400

            new_result = await client.post(
                "/api/saas/verify-email",
                json={"token": new_token},
            )

            assert new_result.status_code == 200

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_admin_request_changes(
    tmp_path,
):
    app, engine, sessions = await open_app(
        tmp_path / "changes.db"
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:

            await signup_verify(
                client,
                "changes@example.com",
            )

            listed = await client.get(
                "/api/admin/tenant-applications"
            )

            application_id = listed.json()[0]["id"]

            result = await client.post(
                "/api/admin/tenant-applications/"
                f"{application_id}/request-changes",
                json={
                    "review_note":
                        "Please update company details."
                },
            )

            assert result.status_code == 200
            assert (
                result.json()["status"]
                == "changes_requested"
            )

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_admin_reject_application(
    tmp_path,
):
    app, engine, sessions = await open_app(
        tmp_path / "reject.db"
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:

            await signup_verify(
                client,
                "reject@example.com",
            )

            listed = await client.get(
                "/api/admin/tenant-applications"
            )

            application_id = listed.json()[0]["id"]

            result = await client.post(
                "/api/admin/tenant-applications/"
                f"{application_id}/reject",
                json={
                    "review_note":
                        "Application rejected."
                },
            )

            assert result.status_code == 200
            assert (
                result.json()["status"]
                == "rejected"
            )
            assert (
                result.json()[
                    "approved_tenant_id"
                ]
                is None
            )

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_signup_uses_email_delivery_adapter(tmp_path, monkeypatch):
    app, engine, _sessions = await open_app(tmp_path / "email-delivery.db")
    sent = {}

    async def fake_send_verification_email(*, recipient, raw_token):
        sent["recipient"] = recipient
        sent["raw_token"] = raw_token
        return "http://example.test/verify-email"

    monkeypatch.setattr(
        "backend.app.api.routes.saas_onboarding.send_verification_email",
        fake_send_verification_email,
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/saas/signup",
                json={
                    "name": "Owner",
                    "email": "mail@example.com",
                    "company_name": "Mail Company",
                    "password": PASSWORD,
                    "requested_plan": "starter",
                    "legal_accepted": True,
                },
            )

        assert response.status_code == 201, response.text
        assert sent["recipient"] == "mail@example.com"
        assert sent["raw_token"].startswith("athka_verify_")
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_verified_pending_user_can_login_and_read_me(
    tmp_path,
):
    app, engine, _sessions = await open_app(
        tmp_path / "pending-login.db"
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            await signup_verify(
                client,
                "pending-login@example.com",
            )

            login = await client.post(
                "/api/v1/tenant-auth/login",
                json={
                    "email": "pending-login@example.com",
                    "password": PASSWORD,
                },
            )

            assert login.status_code == 200, login.text

            login_body = login.json()

            assert login_body["user_id"]
            assert login_body["tenant_id"] is None
            assert login_body["role"] is None
            assert login_body["access_token"]
            assert login_body["refresh_token"]

            me = await client.get(
                "/api/v1/tenant-auth/me",
                headers={
                    "Authorization": (
                        f"Bearer {login_body['access_token']}"
                    )
                },
            )

            assert me.status_code == 200, me.text

            profile = me.json()

            assert profile["email"] == (
                "pending-login@example.com"
            )

            assert profile["application"] is not None
            assert (
                profile["application"]["status"]
                == "under_review"
            )

            assert profile["membership"] is None

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_approved_user_login_resolves_tenant_owner(
    tmp_path,
):
    app, engine, _sessions = await open_app(
        tmp_path / "approved-login.db"
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            await signup_verify(
                client,
                "approved-login@example.com",
            )

            applications = await client.get(
                "/api/admin/tenant-applications"
            )

            assert applications.status_code == 200
            assert len(applications.json()) == 1

            application_id = applications.json()[0]["id"]

            approved = await client.post(
                (
                    "/api/admin/tenant-applications/"
                    f"{application_id}/approve"
                ),
                json={
                    "review_note": "Approved for tenant access."
                },
            )

            assert approved.status_code == 200, approved.text
            assert approved.json()["status"] == "approved"

            login = await client.post(
                "/api/v1/tenant-auth/login",
                json={
                    "email": "approved-login@example.com",
                    "password": PASSWORD,
                },
            )

            assert login.status_code == 200, login.text

            login_body = login.json()

            assert login_body["tenant_id"]
            assert login_body["role"] == "tenant_owner"

            me = await client.get(
                "/api/v1/tenant-auth/me",
                headers={
                    "Authorization": (
                        f"Bearer {login_body['access_token']}"
                    )
                },
            )

            assert me.status_code == 200, me.text

            profile = me.json()

            assert profile["application"] is not None
            assert (
                profile["application"]["status"]
                == "approved"
            )

            assert profile["membership"] is not None
            assert (
                profile["membership"]["tenant_id"]
                == login_body["tenant_id"]
            )
            assert (
                profile["membership"]["role"]
                == "tenant_owner"
            )

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_pending_user_has_no_tenant_authorization(
    tmp_path,
):
    app, engine, sessions = await open_app(
        tmp_path / "pending-tenant-auth.db"
    )

    settings = Settings(
        environment="test",
        jwt_secret_key=(
            "athka-test-only-jwt-secret-"
            "0123456789abcdef0123456789abcdef"
            "0123456789abcdef0123456789abcdef"
        ),
        argon2_time_cost=1,
        argon2_memory_cost=8192,
        argon2_parallelism=1,
        _env_file=None,
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            await signup_verify(
                client,
                "pending-authz@example.com",
            )

            login = await client.post(
                "/api/v1/tenant-auth/login",
                json={
                    "email": "pending-authz@example.com",
                    "password": PASSWORD,
                },
            )

            assert login.status_code == 200, login.text
            token = login.json()["access_token"]

        async with sessions() as session:
            with pytest.raises(TenantAuthError):
                await validate_tenant_user_context(
                    token,
                    session,
                    settings,
                )

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_tenant_authorization_uses_current_db_membership(
    tmp_path,
):
    app, engine, sessions = await open_app(
        tmp_path / "current-membership.db"
    )

    settings = Settings(
        environment="test",
        jwt_secret_key=(
            "athka-test-only-jwt-secret-"
            "0123456789abcdef0123456789abcdef"
            "0123456789abcdef0123456789abcdef"
        ),
        argon2_time_cost=1,
        argon2_memory_cost=8192,
        argon2_parallelism=1,
        _env_file=None,
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            await signup_verify(
                client,
                "current-role@example.com",
            )

            applications = await client.get(
                "/api/admin/tenant-applications"
            )

            application_id = applications.json()[0]["id"]

            approved = await client.post(
                (
                    "/api/admin/tenant-applications/"
                    f"{application_id}/approve"
                ),
                json={
                    "review_note": "Approved."
                },
            )

            assert approved.status_code == 200, approved.text

            login = await client.post(
                "/api/v1/tenant-auth/login",
                json={
                    "email": "current-role@example.com",
                    "password": PASSWORD,
                },
            )

            assert login.status_code == 200, login.text
            token = login.json()["access_token"]

        async with sessions() as session:
            context = await validate_tenant_user_context(
                token,
                session,
                settings,
            )

            assert context.role == "tenant_owner"

            membership = await session.get(
                TenantMembership,
                context.membership_id,
            )

            assert membership is not None

            membership.role = "tenant_admin"
            await session.commit()

        # Same JWT ? role must now come from current DB state.
        async with sessions() as session:
            context = await validate_tenant_user_context(
                token,
                session,
                settings,
            )

            assert context.role == "tenant_admin"

            membership = await session.get(
                TenantMembership,
                context.membership_id,
            )

            membership.status = "revoked"
            await session.commit()

        # Same JWT must immediately lose tenant authorization.
        async with sessions() as session:
            with pytest.raises(TenantAuthError):
                await validate_tenant_user_context(
                    token,
                    session,
                    settings,
                )

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_pending_user_refresh_and_logout(
    tmp_path,
):
    app, engine, _sessions = await open_app(
        tmp_path / "pending-session.db"
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            await signup_verify(
                client,
                "pending-session@example.com",
            )

            login = await client.post(
                "/api/v1/tenant-auth/login",
                json={
                    "email": "pending-session@example.com",
                    "password": PASSWORD,
                },
            )

            assert login.status_code == 200, login.text

            first = login.json()

            refresh = await client.post(
                "/api/v1/tenant-auth/refresh",
                json={
                    "refresh_token": first["refresh_token"],
                },
            )

            assert refresh.status_code == 200, refresh.text

            second = refresh.json()

            assert (
                second["refresh_token"]
                != first["refresh_token"]
            )
            assert second["tenant_id"] is None
            assert second["role"] is None

            logout = await client.post(
                "/api/v1/tenant-auth/logout",
                headers={
                    "Authorization": (
                        f"Bearer {second['access_token']}"
                    )
                },
                json={
                    "refresh_token": second["refresh_token"],
                },
            )

            assert logout.status_code == 200, logout.text

            after_logout = await client.post(
                "/api/v1/tenant-auth/refresh",
                json={
                    "refresh_token": second["refresh_token"],
                },
            )

            assert after_logout.status_code == 401

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_refresh_replay_revokes_session_family(
    tmp_path,
):
    app, engine, _sessions = await open_app(
        tmp_path / "refresh-replay.db"
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            await signup_verify(
                client,
                "replay@example.com",
            )

            login = await client.post(
                "/api/v1/tenant-auth/login",
                json={
                    "email": "replay@example.com",
                    "password": PASSWORD,
                },
            )

            assert login.status_code == 200, login.text

            first_refresh = login.json()["refresh_token"]

            rotated = await client.post(
                "/api/v1/tenant-auth/refresh",
                json={
                    "refresh_token": first_refresh,
                },
            )

            assert rotated.status_code == 200, rotated.text

            second_refresh = rotated.json()["refresh_token"]

            replay = await client.post(
                "/api/v1/tenant-auth/refresh",
                json={
                    "refresh_token": first_refresh,
                },
            )

            assert replay.status_code == 401

            family_after_replay = await client.post(
                "/api/v1/tenant-auth/refresh",
                json={
                    "refresh_token": second_refresh,
                },
            )

            assert family_after_replay.status_code == 401

    finally:
        await engine.dispose()


@pytest.mark.asyncio

@pytest.mark.asyncio
async def test_multiple_memberships_do_not_break_customer_auth(
    tmp_path,
):
    from uuid import uuid4

    app, engine, sessions = await open_app(
        tmp_path / "multi-membership.db"
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            await signup_verify(
                client,
                "multi@example.com",
            )

            applications = await client.get(
                "/api/admin/tenant-applications"
            )

            application_id = applications.json()[0]["id"]

            approved = await client.post(
                (
                    "/api/admin/tenant-applications/"
                    f"{application_id}/approve"
                ),
                json={
                    "review_note": "First tenant."
                },
            )

            assert approved.status_code == 200, approved.text

            first_login = await client.post(
                "/api/v1/tenant-auth/login",
                json={
                    "email": "multi@example.com",
                    "password": PASSWORD,
                },
            )

            assert first_login.status_code == 200
            user_id = first_login.json()["user_id"]

        # Seed a second tenant membership directly.
        # We are testing multi-membership authentication,
        # not a second onboarding application.
        second_tenant_id = str(uuid4())

        async with sessions() as session:
            session.add(
                Tenant(
                    id=second_tenant_id,
                    name="Athka Customer Two",
                    is_active=True,
                )
            )

            await session.flush()

            session.add(
                TenantMembership(
                    id=str(uuid4()),
                    user_id=user_id,
                    tenant_id=second_tenant_id,
                    role="tenant_admin",
                    status="active",
                )
            )

            await session.commit()

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            login = await client.post(
                "/api/v1/tenant-auth/login",
                json={
                    "email": "multi@example.com",
                    "password": PASSWORD,
                },
            )

            assert login.status_code == 200, login.text

            # Identity login must not guess which tenant to use.
            assert login.json()["tenant_id"] is None
            assert login.json()["role"] is None

            me = await client.get(
                "/api/v1/tenant-auth/me",
                headers={
                    "Authorization": (
                        f"Bearer {login.json()['access_token']}"
                    )
                },
            )

            assert me.status_code == 200, me.text

            # Multiple memberships require explicit tenant
            # selection later; /me must not choose arbitrarily.
            assert me.json()["membership"] is None

    finally:
        await engine.dispose()
