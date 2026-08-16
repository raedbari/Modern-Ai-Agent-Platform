"""Platform-level Athkachatbots customer journey integration test."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.app.ai.contracts import EmbeddingResult, GenerationResult
from backend.app.ai.rerank import RerankRequest, RerankResult
from backend.app.api.dependencies import (
    get_core_ai_runtime,
    get_embedding_provider,
    get_rerank_provider,
    require_admin_access,
)
from backend.app.core.config import Settings, get_settings
from backend.app.core.rate_limit import RateLimitResult, get_rate_limiter
from backend.app.db.base import Base, get_db
from backend.app.db.models import (
    AdminUser,
    Agent,
    AgentKnowledgeBase,
    ChunkModel,
    Conversation,
    DocumentModel,
    Message,
    Tenant,
    TenantMembership,
)
from backend.app.main import create_app


PASSWORD = "StrongPlatform99!"
ORIGIN = "https://customer.example"
DOCUMENT_TEXT = (
    "Athka Premium support is available every day from 08:00 to 20:00 UTC."
)
GROUNDED_ANSWER = (
    "Athka Premium support is available daily from 08:00 to 20:00 UTC [S1]."
)


class DeterministicRuntime:
    """Deterministic substitute for DeepSeek and Voyage embedding boundaries."""

    def __init__(self) -> None:
        self.embedding_requests = []
        self.generation_requests = []

    async def embed(self, request):
        self.embedding_requests.append(request)
        return EmbeddingResult(
            embeddings=[[1.0] + [0.0] * 1023 for _ in request.texts],
            model="deterministic-voyage-boundary",
            dimension=1024,
        )

    async def generate(self, request):
        self.generation_requests.append(request)
        return GenerationResult(
            content=GROUNDED_ANSWER,
            model="deterministic-deepseek-boundary",
            finish_reason="stop",
            prompt_tokens=20,
            completion_tokens=12,
        )


class DeterministicReranker:
    """Deterministic substitute for the Voyage reranking boundary."""

    def __init__(self) -> None:
        self.requests: list[RerankRequest] = []

    async def rerank(self, request: RerankRequest) -> RerankResult:
        self.requests.append(request)
        return RerankResult(
            ranked_indices=list(range(min(request.top_k, len(request.documents)))),
            relevance_scores=[0.99] * min(request.top_k, len(request.documents)),
        )


class AllowingLimiter:
    async def check(self, **kwargs) -> RateLimitResult:
        return RateLimitResult(
            allowed=True,
            remaining=int(kwargs["limit"]),
            retry_after_seconds=int(kwargs["window_seconds"]),
        )


@pytest.mark.asyncio
async def test_complete_athkachatbots_customer_journey(
    tmp_path: Path,
) -> None:
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{(tmp_path / 'platform-e2e.sqlite3').as_posix()}"
    )

    @event.listens_for(engine.sync_engine, "connect")
    def enable_foreign_keys(connection, _record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    sessions = async_sessionmaker(engine, expire_on_commit=False)
    settings = Settings(
        environment="test",
        jwt_secret_key=(
            "platform-e2e-jwt-secret-"
            "0123456789abcdef0123456789abcdef"
            "0123456789abcdef0123456789abcdef"
        ),
        widget_jwt_secret_key="platform-e2e-widget-secret-key-0123456789abcdef",
        upload_storage_root=tmp_path / "uploads",
        argon2_time_cost=1,
        argon2_memory_cost=8192,
        argon2_parallelism=1,
        retrieval_min_similarity=0.5,
        _env_file=None,
    )
    runtime = DeterministicRuntime()
    reranker = DeterministicReranker()
    app = create_app()

    async def override_db():
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_embedding_provider] = lambda: runtime
    app.dependency_overrides[get_core_ai_runtime] = lambda: runtime
    app.dependency_overrides[get_rerank_provider] = lambda: reranker
    app.dependency_overrides[get_rate_limiter] = lambda: AllowingLimiter()
    app.dependency_overrides[require_admin_access] = lambda: SimpleNamespace(
        admin_id="platform-reviewer",
        username="reviewer",
        role="super_admin",
        auth_method="test",
    )

    async with sessions() as session:
        session.add(
            AdminUser(
                id="platform-reviewer",
                username="reviewer",
                hashed_password="unused",
                role="super_admin",
                is_active=True,
            )
        )
        await session.commit()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            signup = await client.post(
                "/api/saas/signup",
                json={
                    "name": "Platform Owner",
                    "email": "owner@platform.example",
                    "company_name": "Platform Customer",
                    "password": PASSWORD,
                    "requested_plan": "starter",
                    "legal_accepted": True,
                },
            )
            assert signup.status_code == 201, signup.text

            verification = await client.post(
                "/api/saas/verify-email",
                json={"token": signup.json()["verification_token"]},
            )
            assert verification.status_code == 200, verification.text
            assert verification.json()["status"] == "under_review"

            applications = await client.get("/api/admin/tenant-applications")
            assert applications.status_code == 200, applications.text
            application_id = applications.json()[0]["id"]
            approval = await client.post(
                f"/api/admin/tenant-applications/{application_id}/approve",
                json={"review_note": "Platform E2E approval"},
            )
            assert approval.status_code == 200, approval.text
            tenant_id = approval.json()["approved_tenant_id"]
            assert tenant_id

            login = await client.post(
                "/api/v1/tenant-auth/login",
                json={
                    "email": "owner@platform.example",
                    "password": PASSWORD,
                },
            )
            assert login.status_code == 200, login.text
            assert login.json()["tenant_id"] == tenant_id
            assert login.json()["role"] == "tenant_owner"
            bearer = {"Authorization": f"Bearer {login.json()['access_token']}"}

            agent_response = await client.post(
                "/api/customer/agents",
                headers=bearer,
                json={
                    "name": "Platform Support",
                    "knowledge_mode": "required",
                    "system_prompt": "Answer only from verified evidence.",
                },
            )
            assert agent_response.status_code == 201, agent_response.text
            agent_id = agent_response.json()["id"]
            knowledge_headers = {**bearer, "X-Agent-ID": agent_id}

            kb_response = await client.post(
                "/api/knowledge-bases",
                headers=knowledge_headers,
                json={"name": "Support policy", "description": "Controlled E2E data"},
            )
            assert kb_response.status_code == 201, kb_response.text
            knowledge_base_id = kb_response.json()["id"]

            upload = await client.post(
                f"/api/knowledge-bases/{knowledge_base_id}/documents",
                headers=knowledge_headers,
                data={"source_name": "support-hours.txt"},
                files={"file": ("support-hours.txt", DOCUMENT_TEXT, "text/plain")},
            )
            assert upload.status_code == 201, upload.text
            assert upload.json()["status"] == "ready"
            assert upload.json()["chunks_persisted"] >= 1
            document_id = upload.json()["id"]

            customer_chat = await client.post(
                "/api/chat",
                headers=knowledge_headers,
                json={"message": "When is Athka Premium support available?"},
            )
            assert customer_chat.status_code == 200, customer_chat.text
            customer_payload = customer_chat.json()
            assert customer_payload["answer_status"] == "grounded"
            assert customer_payload["reply"] == GROUNDED_ANSWER
            assert customer_payload["sources"] == [
                {
                    "citation_id": "S1",
                    "source_name": "support-hours.txt",
                    "document_id": document_id,
                    "page_number": 1,
                    "similarity_score": 0.99,
                }
            ]

            widget_settings = await client.put(
                f"/api/customer/agents/{agent_id}/widget-settings",
                headers=bearer,
                json={
                    "is_enabled": True,
                    "display_name": "Platform Support",
                    "greeting": "How can we help?",
                    "allowed_origins": [ORIGIN],
                },
            )
            assert widget_settings.status_code == 200, widget_settings.text
            widget_id = widget_settings.json()["public_widget_id"]

            bootstrap = await client.post(
                "/api/widget/bootstrap",
                headers={"Origin": ORIGIN},
                json={"widget_id": widget_id},
            )
            assert bootstrap.status_code == 200, bootstrap.text
            assert bootstrap.headers["Access-Control-Allow-Origin"] == ORIGIN

            widget_chat = await client.post(
                "/api/chat",
                headers={
                    "Origin": ORIGIN,
                    "Authorization": f"Bearer {bootstrap.json()['session_token']}",
                },
                json={"message": "What are the Premium support hours?"},
            )
            assert widget_chat.status_code == 200, widget_chat.text
            assert widget_chat.json()["answer_status"] == "grounded"
            assert widget_chat.json()["sources"][0]["document_id"] == document_id

        async with sessions() as session:
            tenant = await session.get(Tenant, tenant_id)
            membership = await session.scalar(
                select(TenantMembership).where(TenantMembership.tenant_id == tenant_id)
            )
            agent = await session.get(Agent, agent_id)
            assignment = await session.scalar(
                select(AgentKnowledgeBase).where(
                    AgentKnowledgeBase.tenant_id == tenant_id,
                    AgentKnowledgeBase.agent_id == agent_id,
                    AgentKnowledgeBase.knowledge_base_id == knowledge_base_id,
                )
            )
            document = await session.get(DocumentModel, document_id)
            chunks = list(
                (
                    await session.scalars(
                        select(ChunkModel).where(
                            ChunkModel.tenant_id == tenant_id,
                            ChunkModel.agent_id == agent_id,
                            ChunkModel.document_id == document_id,
                        )
                    )
                ).all()
            )
            conversations = list(
                (
                    await session.scalars(
                        select(Conversation).where(
                            Conversation.tenant_id == tenant_id,
                            Conversation.agent_id == agent_id,
                        )
                    )
                ).all()
            )
            messages = list(
                (
                    await session.scalars(
                        select(Message)
                        .join(
                            Conversation,
                            Conversation.id == Message.conversation_id,
                        )
                        .where(
                            Message.tenant_id == tenant_id,
                            Conversation.agent_id == agent_id,
                        )
                    )
                ).all()
            )

        assert tenant is not None
        assert membership is not None and membership.role == "tenant_owner"
        assert agent is not None and agent.tenant_id == tenant_id
        assert assignment is not None
        assert document is not None and document.status == "ready"
        assert chunks and all(chunk.tenant_id == tenant_id for chunk in chunks)
        assert len(conversations) == 2
        assert len(messages) == 4
        assistant_messages = [message for message in messages if message.role == "assistant"]
        assert len(assistant_messages) == 2
        assert all(
            message.metadata_json["answer_status"] == "grounded"
            and message.metadata_json["sources"][0]["document_id"] == document_id
            for message in assistant_messages
        )
        widget_conversation = next(
            conversation
            for conversation in conversations
            if (conversation.metadata_json or {}).get("auth_source") == "widget"
        )
        assert widget_conversation.metadata_json["widget_session_id"] == bootstrap.json()[
            "session_id"
        ]

        assert len(runtime.embedding_requests) == 3
        assert len(runtime.generation_requests) == 2
        assert len(reranker.requests) == 2
        assert all(request.documents for request in reranker.requests)
        assert all(DOCUMENT_TEXT in request.documents[0] for request in reranker.requests)
        assert all(
            request.context.tenant_id == tenant_id
            and request.context.agent_id == agent_id
            for request in runtime.embedding_requests
        )
        assert all(
            request.context.tenant_id == tenant_id
            and request.context.agent_id == agent_id
            for request in runtime.generation_requests
        )
    finally:
        await engine.dispose()
