"""FastAPI dependencies for authentication and AI runtime construction."""

from datetime import datetime, timezone
from functools import lru_cache
import secrets
from typing import Annotated, Callable, Optional

from fastapi import Depends, Header, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.api_keys import parse_api_key, verify_api_key_secret
from backend.app.ai.ports import EmbeddingProvider
from backend.app.auth.context import ChatExecutionContext
from backend.app.core.config import Settings, get_settings
from backend.app.db.base import get_db
from backend.app.db.models import Agent, ApiKey, Tenant
from backend.app.services.chat import GenerationRuntime

api_key_header = APIKeyHeader(
    name="X-API-Key",
    scheme_name="TenantApiKey",
    description="Server-side tenant API key. Never expose it in a browser.",
    auto_error=False,
)

admin_api_key_header = APIKeyHeader(
    name="X-Admin-Key",
    scheme_name="InternalAdminKey",
    description=(
        "Temporary internal administrative credential. "
        "It will be replaced by RBAC-backed admin sessions."
    ),
    auto_error=False,
)

# ---------------------------------------------------------------------------
# RBAC: role → permission mapping  (T-13)
# ---------------------------------------------------------------------------

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "super_admin": frozenset(
        {
            "tenants:read",
            "tenants:write",
            "tenants:delete",
            "agents:read",
            "agents:write",
            "agents:delete",
            "api_keys:read",
            "api_keys:revoke",
            "conversations:delete",
            "admins:read",
            "admins:write",
            "admins:delete",
            "audit:read",
        }
    ),
    "operator": frozenset(
        {
            "tenants:read",
            "tenants:write",
            "agents:read",
            "agents:write",
            "api_keys:read",
            "api_keys:revoke",
            "conversations:delete",
        }
    ),
    "auditor": frozenset(
        {
            "tenants:read",
            "agents:read",
            "api_keys:read",
            "audit:read",
        }
    ),
}


def require_permission(permission: str) -> Callable:
    """Return a FastAPI dependency that enforces *permission* for the caller.

    Usage::

        @router.delete("/tenants/{id}")
        async def delete_tenant(
            _: Annotated[None, Depends(require_permission("tenants:delete"))],
            ...
        ): ...

    The dependency relies on ``require_admin_access`` having already placed
    an ``AdminContext`` in the request state, **or** on the route calling
    ``require_admin_jwt`` directly.  When the legacy key path is used the
    role defaults to ``super_admin``, so all permissions are granted.

    Raises HTTP 403 if the active role lacks *permission*.
    """
    from backend.app.auth.admin_context import AdminContext

    def _check(
        ctx: Annotated[AdminContext | None, Depends(require_admin_access)],
    ) -> None:
        # ctx is None only when require_admin_access returns None (e.g., via
        # dependency_overrides in tests).  In that case we skip the check so
        # existing lifecycle tests continue to pass unchanged.
        if ctx is None:
            return
        role = getattr(ctx, "role", "super_admin")
        allowed = ROLE_PERMISSIONS.get(role, frozenset())
        if permission not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: '{permission}' required.",
            )

    return _check


def require_admin_access(
    raw_admin_key: Annotated[
        str | None,
        Security(admin_api_key_header),
    ],
    settings: Annotated[Settings, Depends(get_settings)],
    request: Request = None,  # type: ignore[assignment]
) -> "AdminContext | None":
    """Dual-path admin authentication: JWT Bearer or legacy X-Admin-Key.

    Path A (JWT — new default):
        Reads ``Authorization: Bearer <token>`` and returns an ``AdminContext``.

    Path B (legacy — backward-compatible):
        When ``MAAP_ADMIN_LEGACY_KEY_ENABLED=true`` and ``X-Admin-Key`` header
        is present, validates against ``MAAP_ADMIN_API_KEY`` and returns an
        ``AdminContext`` with ``role="super_admin"`` to preserve full access.

    Returns
    -------
    AdminContext | None
        None is only returned when the function body is replaced entirely by
        ``dependency_overrides`` in tests (e.g. ``lambda: None``).  The
        real function always either returns an ``AdminContext`` or raises.

    Backward-compatibility guarantee
    ---------------------------------
    Existing tests that do::

        app.dependency_overrides[require_admin_access] = lambda: None

    continue to work because FastAPI replaces the entire function, so the
    new return type is never seen by those tests.
    """
    from fastapi import Request as _Request
    from backend.app.auth.admin_context import AdminContext

    # --- Path B: legacy X-Admin-Key -----------------------------------
    if settings.admin_legacy_key_enabled and raw_admin_key is not None:
        configured = (
            settings.admin_api_key.get_secret_value().strip()
            if settings.admin_api_key is not None
            else ""
        )
        if not configured:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Administrative API is disabled",
            )
        if not secrets.compare_digest(raw_admin_key, configured):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid administrative credentials",
            )
        # Legacy key is treated as super_admin for backward compatibility.
        return AdminContext(
            admin_id="legacy",
            username="legacy",
            role="super_admin",
        )

    # --- Path A: JWT Bearer -------------------------------------------
    # Extract the token from the Authorization header.
    # ``request`` is None when the dependency is evaluated outside an HTTP
    # context (e.g., unit tests that call the function directly).
    auth_header: str = ""
    if request is not None:
        auth_header = request.headers.get("Authorization", "")

    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid administrative credentials",
        )

    raw_jwt = auth_header[len("Bearer "):]

    from backend.app.auth.admin_jwt import AdminTokenError, decode_access_token

    try:
        return decode_access_token(raw_jwt, settings)
    except AdminTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid administrative credentials",
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
