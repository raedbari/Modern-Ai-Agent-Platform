"""Integration tests for dual-auth Knowledge API (JWT Bearer + API Key)."""

from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)

from backend.app.ai.contracts import EmbeddingResult
from backend.app.api.dependencies import get_embedding_provider
from backend.app.auth.api_keys import IssuedApiKey, issue_api_key
from backend.app.auth.tenant_jwt import generate_tenant_user_jwt
from backend.app.core.config import Settings, get_settings
from backend.app.db.base import Base, get_db
from backend.app.db.models import (
    Agent,
    ApiKey,
    CustomerIdentity,
    KnowledgeBaseModel,
    RefreshSession,
    Tenant,
    TenantMembership,
    TenantUser,
)
from backend.app.main import create_app


async def _open_test_app(
    database_path: Path,
) -> tuple[
    FastAPI,
    AsyncEngine,
    async_sessionmaker,
    AsyncMock,
]:
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{database_path.as_posix()}",
    )

    @event.listens_for(engine.sync_engine, "connect")
    def enable_foreign_keys(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        engine,
        expire_on_commit=False,
    )
    runtime = AsyncMock()

    async def embed(request):
        return EmbeddingResult(
            embeddings=[
                [1.0] + [0.0] * 1023
                for _ in request.texts
            ],
            model="test-embedding",
            dimension=1024,
        )

    runtime.embed.side_effect = embed
    application = create_app()

    async def override_get_db():
        async with session_factory() as session:
            yield session

    application.dependency_overrides[get_db] = override_get_db
    application.dependency_overrides[get_embedding_provider] = lambda: runtime
    return application, engine, session_factory, runtime


async def _seed_tenant_with_jwt_user(
    session_factory: async_sessionmaker,
    *,
    tenant_id: str,
    user_id: str,
    role: str = "tenant_owner",
) -> tuple[str, str]:
    """Seed tenant, user, membership and return (jwt_token, session_id)."""
    settings = Settings(_env_file=None)
    
    async with session_factory() as session:
        # Create tenant
        session.add(Tenant(id=tenant_id, name=tenant_id))
        await session.flush()
        
        # Create customer identity
        identity = CustomerIdentity(
            id=f"identity-{user_id}",
            email=f"{user_id}@test.com",
            is_email_verified=True,
        )
        session.add(identity)
        await session.flush()
        
        # Create tenant user
        user = TenantUser(
            id=user_id,
            customer_identity_id=identity.id,
            display_name=user_id,
        )
        session.add(user)
        await session.flush()
        
        # Create refresh session
        refresh_session = RefreshSession(
            tenant_user_id=user_id,
            is_active=True,
        )
        session.add(refresh_session)
        await session.flush()
        
        # Create membership
        membership = TenantMembership(
            tenant_id=tenant_id,
            tenant_user_id=user_id,
            role=role,
            status="approved",
        )
        session.add(membership)
        await session.commit()
        
        session_id = refresh_session.id
    
    # Generate JWT
    jwt_token = generate_tenant_user_jwt(
        user_id=user_id,
        session_id=session_id,
        tenant_id=tenant_id,
        role=role,
        secret_key=settings.jwt_secret_key,
    )
    
    return jwt_token, session_id


async def _seed_tenant_with_api_key(
    session_factory: async_sessionmaker,
    *,
    tenant_id: str,
    agent_ids: tuple[str, ...],
) -> IssuedApiKey:
    """Seed tenant with API key (existing Phase 1 behavior)."""
    issued = issue_api_key()
    async with session_factory() as session:
        session.add(Tenant(id=tenant_id, name=tenant_id))
        await session.flush()
        session.add_all(
            Agent(
                id=agent_id,
                tenant_id=tenant_id,
                name=agent_id,
            )
            for agent_id in agent_ids
        )
        session.add(
            ApiKey(
                tenant_id=tenant_id,
                key_id=issued.key_id,
                key_digest=issued.key_digest,
            )
        )
        await session.commit()
    return issued


def _api_key_headers(issued: IssuedApiKey, agent_id: str) -> dict[str, str]:
    return {
        "X-API-Key": issued.raw_key,
        "X-Agent-ID": agent_id,
    }


def _jwt_bearer_headers(jwt_token: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {jwt_token}",
    }


