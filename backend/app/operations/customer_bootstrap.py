"""Trusted bootstrap service for the first tenant, agent, and API key."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.api_keys import issue_api_key
from backend.app.db.models import Agent, ApiKey, Tenant


class BootstrapConflictError(ValueError):
    """Raised when bootstrap would overwrite or duplicate trusted data."""


@dataclass(frozen=True, slots=True)
class CustomerBootstrapResult:
    """Created or resolved customer resources and one newly issued key."""

    tenant_id: str
    agent_id: str
    api_key: str = field(repr=False)
    tenant_created: bool
    agent_created: bool
    rotated_key_count: int


def _required(value: str, field_name: str, max_length: int) -> str:
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must not be empty.")
    if len(normalized) > max_length:
        raise ValueError(
            f"{field_name} must be at most {max_length} characters."
        )
    return normalized


async def bootstrap_customer(
    session: AsyncSession,
    *,
    tenant_id: str,
    tenant_name: str,
    agent_id: str,
    agent_name: str,
    system_prompt: str | None,
    key_name: str,
    knowledge_mode: str = "required",
    fallback_message: str | None = None,
    handoff_enabled: bool = True,
    rotate_key: bool = False,
) -> CustomerBootstrapResult:
    """Create one tenant-scoped agent and issue a server-side API key.

    Existing tenant and agent rows are reused only when their ownership is
    compatible. An active key with the same name is never duplicated unless
    ``rotate_key`` is explicitly requested.
    """

    tenant_id = _required(tenant_id, "tenant_id", 128)
    tenant_name = _required(tenant_name, "tenant_name", 255)
    agent_id = _required(agent_id, "agent_id", 128)
    agent_name = _required(agent_name, "agent_name", 255)
    key_name = _required(key_name, "key_name", 255)
    normalized_prompt = (system_prompt or "").strip() or None
    if knowledge_mode not in {"required", "preferred", "disabled"}:
        raise ValueError(
            "knowledge_mode must be required, preferred, or disabled."
        )
    normalized_fallback = (fallback_message or "").strip() or None

    tenant = await session.get(Tenant, tenant_id)
    tenant_created = tenant is None
    if tenant is None:
        tenant = Tenant(id=tenant_id, name=tenant_name)
        session.add(tenant)
        await session.flush()

    agent = await session.get(Agent, agent_id)
    agent_created = agent is None
    if agent is None:
        agent = Agent(
            id=agent_id,
            tenant_id=tenant_id,
            name=agent_name,
            system_prompt=normalized_prompt,
            knowledge_mode=knowledge_mode,
            fallback_message=normalized_fallback,
            handoff_enabled=handoff_enabled,
        )
        session.add(agent)
        await session.flush()
    elif agent.tenant_id != tenant_id:
        raise BootstrapConflictError(
            "The requested agent_id already belongs to another tenant."
        )

    active_keys = list(
        (
            await session.scalars(
                select(ApiKey).where(
                    ApiKey.tenant_id == tenant_id,
                    ApiKey.name == key_name,
                    ApiKey.is_active.is_(True),
                    ApiKey.revoked_at.is_(None),
                )
            )
        ).all()
    )
    if active_keys and not rotate_key:
        raise BootstrapConflictError(
            "An active API key with this name already exists. "
            "Use --rotate-key to replace it."
        )

    now = datetime.now(timezone.utc)
    for existing_key in active_keys:
        existing_key.is_active = False
        existing_key.revoked_at = now

    issued = issue_api_key()
    session.add(
        ApiKey(
            tenant_id=tenant_id,
            key_id=issued.key_id,
            key_digest=issued.key_digest,
            name=key_name,
        )
    )
    await session.flush()

    return CustomerBootstrapResult(
        tenant_id=tenant_id,
        agent_id=agent_id,
        api_key=issued.raw_key,
        tenant_created=tenant_created,
        agent_created=agent_created,
        rotated_key_count=len(active_keys),
    )
