"""Trusted administrative lifecycle operations across tenant aggregates."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import (
    Agent,
    ApiKey,
    Conversation,
    DocumentModel,
    IngestionJob,
    Tenant,
)


if TYPE_CHECKING:
    from backend.app.api.schemas.admin import AgentConfigUpdate


class AdminResourceNotFoundError(LookupError):
    """Raised when an administrative resource is absent in its scope."""


class AdminLifecycleConflictError(RuntimeError):
    """Raised when a destructive operation violates lifecycle preconditions."""


class AdminLifecycleValidationError(ValueError):
    """Raised when an administrative mutation payload is invalid."""


@dataclass(frozen=True, slots=True)
class DeleteResult:
    """Database deletion result with source objects requiring cleanup."""

    storage_keys: tuple[str, ...] = ()


async def list_tenants(session: AsyncSession) -> list[Tenant]:
    """List tenants in deterministic creation order."""

    return list(
        (
            await session.scalars(
                select(Tenant).order_by(Tenant.created_at, Tenant.id)
            )
        ).all()
    )


async def require_tenant(
    session: AsyncSession,
    tenant_id: str,
) -> Tenant:
    """Resolve one tenant without leaking another scope."""

    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        raise AdminResourceNotFoundError("Tenant not found")
    return tenant


async def set_tenant_active(
    session: AsyncSession,
    *,
    tenant_id: str,
    is_active: bool,
) -> Tenant:
    """Activate or suspend a tenant without destroying credentials."""

    tenant = await require_tenant(session, tenant_id)
    tenant.is_active = is_active
    await session.flush()
    return tenant


async def delete_tenant(
    session: AsyncSession,
    *,
    tenant_id: str,
) -> DeleteResult:
    """Hard-delete a suspended tenant and all database-scoped resources."""

    tenant = await require_tenant(session, tenant_id)
    if tenant.is_active:
        raise AdminLifecycleConflictError(
            "Suspend the tenant before permanent deletion."
        )
    await _ensure_no_active_ingestion_jobs(
        session,
        tenant_id=tenant_id,
    )
    storage_keys = await _storage_keys(
        session,
        tenant_id=tenant_id,
    )
    await session.delete(tenant)
    await session.flush()
    return DeleteResult(storage_keys=storage_keys)


async def list_agents(
    session: AsyncSession,
    *,
    tenant_id: str,
) -> list[Agent]:
    """List agents owned by one existing tenant."""

    await require_tenant(session, tenant_id)
    return list(
        (
            await session.scalars(
                select(Agent)
                .where(Agent.tenant_id == tenant_id)
                .order_by(Agent.created_at, Agent.id)
            )
        ).all()
    )


async def require_agent(
    session: AsyncSession,
    *,
    tenant_id: str,
    agent_id: str,
) -> Agent:
    """Resolve one agent strictly inside its tenant scope."""

    agent = await session.scalar(
        select(Agent).where(
            Agent.id == agent_id,
            Agent.tenant_id == tenant_id,
        )
    )
    if agent is None:
        raise AdminResourceNotFoundError("Agent not found")
    return agent


async def set_agent_active(
    session: AsyncSession,
    *,
    tenant_id: str,
    agent_id: str,
    is_active: bool,
) -> Agent:
    """Activate or suspend one tenant-scoped agent."""

    await require_tenant(session, tenant_id)
    agent = await require_agent(
        session,
        tenant_id=tenant_id,
        agent_id=agent_id,
    )
    agent.is_active = is_active
    await session.flush()
    return agent


async def update_agent_config(
    session: AsyncSession,
    *,
    tenant_id: str,
    agent_id: str,
    update: "AgentConfigUpdate",
) -> Agent:
    """Apply a validated partial configuration update to one scoped agent.

    The operation flushes changes but deliberately does not commit. The API
    route owns the transaction so the state mutation and its audit record
    commit or roll back together.
    """

    changed_fields = set(update.model_fields_set)

    if not changed_fields:
        raise AdminLifecycleValidationError(
            "At least one agent configuration field must be provided."
        )

    editable_fields = {
        "name",
        "system_prompt",
        "knowledge_mode",
        "contact_message",
    }

    unsupported_fields = changed_fields - editable_fields

    if unsupported_fields:
        raise AdminLifecycleValidationError(
            "Unsupported agent configuration fields: "
            + ", ".join(sorted(unsupported_fields))
        )

    await require_tenant(session, tenant_id)

    agent = await require_agent(
        session,
        tenant_id=tenant_id,
        agent_id=agent_id,
    )

    for field_name in sorted(changed_fields):
        setattr(
            agent,
            field_name,
            getattr(update, field_name),
        )

    await session.flush()
    return agent


async def delete_agent(
    session: AsyncSession,
    *,
    tenant_id: str,
    agent_id: str,
) -> DeleteResult:
    """Hard-delete a suspended agent after knowledge data is removed.

    The operation deliberately refuses to delete an agent that is still
    referenced by documents. This prevents an administrative action from
    silently removing tenant-owned knowledge that may be shared with another
    agent. Delete or reassign those documents first.
    """

    await require_tenant(session, tenant_id)
    agent = await require_agent(
        session,
        tenant_id=tenant_id,
        agent_id=agent_id,
    )
    if agent.is_active:
        raise AdminLifecycleConflictError(
            "Suspend the agent before permanent deletion."
        )
    await _ensure_no_active_ingestion_jobs(
        session,
        tenant_id=tenant_id,
        agent_id=agent_id,
    )
    dependent_document_id = await session.scalar(
        select(DocumentModel.id)
        .where(
            DocumentModel.tenant_id == tenant_id,
            DocumentModel.agent_id == agent_id,
        )
        .limit(1)
    )
    if dependent_document_id is not None:
        raise AdminLifecycleConflictError(
            "Delete or reassign agent documents before permanent deletion."
        )
    await session.delete(agent)
    await session.flush()
    return DeleteResult()


async def list_api_keys(
    session: AsyncSession,
    *,
    tenant_id: str,
) -> list[ApiKey]:
    """List non-secret key metadata for one tenant."""

    await require_tenant(session, tenant_id)
    return list(
        (
            await session.scalars(
                select(ApiKey)
                .where(ApiKey.tenant_id == tenant_id)
                .order_by(ApiKey.created_at.desc(), ApiKey.key_id)
            )
        ).all()
    )


async def revoke_api_key(
    session: AsyncSession,
    *,
    tenant_id: str,
    key_id: str,
) -> ApiKey:
    """Idempotently revoke one tenant-owned API key."""

    await require_tenant(session, tenant_id)
    api_key = await session.scalar(
        select(ApiKey).where(
            ApiKey.tenant_id == tenant_id,
            ApiKey.key_id == key_id,
        )
    )
    if api_key is None:
        raise AdminResourceNotFoundError("API key not found")
    if api_key.revoked_at is None:
        api_key.revoked_at = datetime.now(timezone.utc)
    api_key.is_active = False
    await session.flush()
    return api_key


async def revoke_all_api_keys(
    session: AsyncSession,
    *,
    tenant_id: str,
) -> int:
    """Revoke every currently active key for one tenant."""

    keys = await list_api_keys(session, tenant_id=tenant_id)
    now = datetime.now(timezone.utc)
    revoked_count = 0
    for api_key in keys:
        if api_key.is_active or api_key.revoked_at is None:
            api_key.is_active = False
            api_key.revoked_at = api_key.revoked_at or now
            revoked_count += 1
    await session.flush()
    return revoked_count


async def delete_conversation(
    session: AsyncSession,
    *,
    tenant_id: str,
    conversation_id: str,
) -> None:
    """Delete one tenant-scoped conversation and cascade its messages."""

    await require_tenant(session, tenant_id)
    conversation = await session.scalar(
        select(Conversation).where(
            Conversation.tenant_id == tenant_id,
            Conversation.id == conversation_id,
        )
    )
    if conversation is None:
        raise AdminResourceNotFoundError("Conversation not found")
    await session.delete(conversation)
    await session.flush()


async def _ensure_no_active_ingestion_jobs(
    session: AsyncSession,
    *,
    tenant_id: str,
    agent_id: str | None = None,
) -> None:
    statement = select(IngestionJob.id).where(
        IngestionJob.tenant_id == tenant_id,
        IngestionJob.status.in_(("pending", "processing")),
    )
    if agent_id is not None:
        statement = statement.where(IngestionJob.agent_id == agent_id)
    active_job_id = await session.scalar(statement.limit(1))
    if active_job_id is not None:
        raise AdminLifecycleConflictError(
            "Wait for active ingestion jobs to finish before deletion."
        )


async def _storage_keys(
    session: AsyncSession,
    *,
    tenant_id: str,
    agent_id: str | None = None,
) -> tuple[str, ...]:
    statement = select(IngestionJob.storage_key).where(
        IngestionJob.tenant_id == tenant_id
    )
    if agent_id is not None:
        statement = statement.where(IngestionJob.agent_id == agent_id)
    return tuple((await session.scalars(statement)).all())
