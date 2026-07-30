"""FastAPI dependencies for authentication and AI runtime construction."""

from datetime import datetime, timezone
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.api_keys import parse_api_key, verify_api_key_secret
from backend.app.ai.ports import EmbeddingProvider
from backend.app.auth.context import ChatExecutionContext
from backend.app.core.config import get_settings
from backend.app.db.base import get_db
from backend.app.db.models import Agent, ApiKey, Tenant
from backend.app.services.chat import GenerationRuntime

api_key_header = APIKeyHeader(
    name="X-API-Key",
    scheme_name="TenantApiKey",
    description="Server-side tenant API key. Never expose it in a browser.",
    auto_error=False,
)


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or inactive API credentials",
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


async def require_chat_context(
    session: Annotated[AsyncSession, Depends(get_db)],
    raw_api_key: Annotated[str | None, Security(api_key_header)],
    agent_id: Annotated[
        str | None,
        Header(
            alias="X-Agent-ID",
            description="Agent selector authorized against the API-key tenant.",
        ),
    ] = None,
) -> ChatExecutionContext:
    """Authenticate the key and resolve a tenant-scoped active agent."""

    if raw_api_key is None:
        raise _unauthorized()

    parsed = parse_api_key(raw_api_key)
    if parsed is None:
        raise _unauthorized()

    key_id, secret = parsed
    row = (
        await session.execute(
            select(ApiKey, Tenant)
            .join(Tenant, Tenant.id == ApiKey.tenant_id)
            .where(ApiKey.key_id == key_id)
        )
    ).one_or_none()

    if row is None:
        raise _unauthorized()

    api_key, tenant = row
    now = datetime.now(timezone.utc)
    expired = (
        api_key.expires_at is not None
        and _as_utc(api_key.expires_at) <= now
    )

    if (
        not verify_api_key_secret(secret, api_key.key_digest)
        or not api_key.is_active
        or api_key.revoked_at is not None
        or expired
        or not tenant.is_active
    ):
        raise _unauthorized()

    normalized_agent_id = (agent_id or "").strip()
    if not normalized_agent_id or len(normalized_agent_id) > 128:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Agent-ID is required",
        )

    agent = await session.scalar(
        select(Agent).where(
            Agent.id == normalized_agent_id,
            Agent.tenant_id == tenant.id,
            Agent.is_active.is_(True),
        )
    )
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Agent is not authorized for these credentials",
        )

    api_key.last_used_at = now
    return ChatExecutionContext(
        tenant_id=tenant.id,
        agent_id=agent.id,
        system_prompt=agent.system_prompt,
        knowledge_mode=agent.knowledge_mode,
        contact_message=agent.contact_message,
    )


@lru_cache
def get_core_ai_runtime() -> GenerationRuntime:
    """Build and cache the configured provider-independent AI runtime."""

    from backend.app.ai.providers.deepseek import (
        DeepSeekGenerationProvider,
    )
    from backend.app.ai.providers.ollama import OllamaEmbeddingProvider
    from backend.app.ai.runtime import CoreAIRuntime

    settings = get_settings()
    return CoreAIRuntime(
        generation_provider=DeepSeekGenerationProvider(settings),
        embedding_provider=OllamaEmbeddingProvider(settings),
    )


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    """Build embeddings without requiring a generation-provider API key."""

    from backend.app.ai.providers.ollama import OllamaEmbeddingProvider

    return OllamaEmbeddingProvider(get_settings())
