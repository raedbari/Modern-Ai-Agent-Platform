"""PostgreSQL integration tests for immediate agent configuration."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from backend.app.ai.contracts import GenerationResult
from backend.app.api.dependencies import (
    get_core_ai_runtime,
    require_admin_access,
)
from backend.app.auth.api_keys import IssuedApiKey, issue_api_key
from backend.app.core.config import Settings, get_settings
from backend.app.db.base import get_db
from backend.app.db.models import (
    AdminAuditLog,
    Agent,
    ApiKey,
    Tenant,
)
from backend.app.main import create_app
from backend.app.services.audit import AuditService


TEST_DATABASE_URL = os.getenv("MAAP_TEST_DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="MAAP_TEST_DATABASE_URL is required.",
)


class RuntimeTestContext:
    def __init__(
        self,
        *,
        prefix: str,
        application: FastAPI,
        engine: AsyncEngine,
        sessions: async_sessionmaker[AsyncSession],
        runtime: AsyncMock,
    ) -> None:
        self.prefix = prefix
        self.application = application
        self.engine = engine
        self.sessions = sessions
        self.runtime = runtime


@pytest_asyncio.fixture
async def runtime_context() -> AsyncIterator[RuntimeTestContext]:
    assert TEST_DATABASE_URL is not None

    database_name = make_url(TEST_DATABASE_URL).database

    if database_name != "maap_review_test":
        raise RuntimeError(
            "Runtime configuration tests may run only against "
            "maap_review_test."
        )

    engine = create_async_engine(
        TEST_DATABASE_URL,
        pool_pre_ping=True,
    )

    sessions = async_sessionmaker(
        engine,
        expire_on_commit=False,
    )

    prefix = f"config-runtime-{uuid4().hex[:12]}"

    runtime = AsyncMock()
    runtime.generate.return_value = GenerationResult(
        content="Runtime response",
        model="runtime-test-model",
        finish_reason="stop",
        prompt_tokens=5,
        completion_tokens=3,
    )

    settings = Settings(
        environment="test",
        database_url=TEST_DATABASE_URL,
        redis_url=None,
        _env_file=None,
    )

    application = create_app()

    async def override_get_db():
        async with sessions() as session:
            yield session

    application.dependency_overrides[get_db] = override_get_db
    application.dependency_overrides[get_settings] = lambda: settings
    application.dependency_overrides[get_core_ai_runtime] = lambda: runtime

    # Permission checks remain present, but the test does not need to create
    # a complete JWT session merely to exercise transaction/runtime behavior.
    application.dependency_overrides[require_admin_access] = lambda: None

    context = RuntimeTestContext(
        prefix=prefix,
        application=application,
        engine=engine,
        sessions=sessions,
        runtime=runtime,
    )

    try:
        yield context
    finally:
        async with sessions() as session:
            await session.execute(
                delete(AdminAuditLog).where(
                    AdminAuditLog.target_id.like(f"{prefix}%")
                )
            )

            await session.execute(
                delete(Tenant).where(
                    Tenant.id.like(f"{prefix}%")
                )
            )

            await session.commit()

        await engine.dispose()


async def _seed_agent(
    context: RuntimeTestContext,
    *,
    system_prompt: str,
    knowledge_mode: str = "preferred",
    contact_message: str | None = None,
) -> tuple[str, str, IssuedApiKey]:
    tenant_id = f"{context.prefix}-tenant"
    agent_id = f"{context.prefix}-agent"
    issued = issue_api_key()

    async with context.sessions() as session:
        session.add(
            Tenant(
                id=tenant_id,
                name="Runtime test tenant",
            )
        )

        await session.flush()

        session.add_all(
            [
                Agent(
                    id=agent_id,
                    tenant_id=tenant_id,
                    name="Runtime test agent",
                    system_prompt=system_prompt,
                    knowledge_mode=knowledge_mode,
                    contact_message=contact_message,
                ),
                ApiKey(
                    tenant_id=tenant_id,
                    key_id=issued.key_id,
                    key_digest=issued.key_digest,
                    is_active=True,
                ),
            ]
        )

        await session.commit()

    return tenant_id, agent_id, issued


def _chat_headers(
    issued: IssuedApiKey,
    agent_id: str,
) -> dict[str, str]:
    return {
        "X-API-Key": issued.raw_key,
        "X-Agent-ID": agent_id,
    }


@pytest.mark.asyncio
async def test_admin_patch_prompt_is_used_by_next_chat_request(
    runtime_context: RuntimeTestContext,
) -> None:
    old_prompt = "OLD SYSTEM PROMPT"
    new_prompt = "NEW SYSTEM PROMPT USED IMMEDIATELY"

    tenant_id, agent_id, issued = await _seed_agent(
        runtime_context,
        system_prompt=old_prompt,
    )

    async with AsyncClient(
        transport=ASGITransport(
            app=runtime_context.application
        ),
        base_url="http://test",
    ) as client:
        update_response = await client.patch(
            (
                f"/api/admin/tenants/{tenant_id}"
                f"/agents/{agent_id}/config"
            ),
            json={
                "system_prompt": new_prompt,
                "knowledge_mode": "disabled",
            },
        )

        assert update_response.status_code == 200

        chat_response = await client.post(
            "/api/chat",
            json={
                "message":
                    "Which configuration is active now?"
            },
            headers=_chat_headers(
                issued,
                agent_id,
            ),
        )

    assert chat_response.status_code == 200
    assert chat_response.json()["reply"] == "Runtime response"

    generation_request = (
        runtime_context.runtime.generate.await_args.args[0]
    )

    messages = [
        (message.role, message.content)
        for message in generation_request.messages
    ]

    assert messages == [
        ("system", new_prompt),
        (
            "user",
            "Which configuration is active now?",
        ),
    ]

    assert old_prompt not in {
        message.content
        for message in generation_request.messages
    }

    async with runtime_context.sessions() as session:
        agent = await session.get(
            Agent,
            agent_id,
        )

        audit_count = await session.scalar(
            select(func.count())
            .select_from(AdminAuditLog)
            .where(
                AdminAuditLog.event_type
                == "agent_config_updated",
                AdminAuditLog.target_id == agent_id,
            )
        )

    assert agent is not None
    assert agent.system_prompt == new_prompt
    assert agent.knowledge_mode == "disabled"
    assert audit_count == 1


@pytest.mark.asyncio
async def test_contact_message_is_used_by_next_chat_request(
    runtime_context: RuntimeTestContext,
) -> None:
    new_contact_message = (
        "?? ???? ????? ?????. ????? ?? ????? ??????."
    )

    tenant_id, agent_id, issued = await _seed_agent(
        runtime_context,
        system_prompt="Original prompt",
        knowledge_mode="preferred",
        contact_message="Old contact message",
    )

    async with AsyncClient(
        transport=ASGITransport(
            app=runtime_context.application
        ),
        base_url="http://test",
    ) as client:
        update_response = await client.patch(
            (
                f"/api/admin/tenants/{tenant_id}"
                f"/agents/{agent_id}/config"
            ),
            json={
                "knowledge_mode": "required",
                "contact_message": new_contact_message,
            },
        )

        assert update_response.status_code == 200

        chat_response = await client.post(
            "/api/chat",
            json={
                "message":
                    "Question without indexed knowledge"
            },
            headers=_chat_headers(
                issued,
                agent_id,
            ),
        )

    assert chat_response.status_code == 200

    payload = chat_response.json()

    assert payload["reply"] == new_contact_message
    assert payload["answer_status"] == "insufficient_knowledge"
    assert payload["model"] == "platform-fallback"

    runtime_context.runtime.generate.assert_not_awaited()


@pytest.mark.asyncio
async def test_audit_failure_rolls_back_agent_configuration(
    runtime_context: RuntimeTestContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    old_prompt = "PROMPT BEFORE FAILED TRANSACTION"
    attempted_prompt = "THIS MUST NOT BE COMMITTED"

    tenant_id, agent_id, _ = await _seed_agent(
        runtime_context,
        system_prompt=old_prompt,
        knowledge_mode="preferred",
        contact_message="Original contact message",
    )

    failing_audit = AsyncMock(
        side_effect=RuntimeError(
            "forced audit transaction failure"
        )
    )

    monkeypatch.setattr(
        AuditService,
        "write",
        failing_audit,
    )

    async with AsyncClient(
        transport=ASGITransport(
            app=runtime_context.application,
            raise_app_exceptions=False,
        ),
        base_url="http://test",
    ) as client:
        response = await client.patch(
            (
                f"/api/admin/tenants/{tenant_id}"
                f"/agents/{agent_id}/config"
            ),
            json={
                "system_prompt": attempted_prompt,
                "knowledge_mode": "disabled",
                "contact_message": "Attempted contact message",
            },
        )

    assert response.status_code == 500
    failing_audit.assert_awaited_once()

    async with runtime_context.sessions() as session:
        agent = await session.get(
            Agent,
            agent_id,
        )

        audit_count = await session.scalar(
            select(func.count())
            .select_from(AdminAuditLog)
            .where(
                AdminAuditLog.event_type
                == "agent_config_updated",
                AdminAuditLog.target_id == agent_id,
            )
        )

    assert agent is not None
    assert agent.system_prompt == old_prompt
    assert agent.knowledge_mode == "preferred"
    assert agent.contact_message == "Original contact message"
    assert audit_count == 0