async def _create_knowledge_base(
    client: AsyncClient,
    headers: dict[str, str],
    *,
    name: str = "Support",
) -> str:
    response = await client.post(
        "/api/knowledge-bases",
        headers=headers,
        json={"name": name, "description": "Tenant knowledge"},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


@pytest.mark.asyncio
async def test_jwt_bearer_can_create_knowledge_base(
    tmp_path: Path,
) -> None:
    """Test JWT Bearer auth works for creating knowledge base."""
    app, engine, session_factory, _ = await _open_test_app(
        tmp_path / "kb-jwt-create.sqlite3"
    )
    try:
        jwt_token, _ = await _seed_tenant_with_jwt_user(
            session_factory,
            tenant_id="tenant-jwt",
            user_id="user-owner",
            role="tenant_owner",
        )
        
        headers = _jwt_bearer_headers(jwt_token)
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/knowledge-bases",
                headers=headers,
                json={"name": "JWT KB", "description": "Created via JWT"},
            )
        
        assert response.status_code == 201, response.text
        assert response.json()["name"] == "JWT KB"
        assert response.json()["tenant_id"] == "tenant-jwt"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_jwt_bearer_can_list_knowledge_bases(
    tmp_path: Path,
) -> None:
    """Test JWT Bearer auth works for listing knowledge bases."""
    app, engine, session_factory, _ = await _open_test_app(
        tmp_path / "kb-jwt-list.sqlite3"
    )
    try:
        jwt_token, _ = await _seed_tenant_with_jwt_user(
            session_factory,
            tenant_id="tenant-jwt",
            user_id="user-owner",
            role="tenant_owner",
        )
        
        # Create KB via API key first
        issued = await _seed_tenant_with_api_key(
            session_factory,
            tenant_id="tenant-jwt",
            agent_ids=("agent-jwt",),
        )
        
        api_headers = _api_key_headers(issued, "agent-jwt")
        jwt_headers = _jwt_bearer_headers(jwt_token)
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            kb_id = await _create_knowledge_base(client, api_headers)
            
            # List via JWT
            response = await client.get(
                "/api/knowledge-bases",
                headers=jwt_headers,
            )
        
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["id"] == kb_id
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_jwt_bearer_can_get_knowledge_base(
    tmp_path: Path,
) -> None:
    """Test JWT Bearer auth works for getting single knowledge base."""
    app, engine, session_factory, _ = await _open_test_app(
        tmp_path / "kb-jwt-get.sqlite3"
    )
    try:
        jwt_token, _ = await _seed_tenant_with_jwt_user(
            session_factory,
            tenant_id="tenant-jwt",
            user_id="user-owner",
            role="tenant_owner",
        )
        
        jwt_headers = _jwt_bearer_headers(jwt_token)
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            kb_id = await _create_knowledge_base(client, jwt_headers)
            
            response = await client.get(
                f"/api/knowledge-bases/{kb_id}",
                headers=jwt_headers,
            )
        
        assert response.status_code == 200
        assert response.json()["id"] == kb_id
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_jwt_bearer_can_update_knowledge_base(
    tmp_path: Path,
) -> None:
    """Test JWT Bearer auth works for updating knowledge base."""
    app, engine, session_factory, _ = await _open_test_app(
        tmp_path / "kb-jwt-update.sqlite3"
    )
    try:
        jwt_token, _ = await _seed_tenant_with_jwt_user(
            session_factory,
            tenant_id="tenant-jwt",
            user_id="user-editor",
            role="knowledge_editor",
        )
        
        jwt_headers = _jwt_bearer_headers(jwt_token)
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            kb_id = await _create_knowledge_base(client, jwt_headers)
            
            response = await client.patch(
                f"/api/knowledge-bases/{kb_id}",
                headers=jwt_headers,
                json={"name": "Updated KB", "status": "inactive"},
            )
        
        assert response.status_code == 200
        assert response.json()["name"] == "Updated KB"
        assert response.json()["status"] == "inactive"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_jwt_bearer_can_delete_knowledge_base(
    tmp_path: Path,
) -> None:
    """Test JWT Bearer auth works for deleting knowledge base."""
    app, engine, session_factory, _ = await _open_test_app(
        tmp_path / "kb-jwt-delete.sqlite3"
    )
    try:
        jwt_token, _ = await _seed_tenant_with_jwt_user(
            session_factory,
            tenant_id="tenant-jwt",
            user_id="user-owner",
            role="tenant_owner",
        )
        
        jwt_headers = _jwt_bearer_headers(jwt_token)
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            kb_id = await _create_knowledge_base(client, jwt_headers)
            
            response = await client.delete(
                f"/api/knowledge-bases/{kb_id}",
                headers=jwt_headers,
            )
        
        assert response.status_code == 204
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_api_key_auth_still_works_regression(
    tmp_path: Path,
) -> None:
    """Test existing API Key auth still works (regression test)."""
    app, engine, session_factory, _ = await _open_test_app(
        tmp_path / "kb-api-key-regression.sqlite3"
    )
    try:
        issued = await _seed_tenant_with_api_key(
            session_factory,
            tenant_id="tenant-api",
            agent_ids=("agent-api",),
        )
        
        headers = _api_key_headers(issued, "agent-api")
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # Create
            create_resp = await client.post(
                "/api/knowledge-bases",
                headers=headers,
                json={"name": "API Key KB", "description": "Via API key"},
            )
            kb_id = create_resp.json()["id"]
            
            # List
            list_resp = await client.get(
                "/api/knowledge-bases",
                headers=headers,
            )
            
            # Get
            get_resp = await client.get(
                f"/api/knowledge-bases/{kb_id}",
                headers=headers,
            )
            
            # Update
            update_resp = await client.patch(
                f"/api/knowledge-bases/{kb_id}",
                headers=headers,
                json={"name": "Updated via API Key"},
            )
            
            # Delete
            delete_resp = await client.delete(
                f"/api/knowledge-bases/{kb_id}",
                headers=headers,
            )
        
        assert create_resp.status_code == 201
        assert list_resp.status_code == 200
        assert get_resp.status_code == 200
        assert update_resp.status_code == 200
        assert delete_resp.status_code == 204
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_jwt_cross_tenant_kb_access_returns_404(
    tmp_path: Path,
) -> None:
    """Test JWT user cannot access other tenant's knowledge base (returns 404)."""
    app, engine, session_factory, _ = await _open_test_app(
        tmp_path / "kb-jwt-cross-tenant.sqlite3"
    )
    try:
        # Tenant A with JWT user
        jwt_token_a, _ = await _seed_tenant_with_jwt_user(
            session_factory,
            tenant_id="tenant-a",
            user_id="user-a",
            role="tenant_owner",
        )
        
        # Tenant B with JWT user
        jwt_token_b, _ = await _seed_tenant_with_jwt_user(
            session_factory,
            tenant_id="tenant-b",
            user_id="user-b",
            role="tenant_owner",
        )
        
        headers_a = _jwt_bearer_headers(jwt_token_a)
        headers_b = _jwt_bearer_headers(jwt_token_b)
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # Tenant A creates KB
            kb_id = await _create_knowledge_base(client, headers_a)
            
            # Tenant B tries to access Tenant A's KB
            response = await client.get(
                f"/api/knowledge-bases/{kb_id}",
                headers=headers_b,
            )
        
        assert response.status_code == 404
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_jwt_role_permissions_knowledge_editor_can_manage(
    tmp_path: Path,
) -> None:
    """Test knowledge_editor role can manage knowledge bases."""
    app, engine, session_factory, _ = await _open_test_app(
        tmp_path / "kb-jwt-editor.sqlite3"
    )
    try:
        jwt_token, _ = await _seed_tenant_with_jwt_user(
            session_factory,
            tenant_id="tenant-jwt",
            user_id="user-editor",
            role="knowledge_editor",
        )
        
        headers = _jwt_bearer_headers(jwt_token)
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # Create
            create_resp = await client.post(
                "/api/knowledge-bases",
                headers=headers,
                json={"name": "Editor KB", "description": "Editor created"},
            )
            kb_id = create_resp.json()["id"]
            
            # Update
            update_resp = await client.patch(
                f"/api/knowledge-bases/{kb_id}",
                headers=headers,
                json={"name": "Editor Updated"},
            )
            
            # Delete
            delete_resp = await client.delete(
                f"/api/knowledge-bases/{kb_id}",
                headers=headers,
            )
        
        assert create_resp.status_code == 201
        assert update_resp.status_code == 200
        assert delete_resp.status_code == 204
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_jwt_role_permissions_conversation_viewer_read_only(
    tmp_path: Path,
) -> None:
    """Test conversation_viewer role has read-only access to knowledge bases."""
    app, engine, session_factory, _ = await _open_test_app(
        tmp_path / "kb-jwt-viewer.sqlite3"
    )
    try:
        # Owner creates KB
        jwt_owner, _ = await _seed_tenant_with_jwt_user(
            session_factory,
            tenant_id="tenant-jwt",
            user_id="user-owner",
            role="tenant_owner",
        )
        
        # Viewer has read-only access
        jwt_viewer, _ = await _seed_tenant_with_jwt_user(
            session_factory,
            tenant_id="tenant-jwt",
            user_id="user-viewer",
            role="conversation_viewer",
        )
        
        owner_headers = _jwt_bearer_headers(jwt_owner)
        viewer_headers = _jwt_bearer_headers(jwt_viewer)
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            # Owner creates KB
            kb_id = await _create_knowledge_base(client, owner_headers)
            
            # Viewer can read
            list_resp = await client.get(
                "/api/knowledge-bases",
                headers=viewer_headers,
            )
            get_resp = await client.get(
                f"/api/knowledge-bases/{kb_id}",
                headers=viewer_headers,
            )
            
            # Viewer cannot create
            create_resp = await client.post(
                "/api/knowledge-bases",
                headers=viewer_headers,
                json={"name": "Forbidden", "description": "Should fail"},
            )
            
            # Viewer cannot update
            update_resp = await client.patch(
                f"/api/knowledge-bases/{kb_id}",
                headers=viewer_headers,
                json={"name": "Forbidden Update"},
            )
            
            # Viewer cannot delete
            delete_resp = await client.delete(
                f"/api/knowledge-bases/{kb_id}",
                headers=viewer_headers,
            )
        
        assert list_resp.status_code == 200
        assert get_resp.status_code == 200
        assert create_resp.status_code == 403
        assert update_resp.status_code == 403
        assert delete_resp.status_code == 403
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_jwt_bearer_can_upload_document(
    tmp_path: Path,
) -> None:
    """Test JWT Bearer auth works for uploading documents."""
    app, engine, session_factory, _ = await _open_test_app(
        tmp_path / "kb-jwt-doc-upload.sqlite3"
    )
    try:
        jwt_token, _ = await _seed_tenant_with_jwt_user(
            session_factory,
            tenant_id="tenant-jwt",
            user_id="user-owner",
            role="tenant_owner",
        )
        
        headers = _jwt_bearer_headers(jwt_token)
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            kb_id = await _create_knowledge_base(client, headers)
            
            response = await client.post(
                f"/api/knowledge-bases/{kb_id}/documents",
                headers=headers,
                files={
                    "file": (
                        "guide.txt",
                        b"JWT uploaded document.",
                        "text/plain",
                    )
                },
            )
        
        assert response.status_code == 201
        assert response.json()["status"] == "ready"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_jwt_bearer_can_list_and_delete_documents(
    tmp_path: Path,
) -> None:
    """Test JWT Bearer auth works for listing and deleting documents."""
    app, engine, session_factory, _ = await _open_test_app(
        tmp_path / "kb-jwt-doc-ops.sqlite3"
    )
    try:
        jwt_token, _ = await _seed_tenant_with_jwt_user(
            session_factory,
            tenant_id="tenant-jwt",
            user_id="user-owner",
            role="tenant_owner",
        )
        
        headers = _jwt_bearer_headers(jwt_token)
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            kb_id = await _create_knowledge_base(client, headers)
            
            # Upload
            upload_resp = await client.post(
                f"/api/knowledge-bases/{kb_id}/documents",
                headers=headers,
                files={
                    "file": (
                        "doc.txt",
                        b"Document content.",
                        "text/plain",
                    )
                },
            )
            doc_id = upload_resp.json()["id"]
            
            # List
            list_resp = await client.get(
                f"/api/knowledge-bases/{kb_id}/documents",
                headers=headers,
            )
            
            # Get
            get_resp = await client.get(
                f"/api/knowledge-bases/{kb_id}/documents/{doc_id}",
                headers=headers,
            )
            
            # Delete
            delete_resp = await client.delete(
                f"/api/knowledge-bases/{kb_id}/documents/{doc_id}",
                headers=headers,
            )
        
        assert upload_resp.status_code == 201
        assert list_resp.status_code == 200
        assert len(list_resp.json()) == 1
        assert get_resp.status_code == 200
        assert delete_resp.status_code == 204
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_jwt_bearer_can_reindex_document(
    tmp_path: Path,
) -> None:
    """Test JWT Bearer auth works for reindexing documents."""
    app, engine, session_factory, _ = await _open_test_app(
        tmp_path / "kb-jwt-reindex.sqlite3"
    )
    try:
        jwt_token, _ = await _seed_tenant_with_jwt_user(
            session_factory,
            tenant_id="tenant-jwt",
            user_id="user-editor",
            role="knowledge_editor",
        )
        
        headers = _jwt_bearer_headers(jwt_token)
        
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            kb_id = await _create_knowledge_base(client, headers)
            
            # Upload
            upload_resp = await client.post(
                f"/api/knowledge-bases/{kb_id}/documents",
                headers=headers,
                files={
                    "file": (
                        "old.txt",
                        b"Old content.",
                        "text/plain",
                    )
                },
            )
            doc_id = upload_resp.json()["id"]
            
            # Reindex
            reindex_resp = await client.post(
                f"/api/knowledge-bases/{kb_id}/documents/{doc_id}/reindex",
                headers=headers,
                files={
                    "file": (
                        "new.txt",
                        b"New content.",
                        "text/plain",
                    )
                },
            )
        
        assert reindex_resp.status_code == 200
        assert reindex_resp.json()["id"] == doc_id
        assert reindex_resp.json()["original_filename"] == "new.txt"
    finally:
        await engine.dispose()
