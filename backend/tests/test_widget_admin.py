"""Integration tests for RBAC-protected Widget configuration."""

from __future__ import annotations

from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from backend.app.db.models import (
    AdminAuditLog,
    Agent,
    AgentWidgetSettings,
    Tenant,
    WidgetAllowedOrigin,
)
from backend.tests.test_admin_rbac import (
    _login_as,
    _open_admin_mgmt_app,
    _seed_admin_t16,
)


_WIDGET_PATH = "/api/admin/tenants/tenant-a/agents/agent-a/widget"


async def _seed_agent(sessions) -> None:
    async with sessions() as session:
        session.add_all(
            [
                Tenant(id="tenant-a", name="Tenant A"),
                Agent(
                    id="agent-a",
                    tenant_id="tenant-a",
                    name="Agent A",
                ),
            ]
        )
        await session.commit()


def _payload(**overrides) -> dict:
    value = {
        "is_enabled": True,
        "display_name": "Customer Support",
        "greeting": "How can we help?",
        "theme": {
            "primaryColor": "#123456",
            "textColor": "#FFFFFF",
            "launcherColor": "#234567",
            "headerColor": "#345678",
            "userMessageColor": "#456789",
            "position": "left",
            "appearance": "dark",
        },
        "allowed_origins": ["https://Example.COM:443/"],
    }
    value.update(overrides)
    return value


@pytest.mark.asyncio
async def test_super_admin_configures_widget_with_runtime_theme(
    tmp_path: Path,
) -> None:
    app, engine, sessions = await _open_admin_mgmt_app(
        tmp_path / "widget-config.sqlite3"
    )
    await _seed_admin_t16(
        sessions,
        admin_id="super-001",
        username="alice",
        role="super_admin",
    )
    await _seed_agent(sessions)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            token = await _login_as(client, username="alice")
            response = await client.put(
                _WIDGET_PATH,
                json=_payload(),
                headers={"Authorization": f"Bearer {token}"},
            )

        assert response.status_code == 200, response.text
        body = response.json()
        assert body["public_widget_id"].startswith("wgt_")
        assert body["is_enabled"] is True
        assert body["allowed_origins"] == ["https://example.com"]
        assert body["theme"]["primaryColor"] == "#123456"
        assert body["theme"]["position"] == "left"

        async with sessions() as session:
            widget = await session.get(
                AgentWidgetSettings,
                {"tenant_id": "tenant-a", "agent_id": "agent-a"},
            )
            origin = await session.scalar(select(WidgetAllowedOrigin))
            audit = await session.scalar(
                select(AdminAuditLog).where(
                    AdminAuditLog.event_type == "widget_configured"
                )
            )
        assert widget is not None
        assert origin is not None and origin.origin == "https://example.com"
        assert audit is not None and audit.admin_id == "super-001"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_widget_public_id_is_stable_across_configuration_updates(
    tmp_path: Path,
) -> None:
    app, engine, sessions = await _open_admin_mgmt_app(
        tmp_path / "stable-id.sqlite3"
    )
    await _seed_admin_t16(
        sessions,
        admin_id="super-001",
        username="alice",
        role="super_admin",
    )
    await _seed_agent(sessions)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            token = await _login_as(client, username="alice")
            first = await client.put(
                _WIDGET_PATH,
                json=_payload(),
                headers={"Authorization": f"Bearer {token}"},
            )
            second = await client.put(
                _WIDGET_PATH,
                json=_payload(display_name="Updated Name"),
                headers={"Authorization": f"Bearer {token}"},
            )

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["public_widget_id"] == (
            second.json()["public_widget_id"]
        )
        assert second.json()["display_name"] == "Updated Name"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_auditor_can_read_but_cannot_change_widget_settings(
    tmp_path: Path,
) -> None:
    app, engine, sessions = await _open_admin_mgmt_app(
        tmp_path / "widget-rbac.sqlite3"
    )
    await _seed_admin_t16(
        sessions,
        admin_id="super-001",
        username="alice",
        role="super_admin",
    )
    await _seed_admin_t16(
        sessions,
        admin_id="auditor-001",
        username="eve",
        role="auditor",
    )
    await _seed_agent(sessions)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            super_token = await _login_as(client, username="alice")
            configured = await client.put(
                _WIDGET_PATH,
                json=_payload(),
                headers={"Authorization": f"Bearer {super_token}"},
            )
            assert configured.status_code == 200

            auditor_token = await _login_as(client, username="eve")
            read_response = await client.get(
                _WIDGET_PATH,
                headers={"Authorization": f"Bearer {auditor_token}"},
            )
            write_response = await client.put(
                _WIDGET_PATH,
                json=_payload(display_name="Forbidden Update"),
                headers={"Authorization": f"Bearer {auditor_token}"},
            )

        assert read_response.status_code == 200
        assert write_response.status_code == 403
    finally:
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        _payload(allowed_origins=["http://customer.example"]),
        _payload(allowed_origins=[f"https://{'a' * 250}.example"]),
        _payload(
            allowed_origins=[
                "https://example.com",
                "https://EXAMPLE.com:443/",
            ]
        ),
        _payload(
            theme={
                "primaryColor": "red",
                "textColor": "#FFFFFF",
                "launcherColor": "#234567",
                "headerColor": "#345678",
                "userMessageColor": "#456789",
                "position": "left",
                "appearance": "dark",
            }
        ),
        _payload(
            theme={
                "primaryColor": "#FFFFFF",
                "textColor": "#FFFFFF",
                "launcherColor": "#FFFFFF",
                "headerColor": "#FFFFFF",
                "userMessageColor": "#FFFFFF",
                "position": "right",
                "appearance": "light",
            }
        ),
    ],
)
async def test_invalid_widget_configuration_returns_422(
    tmp_path: Path,
    payload: dict,
) -> None:
    app, engine, sessions = await _open_admin_mgmt_app(
        tmp_path / f"invalid-{abs(hash(str(payload)))}.sqlite3"
    )
    await _seed_admin_t16(
        sessions,
        admin_id="super-001",
        username="alice",
        role="super_admin",
    )
    await _seed_agent(sessions)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            token = await _login_as(client, username="alice")
            response = await client.put(
                _WIDGET_PATH,
                json=payload,
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 422
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_get_unconfigured_widget_returns_404(tmp_path: Path) -> None:
    app, engine, sessions = await _open_admin_mgmt_app(
        tmp_path / "unconfigured.sqlite3"
    )
    await _seed_admin_t16(
        sessions,
        admin_id="super-001",
        username="alice",
        role="super_admin",
    )
    await _seed_agent(sessions)
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            token = await _login_as(client, username="alice")
            response = await client.get(
                _WIDGET_PATH,
                headers={"Authorization": f"Bearer {token}"},
            )
        assert response.status_code == 404
    finally:
        await engine.dispose()
