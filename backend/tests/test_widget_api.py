"""Integration tests for Widget bootstrap, CORS, dual auth and isolation."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)

from backend.app.ai.contracts import GenerationResult
from backend.app.api.dependencies import get_core_ai_runtime
from backend.app.api.dependencies import require_tenant_user_jwt
from backend.app.auth.tenant_context import TenantUserContext
from backend.app.auth.widget_jwt import (
    create_widget_token,
    decode_widget_token,
)
from backend.app.core.config import Settings, get_settings
from backend.app.core.rate_limit import (
    RateLimitResult,
    get_rate_limiter,
)
from backend.app.db.base import Base, get_db
from backend.app.db.models import (
    Agent,
    AgentWidgetSettings,
    Conversation,
    Tenant,
    WidgetAllowedOrigin,
    WidgetConnectorPairing,
)
from backend.app.main import create_app
from backend.app.operations.widget_pairing import pairing_code_digest


_WIDGET_ID = "wgt_customer_widget_identifier_1234"
_ORIGIN = "https://customer.example"
_WIDGET_SECRET = "widget-api-test-secret-key-with-at-least-32-bytes!"


def _tenant_context(tenant_id: str = "tenant-a") -> TenantUserContext:
    return TenantUserContext(
        user_id="user-a",
        email="owner@example.test",
        display_name="Owner",
        tenant_id=tenant_id,
        membership_id="membership-a",
        role="tenant_owner",
        auth_method="jwt",
        session_family_id="family-a",
        jti="jti-a",
    )


class AllowingLimiter:
    async def check(self, **kwargs) -> RateLimitResult:
        return RateLimitResult(
            allowed=True,
            remaining=int(kwargs["limit"]),
            retry_after_seconds=int(kwargs["window_seconds"]),
        )


async def _open_widget_app(
    db_path: Path,
) -> tuple[
    FastAPI,
    AsyncEngine,
    async_sessionmaker,
    AsyncMock,
    Settings,
]:
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path.as_posix()}"
    )

    @event.listens_for(engine.sync_engine, "connect")
    def enable_fk(dbapi_conn, _rec):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    sessions = async_sessionmaker(engine, expire_on_commit=False)
    runtime = AsyncMock()
    runtime.generate.return_value = GenerationResult(
        content="Widget assistant response",
        model="test-widget-model",
        finish_reason="stop",
        prompt_tokens=5,
        completion_tokens=3,
    )
    settings = Settings(
        environment="test",
        widget_jwt_secret_key=_WIDGET_SECRET,
        widget_token_lifetime_seconds=600,
        _env_file=None,
    )
    app = create_app()

    async def override_db():
        async with sessions() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_settings] = lambda: settings
    app.dependency_overrides[get_rate_limiter] = lambda: AllowingLimiter()
    app.dependency_overrides[get_core_ai_runtime] = lambda: runtime
    return app, engine, sessions, runtime, settings


async def _seed_widget(
    sessions: async_sessionmaker,
    *,
    widget_id: str = _WIDGET_ID,
    origin: str = _ORIGIN,
    tenant_active: bool = True,
    agent_active: bool = True,
    widget_enabled: bool = True,
) -> None:
    async with sessions() as session:
        session.add_all(
            [
                Tenant(
                    id="tenant-a",
                    name="Tenant A",
                    is_active=tenant_active,
                ),
                Agent(
                    id="agent-a",
                    tenant_id="tenant-a",
                    name="Support Agent",
                    system_prompt="PRIVATE SYSTEM PROMPT - NEVER PUBLIC",
                    is_active=agent_active,
                ),
            ]
        )
        await session.commit()
        session.add(
            AgentWidgetSettings(
                tenant_id="tenant-a",
                agent_id="agent-a",
                public_widget_id=widget_id,
                is_enabled=widget_enabled,
                display_name="Public Support",
                greeting="Hello from the configured greeting.",
                primary_color="#112233",
                text_color="#FFFFFF",
                launcher_color="#223344",
                header_color="#334455",
                user_message_color="#445566",
                position="left",
                appearance="dark",
            )
        )
        await session.commit()
        session.add(
            WidgetAllowedOrigin(
                tenant_id="tenant-a",
                agent_id="agent-a",
                origin=origin,
            )
        )
        await session.commit()


async def _seed_pairing(
    sessions: async_sessionmaker,
    *,
    pairing_code: str = "ATK-TEST-PAIR-CODE-0001",
    origin: str = _ORIGIN,
    connector_type: str = "wordpress",
    expired: bool = False,
) -> str:
    pairing_id = str(uuid4())
    now = datetime.now(timezone.utc)

    async with sessions() as session:
        session.add(
            WidgetConnectorPairing(
                id=pairing_id,
                tenant_id="tenant-a",
                agent_id="agent-a",
                origin=origin,
                connector_type=connector_type,
                code_digest=pairing_code_digest(
                    pairing_code,
                ),
                expires_at=(
                    now - timedelta(minutes=1)
                    if expired
                    else now + timedelta(minutes=10)
                ),
                used_at=None,
                connected_at=None,
                created_by_admin_id=None,
            )
        )
        await session.commit()

    return pairing_id


async def _bootstrap(
    client: AsyncClient,
    *,
    origin: str = _ORIGIN,
) -> tuple[str, dict]:
    response = await client.post(
        "/api/widget/bootstrap",
        json={"widget_id": _WIDGET_ID},
        headers={"Origin": origin},
    )
    assert response.status_code == 200, response.text
    return response.json()["session_token"], response.json()


@pytest.mark.asyncio
async def test_bootstrap_returns_only_safe_runtime_configuration(
    tmp_path: Path,
) -> None:
    app, engine, sessions, _, settings = await _open_widget_app(
        tmp_path / "bootstrap.sqlite3"
    )
    await _seed_widget(sessions)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/widget/bootstrap",
                json={"widget_id": _WIDGET_ID},
                headers={"Origin": _ORIGIN},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["widget"]["display_name"] == "Public Support"
        assert body["widget"]["greeting"] == (
            "Hello from the configured greeting."
        )
        assert body["widget"]["theme"] == {
            "primaryColor": "#112233",
            "textColor": "#FFFFFF",
            "launcherColor": "#223344",
            "headerColor": "#334455",
            "userMessageColor": "#445566",
            "position": "left",
            "appearance": "dark",
        }
        assert "PRIVATE SYSTEM PROMPT" not in response.text
        assert response.headers["Access-Control-Allow-Origin"] == _ORIGIN
        assert response.headers["Cache-Control"] == "no-store"

        token_context = decode_widget_token(body["session_token"], settings)
        assert token_context.session_id == body["session_id"]
        assert token_context.tenant_id == "tenant-a"
        assert token_context.agent_id == "agent-a"
        assert token_context.origin == _ORIGIN
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_bootstrap_rejects_missing_and_unlisted_origins(
    tmp_path: Path,
) -> None:
    app, engine, sessions, _, _ = await _open_widget_app(
        tmp_path / "origin-reject.sqlite3"
    )
    await _seed_widget(sessions)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            missing = await client.post(
                "/api/widget/bootstrap",
                json={"widget_id": _WIDGET_ID},
            )
            unlisted = await client.post(
                "/api/widget/bootstrap",
                json={"widget_id": _WIDGET_ID},
                headers={"Origin": "https://attacker.example"},
            )

        assert missing.status_code == 403
        assert unlisted.status_code == 403
        assert "Access-Control-Allow-Origin" not in unlisted.headers
    finally:
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tenant_active,agent_active,widget_enabled",
    [
        (False, True, True),
        (True, False, True),
        (True, True, False),
    ],
)
async def test_bootstrap_hides_disabled_resource_state(
    tmp_path: Path,
    tenant_active: bool,
    agent_active: bool,
    widget_enabled: bool,
) -> None:
    app, engine, sessions, _, _ = await _open_widget_app(
        tmp_path
        / f"disabled-{tenant_active}-{agent_active}-{widget_enabled}.sqlite3"
    )
    await _seed_widget(
        sessions,
        tenant_active=tenant_active,
        agent_active=agent_active,
        widget_enabled=widget_enabled,
    )
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/widget/bootstrap",
                json={"widget_id": _WIDGET_ID},
                headers={"Origin": _ORIGIN},
            )
        assert response.status_code == 404
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_customer_preview_allows_disabled_widget_without_public_exposure(
    tmp_path: Path,
) -> None:
    app, engine, sessions, _, settings = await _open_widget_app(
        tmp_path / "customer-preview.sqlite3"
    )
    await _seed_widget(sessions, widget_enabled=False)
    app.dependency_overrides[require_tenant_user_jwt] = _tenant_context
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            public = await client.post(
                "/api/widget/bootstrap",
                json={"widget_id": _WIDGET_ID},
                headers={"Origin": _ORIGIN},
            )
            preview = await client.post(
                "/api/customer/agents/agent-a/widget-settings/preview/bootstrap",
                headers={"Origin": _ORIGIN},
            )
            assert public.status_code == 404
            assert preview.status_code == 200, preview.text
            token = preview.json()["session_token"]
            assert decode_widget_token(token, settings).token_type == "widget_preview_session"

            chat = await client.post(
                "/api/chat",
                json={"message": "Hello"},
                headers={"Authorization": f"Bearer {token}", "Origin": _ORIGIN},
            )
            mismatch = await client.post(
                "/api/chat",
                json={"message": "Hello"},
                headers={"Authorization": f"Bearer {token}", "Origin": "https://attacker.example"},
            )

        assert chat.status_code == 200, chat.text
        assert mismatch.status_code == 403
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_customer_preview_and_pairing_hide_cross_tenant_resources(
    tmp_path: Path,
) -> None:
    app, engine, sessions, _, _ = await _open_widget_app(
        tmp_path / "customer-widget-cross-tenant.sqlite3"
    )
    await _seed_widget(sessions)
    pairing_id = await _seed_pairing(sessions)
    app.dependency_overrides[require_tenant_user_jwt] = lambda: _tenant_context("tenant-b")
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            preview = await client.post(
                "/api/customer/agents/agent-a/widget-settings/preview/bootstrap",
                headers={"Origin": _ORIGIN},
            )
            pairing = await client.post(
                "/api/customer/agents/agent-a/widget-settings/pairings",
                json={"origin": _ORIGIN, "connector_type": "custom"},
            )
            installation = await client.get(
                "/api/customer/agents/agent-a/widget-settings/installation",
                params={"pairing_id": pairing_id},
            )
        assert preview.status_code == 404
        assert pairing.status_code == 404
        assert installation.status_code == 404
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_customer_pairing_uses_existing_digest_only_service(
    tmp_path: Path,
) -> None:
    app, engine, sessions, _, _ = await _open_widget_app(
        tmp_path / "customer-pairing.sqlite3"
    )
    await _seed_widget(sessions)
    app.dependency_overrides[require_tenant_user_jwt] = _tenant_context
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/customer/agents/agent-a/widget-settings/pairings",
                json={"origin": _ORIGIN, "connector_type": "custom"},
            )
        assert response.status_code == 201, response.text
        pairing_code = response.json()["pairing_code"]
        assert response.json()["expires_in"] == 600
        async with sessions() as session:
            pairing = await session.scalar(
                select(WidgetConnectorPairing).where(
                    WidgetConnectorPairing.id == response.json()["pairing_id"]
                )
            )
            assert pairing is not None
            assert pairing.code_digest == pairing_code_digest(pairing_code)
            assert pairing_code not in pairing.code_digest
            assert pairing.created_by_admin_id is None
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_widget_preflight_allows_only_expected_protocol_headers(
    tmp_path: Path,
) -> None:
    app, engine, _, _, _ = await _open_widget_app(
        tmp_path / "preflight.sqlite3"
    )
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            accepted = await client.options(
                "/api/chat",
                headers={
                    "Origin": _ORIGIN,
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": (
                        "authorization, content-type"
                    ),
                },
            )
            rejected = await client.options(
                "/api/chat",
                headers={
                    "Origin": _ORIGIN,
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "x-api-key",
                },
            )

        assert accepted.status_code == 204
        assert accepted.headers["Access-Control-Allow-Origin"] == _ORIGIN
        assert rejected.status_code == 403
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_widget_bootstrap_rate_limit_is_enforced(
    tmp_path: Path,
) -> None:
    app, engine, sessions, _, _ = await _open_widget_app(
        tmp_path / "bootstrap-rate.sqlite3"
    )
    await _seed_widget(sessions)

    class DenyingLimiter:
        async def check(self, **kwargs) -> RateLimitResult:
            return RateLimitResult(False, 0, 29)

    app.dependency_overrides[get_rate_limiter] = lambda: DenyingLimiter()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/widget/bootstrap",
                json={"widget_id": _WIDGET_ID},
                headers={"Origin": _ORIGIN},
            )
        assert response.status_code == 429
        assert response.headers["Retry-After"] == "29"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_bootstrap_returns_503_when_widget_signing_is_unconfigured(
    tmp_path: Path,
) -> None:
    app, engine, sessions, _, _ = await _open_widget_app(
        tmp_path / "bootstrap-secret.sqlite3"
    )
    await _seed_widget(sessions)
    app.dependency_overrides[get_settings] = lambda: Settings(
        environment="test",
        widget_jwt_secret_key=None,
        _env_file=None,
    )
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/widget/bootstrap",
                json={"widget_id": _WIDGET_ID},
                headers={"Origin": _ORIGIN},
            )

        assert response.status_code == 503
        assert response.headers["Access-Control-Allow-Origin"] == _ORIGIN
        assert response.json() == {
            "detail": "Widget authentication is not configured."
        }
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_widget_chat_rate_limit_is_enforced_after_bootstrap(
    tmp_path: Path,
) -> None:
    app, engine, sessions, runtime, _ = await _open_widget_app(
        tmp_path / "chat-rate.sqlite3"
    )
    await _seed_widget(sessions)

    class DenyingLimiter:
        async def check(self, **kwargs) -> RateLimitResult:
            return RateLimitResult(False, 0, 17)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            token, _ = await _bootstrap(client)
            app.dependency_overrides[get_rate_limiter] = (
                lambda: DenyingLimiter()
            )
            response = await client.post(
                "/api/chat",
                json={"message": "Rate limited"},
                headers={
                    "Origin": _ORIGIN,
                    "Authorization": f"Bearer {token}",
                },
            )

        assert response.status_code == 429
        assert response.headers["Retry-After"] == "17"
        assert response.headers["Access-Control-Allow-Origin"] == _ORIGIN
        runtime.generate.assert_not_awaited()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_widget_chat_rejects_token_origin_mismatch(
    tmp_path: Path,
) -> None:
    app, engine, sessions, runtime, _ = await _open_widget_app(
        tmp_path / "token-origin.sqlite3"
    )
    await _seed_widget(sessions)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            token, _ = await _bootstrap(client)
            response = await client.post(
                "/api/chat",
                json={"message": "Wrong origin"},
                headers={
                    "Origin": "https://attacker.example",
                    "Authorization": f"Bearer {token}",
                },
            )

        assert response.status_code == 403
        assert "Access-Control-Allow-Origin" not in response.headers
        runtime.generate.assert_not_awaited()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_widget_chat_rejects_signed_cross_tenant_claims(
    tmp_path: Path,
) -> None:
    app, engine, sessions, runtime, settings = await _open_widget_app(
        tmp_path / "token-tenant.sqlite3"
    )
    await _seed_widget(sessions)
    token = create_widget_token(
        tenant_id="tenant-other",
        agent_id="agent-other",
        public_widget_id=_WIDGET_ID,
        origin=_ORIGIN,
        session_id=str(uuid4()),
        settings=settings,
    )
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/chat",
                json={"message": "Cross tenant"},
                headers={
                    "Origin": _ORIGIN,
                    "Authorization": f"Bearer {token}",
                },
            )

        assert response.status_code == 401
        runtime.generate.assert_not_awaited()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_widget_chat_persists_session_binding_and_blocks_other_session(
    tmp_path: Path,
) -> None:
    app, engine, sessions, runtime, _ = await _open_widget_app(
        tmp_path / "widget-chat.sqlite3"
    )
    await _seed_widget(sessions)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            token_a, bootstrap_a = await _bootstrap(client)
            first = await client.post(
                "/api/chat",
                json={"message": "Hello from session A"},
                headers={
                    "Origin": _ORIGIN,
                    "Authorization": f"Bearer {token_a}",
                },
            )
            token_b, _ = await _bootstrap(client)
            cross_session = await client.post(
                "/api/chat",
                json={
                    "message": "Try another session",
                    "conversation_id": first.json()["conversation_id"],
                },
                headers={
                    "Origin": _ORIGIN,
                    "Authorization": f"Bearer {token_b}",
                },
            )

        assert first.status_code == 200
        assert first.headers["Access-Control-Allow-Origin"] == _ORIGIN
        assert first.headers["Access-Control-Expose-Headers"] == (
            "X-Request-ID"
        )
        assert first.headers["X-Request-ID"]
        assert cross_session.status_code == 404
        assert cross_session.headers["Access-Control-Allow-Origin"] == _ORIGIN
        async with sessions() as session:
            conversation = await session.get(
                Conversation,
                first.json()["conversation_id"],
            )
        assert conversation is not None
        assert conversation.metadata_json == {
            "auth_source": "widget",
            "widget_session_id": bootstrap_a["session_id"],
            "public_widget_id": _WIDGET_ID,
        }
        assert runtime.generate.await_count == 1
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_widget_chat_rechecks_origin_allow_list_after_bootstrap(
    tmp_path: Path,
) -> None:
    app, engine, sessions, runtime, _ = await _open_widget_app(
        tmp_path / "origin-recheck.sqlite3"
    )
    await _seed_widget(sessions)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            token, _ = await _bootstrap(client)

            async with sessions() as session:
                row = await session.scalar(select(WidgetAllowedOrigin))
                assert row is not None
                await session.delete(row)
                await session.commit()

            response = await client.post(
                "/api/chat",
                json={"message": "Should not run"},
                headers={
                    "Origin": _ORIGIN,
                    "Authorization": f"Bearer {token}",
                },
            )

        assert response.status_code == 403
        runtime.generate.assert_not_awaited()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_invalid_widget_bearer_never_falls_back_to_api_key(
    tmp_path: Path,
) -> None:
    app, engine, sessions, runtime, _ = await _open_widget_app(
        tmp_path / "no-fallback.sqlite3"
    )
    await _seed_widget(sessions)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/chat",
                json={"message": "Do not fall back"},
                headers={
                    "Origin": _ORIGIN,
                    "Authorization": "Bearer invalid.token.value",
                    "X-API-Key": "also-invalid",
                    "X-Agent-ID": "agent-a",
                },
            )

        assert response.status_code == 401
        runtime.generate.assert_not_awaited()
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_public_widget_config_reflects_saved_runtime_changes(
    tmp_path: Path,
) -> None:
    app, engine, sessions, _, _ = await _open_widget_app(
        tmp_path / "public-config.sqlite3"
    )
    await _seed_widget(sessions)

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            preflight = await client.options(
                "/api/widget/config",
                headers={
                    "Origin": _ORIGIN,
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers": "content-type",
                },
            )

            assert preflight.status_code == 204
            assert (
                preflight.headers["Access-Control-Allow-Origin"]
                == _ORIGIN
            )

            first = await client.post(
                "/api/widget/config",
                json={"widget_id": _WIDGET_ID},
                headers={"Origin": _ORIGIN},
            )

            assert first.status_code == 200, first.text
            first_body = first.json()

            assert first_body["widget_id"] == _WIDGET_ID
            assert first_body["display_name"] == "Public Support"
            assert first_body["theme"]["primaryColor"] == "#112233"
            assert "session_token" not in first_body
            assert "session_id" not in first_body
            assert "tenant_id" not in first.text
            assert "agent_id" not in first.text
            assert first.headers["Cache-Control"] == "no-store"
            assert (
                first.headers["Access-Control-Allow-Origin"]
                == _ORIGIN
            )

            async with sessions() as session:
                widget = await session.get(
                    AgentWidgetSettings,
                    {
                        "tenant_id": "tenant-a",
                        "agent_id": "agent-a",
                    },
                )
                assert widget is not None

                widget.display_name = "Updated Public Support"
                widget.primary_color = "#000000"

                await session.commit()

            updated = await client.post(
                "/api/widget/config",
                json={"widget_id": _WIDGET_ID},
                headers={"Origin": _ORIGIN},
            )

            assert updated.status_code == 200
            assert (
                updated.json()["display_name"]
                == "Updated Public Support"
            )
            assert (
                updated.json()["theme"]["primaryColor"]
                == "#000000"
            )

            attacker = await client.post(
                "/api/widget/config",
                json={"widget_id": _WIDGET_ID},
                headers={
                    "Origin": "https://attacker.example",
                },
            )

            assert attacker.status_code == 403
            assert (
                "Access-Control-Allow-Origin"
                not in attacker.headers
            )

            async with sessions() as session:
                widget = await session.get(
                    AgentWidgetSettings,
                    {
                        "tenant_id": "tenant-a",
                        "agent_id": "agent-a",
                    },
                )
                assert widget is not None

                widget.is_enabled = False
                await session.commit()

            disabled = await client.post(
                "/api/widget/config",
                json={"widget_id": _WIDGET_ID},
                headers={"Origin": _ORIGIN},
            )

            assert disabled.status_code == 404

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_connector_pairing_redeem_connects_once(
    tmp_path: Path,
) -> None:
    app, engine, sessions, _, _ = await _open_widget_app(
        tmp_path / "pairing-redeem.sqlite3"
    )
    await _seed_widget(sessions)

    pairing_code = "ATK-TEST-PAIR-CODE-0001"
    pairing_id = await _seed_pairing(
        sessions,
        pairing_code=pairing_code,
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            first = await client.post(
                "/api/widget/connector/pair",
                json={
                    "pairing_code": pairing_code.lower(),
                },
                headers={
                    "Origin": _ORIGIN,
                },
            )

            second = await client.post(
                "/api/widget/connector/pair",
                json={
                    "pairing_code": pairing_code,
                },
                headers={
                    "Origin": _ORIGIN,
                },
            )

        assert first.status_code == 200, first.text
        assert first.json() == {
            "connected": True,
            "widget_id": _WIDGET_ID,
            "origin": _ORIGIN,
            "connector_type": "wordpress",
        }
        assert (
            first.headers["Access-Control-Allow-Origin"]
            == _ORIGIN
        )
        assert first.headers["Cache-Control"] == "no-store"

        assert second.status_code == 400
        assert second.json() == {
            "detail": (
                "Pairing code has already been used. "
                "Generate a new code and retry."
            )
        }

        async with sessions() as session:
            pairing = await session.get(
                WidgetConnectorPairing,
                pairing_id,
            )

        assert pairing is not None
        assert pairing.used_at is not None
        assert pairing.connected_at is not None

        # Only the digest is persisted.
        assert pairing.code_digest == pairing_code_digest(
            pairing_code
        )
        assert pairing.code_digest != pairing_code

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_connector_pairing_rejects_expired_code(
    tmp_path: Path,
) -> None:
    app, engine, sessions, _, _ = await _open_widget_app(
        tmp_path / "pairing-expired.sqlite3"
    )
    await _seed_widget(sessions)

    pairing_code = "ATK-EXPIRED-PAIR-CODE-01"
    await _seed_pairing(
        sessions,
        pairing_code=pairing_code,
        expired=True,
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/widget/connector/pair",
                json={"pairing_code": pairing_code},
                headers={"Origin": _ORIGIN},
            )

        assert response.status_code == 400
        assert response.json() == {
            "detail": (
                "Pairing code has expired. "
                "Generate a new code and retry."
            )
        }

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_real_site_installation_verification_persists_all_checks(
    tmp_path: Path,
) -> None:
    app, engine, sessions, _, _ = await _open_widget_app(
        tmp_path / "installation-verification.sqlite3"
    )
    await _seed_widget(sessions)
    pairing_code = "ATK-INSTALL-VERIFY-CODE-01"
    pairing_id = await _seed_pairing(
        sessions,
        pairing_code=pairing_code,
        connector_type="custom",
    )
    app.dependency_overrides[require_tenant_user_jwt] = _tenant_context

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            public_config = await client.post(
                "/api/widget/config",
                json={"widget_id": _WIDGET_ID},
                headers={"Origin": _ORIGIN},
            )
            token, _ = await _bootstrap(client)
            missing_config_proof = await client.post(
                "/api/widget/connector/verify-installation",
                json={"pairing_code": pairing_code},
                headers={
                    "Origin": _ORIGIN,
                    "Authorization": f"Bearer {token}",
                },
            )
            verified = await client.post(
                "/api/widget/connector/verify-installation",
                json={"pairing_code": pairing_code},
                headers={
                    "Origin": _ORIGIN,
                    "Authorization": f"Bearer {token}",
                    "X-Widget-Config-Proof": public_config.headers[
                        "X-Widget-Config-Proof"
                    ],
                },
            )
            persisted = await client.get(
                "/api/customer/agents/agent-a/widget-settings/installation",
                params={"pairing_id": pairing_id},
            )

        assert public_config.status_code == 200
        assert missing_config_proof.status_code == 401
        assert missing_config_proof.json()["detail"] == (
            "A successful public Widget config load is required."
        )
        assert verified.status_code == 200, verified.text
        assert verified.json()["widget_id"] == _WIDGET_ID
        assert persisted.status_code == 200, persisted.text
        body = persisted.json()
        assert body["status"] == "verified"
        assert body["pairing_id"] == pairing_id
        assert body["origin"] == _ORIGIN
        assert body["connected_at"] is not None
        assert body["checks"] == {
            "script_loaded": True,
            "origin_valid": True,
            "public_config_loaded": True,
            "bootstrap_succeeded": True,
        }
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_installation_verification_requires_matching_bootstrap_origin(
    tmp_path: Path,
) -> None:
    app, engine, sessions, _, settings = await _open_widget_app(
        tmp_path / "installation-origin-scope.sqlite3"
    )
    await _seed_widget(sessions)
    pairing_code = "ATK-INSTALL-ORIGIN-CODE-01"
    pairing_id = await _seed_pairing(
        sessions,
        pairing_code=pairing_code,
        connector_type="custom",
    )
    wrong_origin_token = create_widget_token(
        tenant_id="tenant-a",
        agent_id="agent-a",
        public_widget_id=_WIDGET_ID,
        origin="https://attacker.example",
        session_id=str(uuid4()),
        settings=settings,
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/widget/connector/verify-installation",
                json={"pairing_code": pairing_code},
                headers={
                    "Origin": _ORIGIN,
                    "Authorization": f"Bearer {wrong_origin_token}",
                },
            )

        assert response.status_code == 403
        assert response.json()["detail"] == (
            "Widget bootstrap origin does not match this site."
        )
        async with sessions() as session:
            pairing = await session.get(WidgetConnectorPairing, pairing_id)
            assert pairing is not None
            assert pairing.used_at is None
            assert pairing.connected_at is None
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_connector_pairing_rejects_wrong_origin(
    tmp_path: Path,
) -> None:
    app, engine, sessions, _, _ = await _open_widget_app(
        tmp_path / "pairing-wrong-origin.sqlite3"
    )
    await _seed_widget(sessions)

    pairing_code = "ATK-WRONG-ORIGIN-CODE-01"
    await _seed_pairing(
        sessions,
        pairing_code=pairing_code,
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/widget/connector/pair",
                json={"pairing_code": pairing_code},
                headers={
                    "Origin": "https://attacker.example",
                },
            )

        assert response.status_code == 403
        assert (
            "Access-Control-Allow-Origin"
            not in response.headers
        )

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_connector_pairing_rejects_origin_removed_from_allowlist(
    tmp_path: Path,
) -> None:
    app, engine, sessions, _, _ = await _open_widget_app(
        tmp_path / "pairing-origin-removed.sqlite3"
    )
    await _seed_widget(sessions)

    pairing_code = "ATK-REMOVED-ORIGIN-CODE-1"
    await _seed_pairing(
        sessions,
        pairing_code=pairing_code,
    )

    async with sessions() as session:
        origin = await session.scalar(
            select(WidgetAllowedOrigin).where(
                WidgetAllowedOrigin.tenant_id == "tenant-a",
                WidgetAllowedOrigin.agent_id == "agent-a",
                WidgetAllowedOrigin.origin == _ORIGIN,
            )
        )
        assert origin is not None
        await session.delete(origin)
        await session.commit()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/widget/connector/pair",
                json={"pairing_code": pairing_code},
                headers={"Origin": _ORIGIN},
            )

        assert response.status_code == 403

    finally:
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tenant_active,agent_active,widget_enabled",
    [
        (False, True, True),
        (True, False, True),
        (True, True, False),
    ],
)
async def test_connector_pairing_rejects_disabled_target(
    tmp_path: Path,
    tenant_active: bool,
    agent_active: bool,
    widget_enabled: bool,
) -> None:
    app, engine, sessions, _, _ = await _open_widget_app(
        tmp_path
        / (
            "pairing-disabled-"
            f"{tenant_active}-"
            f"{agent_active}-"
            f"{widget_enabled}.sqlite3"
        )
    )

    await _seed_widget(
        sessions,
        tenant_active=tenant_active,
        agent_active=agent_active,
        widget_enabled=widget_enabled,
    )

    pairing_code = "ATK-DISABLED-TARGET-0001"
    await _seed_pairing(
        sessions,
        pairing_code=pairing_code,
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/widget/connector/pair",
                json={"pairing_code": pairing_code},
                headers={"Origin": _ORIGIN},
            )

        assert response.status_code == 409

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_connector_pairing_rate_limit_is_enforced(
    tmp_path: Path,
) -> None:
    app, engine, _, _, _ = await _open_widget_app(
        tmp_path / "pairing-rate-limit.sqlite3"
    )

    class DenyingLimiter:
        async def check(
            self,
            **kwargs,
        ) -> RateLimitResult:
            return RateLimitResult(
                allowed=False,
                remaining=0,
                retry_after_seconds=31,
            )

    app.dependency_overrides[
        get_rate_limiter
    ] = lambda: DenyingLimiter()

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/widget/connector/pair",
                json={
                    "pairing_code":
                        "ATK-RATE-LIMIT-TEST-0001"
                },
                headers={"Origin": _ORIGIN},
            )

        assert response.status_code == 429
        assert response.headers["Retry-After"] == "31"

    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_connector_pairing_preflight_is_supported(
    tmp_path: Path,
) -> None:
    app, engine, _, _, _ = await _open_widget_app(
        tmp_path / "pairing-preflight.sqlite3"
    )

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.options(
                "/api/widget/connector/pair",
                headers={
                    "Origin": _ORIGIN,
                    "Access-Control-Request-Method": "POST",
                    "Access-Control-Request-Headers":
                        "content-type",
                },
            )

        assert response.status_code == 204
        assert (
            response.headers["Access-Control-Allow-Origin"]
            == _ORIGIN
        )

    finally:
        await engine.dispose()
