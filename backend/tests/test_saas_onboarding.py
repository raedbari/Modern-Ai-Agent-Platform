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
