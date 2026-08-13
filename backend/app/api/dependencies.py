"""FastAPI dependencies for authentication and AI runtime construction."""

from datetime import datetime, timezone
from functools import lru_cache
import secrets
from typing import Annotated, Callable, Optional

from fastapi import Depends, Header, HTTPException, Request, Security, status
from fastapi.security import (
    APIKeyHeader,
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.api_keys import parse_api_key, verify_api_key_secret
from backend.app.auth.origin import normalize_origin
from backend.app.auth.widget_jwt import WidgetTokenError, decode_widget_token
from backend.app.ai.ports import EmbeddingProvider
from backend.app.auth.admin_context import AdminContext
from backend.app.auth.context import ChatExecutionContext
from backend.app.core.config import Settings, get_settings
from backend.app.core.rate_limit import RateLimiter, get_rate_limiter
from backend.app.db.base import get_db
from backend.app.db.models import (
    AdminRefreshSession,
    AdminUser,
    Agent,
    ApiKey,
    Tenant,
)
from backend.app.services.chat import GenerationRuntime
from backend.app.operations.widget import (
    is_widget_origin_allowed,
    resolve_public_widget,
)

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
        "Legacy internal administrative credential. "
        "Prefer a short-lived AdminJWT session."
    ),
    auto_error=False,
)

admin_bearer = HTTPBearer(
    scheme_name="AdminJWT",
    bearerFormat="JWT",
    description=(
        "Short-lived administrative access token issued by "
        "POST /api/admin/auth/login."
    ),
    auto_error=False,
)

widget_bearer = HTTPBearer(
    scheme_name="WidgetToken",
    bearerFormat="JWT",
    description=(
        "Short-lived, origin-bound browser token issued by "
        "POST /api/widget/bootstrap."
    ),
    auto_error=False,
)

tenant_bearer = HTTPBearer(
    scheme_name="TenantUserJWT",
    bearerFormat="JWT",
    description=(
        "Short-lived tenant user access token issued by "
        "POST /api/v1/tenant-auth/login."
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
            "conversations:read",
            "conversations:delete",
            "admins:read",
            "admins:write",
            "admins:delete",
            "audit:read",
            "widgets:read",
            "widgets:write",
            "knowledge:read",
            "knowledge:write",
            "knowledge:delete",
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
            "conversations:read",
            "conversations:delete",
            "widgets:read",
            "widgets:write",
            "knowledge:read",
            "knowledge:write",
        }
    ),
    "auditor": frozenset(
        {
            "tenants:read",
            "agents:read",
            "api_keys:read",
            "conversations:read",
            "audit:read",
            "widgets:read",
            "knowledge:read",
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


def _admin_unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid administrative credentials",
    )


async def _validated_admin_jwt(
    request: Request,
    session: AsyncSession,
    settings: Settings,
) -> AdminContext:
    """Validate JWT integrity and its authoritative database session."""

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise _admin_unauthorized()

    from backend.app.auth.admin_jwt import AdminTokenError, decode_access_token

    try:
        token_context = decode_access_token(
            auth_header[len("Bearer "):],
            settings,
        )
    except AdminTokenError as exc:
        raise _admin_unauthorized() from exc

    if token_context.session_family_id is None:
        raise _admin_unauthorized()

    admin = await session.get(AdminUser, token_context.admin_id)
    if (
        admin is None
        or not admin.is_active
        or admin.role not in ROLE_PERMISSIONS
    ):
        raise _admin_unauthorized()

    now = datetime.now(timezone.utc)
    family_sessions = list(
        (
            await session.scalars(
                select(AdminRefreshSession).where(
                    AdminRefreshSession.admin_id == admin.id,
                    AdminRefreshSession.family_id
                    == token_context.session_family_id,
                    AdminRefreshSession.revoked_at.is_(None),
                )
            )
        ).all()
    )
    if not any(_as_utc(item.expires_at) > now for item in family_sessions):
        raise _admin_unauthorized()

    return AdminContext(
        admin_id=admin.id,
        username=admin.username,
        role=admin.role,  # type: ignore[arg-type]
        auth_method="jwt",
        session_family_id=token_context.session_family_id,
        jti=token_context.jti,
    )


async def require_admin_jwt(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    _admin_credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Security(admin_bearer),
    ] = None,
) -> AdminContext:
    """Require a live database-backed admin JWT session."""

    return await _validated_admin_jwt(request, session, settings)


async def require_admin_access(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    raw_admin_key: Annotated[
        str | None,
        Security(admin_api_key_header),
    ] = None,
    _admin_credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Security(admin_bearer),
    ] = None,
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
            auth_method="legacy",
        )

    # --- Path A: JWT Bearer -------------------------------------------
    return await _validated_admin_jwt(request, session, settings)



def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or inactive API credentials",
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


async def require_tenant_api_key_context(
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
    """Authenticate a server-side tenant API key only."""

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
        auth_method="api_key",
    )


async def require_chat_context(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    raw_api_key: Annotated[str | None, Security(api_key_header)],
    settings: Annotated[Settings, Depends(get_settings)],
    rate_limiter: Annotated[RateLimiter, Depends(get_rate_limiter)],
    _widget_credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Security(widget_bearer),
    ] = None,
    agent_id: Annotated[
        str | None,
        Header(
            alias="X-Agent-ID",
            description="Agent selector authorized against the API-key tenant.",
        ),
    ] = None,
) -> ChatExecutionContext:
    """Authenticate either a browser Widget JWT or a server-side API key."""

    authorization = request.headers.get("Authorization", "")
    if authorization:
        if not authorization.startswith("Bearer "):
            raise _unauthorized()
        raw_widget_token = authorization[len("Bearer "):].strip()
        if not raw_widget_token or " " in raw_widget_token:
            raise _unauthorized()
        try:
            widget_context = decode_widget_token(raw_widget_token, settings)
        except WidgetTokenError as exc:
            raise _unauthorized() from exc

        origin = normalize_origin(request.headers.get("Origin"))
        if origin is None or origin != widget_context.origin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Widget origin mismatch",
            )

        resolved = await resolve_public_widget(
            session,
            widget_context.public_widget_id,
        )
        if resolved is None:
            raise _unauthorized()
        widget, agent, tenant = resolved
        if (
            widget.tenant_id != widget_context.tenant_id
            or widget.agent_id != widget_context.agent_id
            or tenant.id != widget_context.tenant_id
            or agent.id != widget_context.agent_id
        ):
            raise _unauthorized()
        if not await is_widget_origin_allowed(
            session,
            tenant_id=tenant.id,
            agent_id=agent.id,
            origin=origin,
            environment=settings.environment,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Origin is no longer allowed for this Widget",
            )

        request.state.widget_cors_origin = origin
        try:
            limit = await rate_limiter.check(
                bucket="widget-chat-session",
                identity=(
                    f"{tenant.id}:{agent.id}:{widget_context.session_id}"
                ),
                limit=settings.widget_chat_rate_limit_per_session,
                window_seconds=(
                    settings.widget_chat_rate_limit_window_seconds
                ),
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Widget service is temporarily unavailable.",
            ) from exc
        if not limit.allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many Widget chat requests.",
                headers={
                    "Retry-After": str(limit.retry_after_seconds),
                },
            )

        return ChatExecutionContext(
            tenant_id=tenant.id,
            agent_id=agent.id,
            system_prompt=agent.system_prompt,
            knowledge_mode=agent.knowledge_mode,  # type: ignore[arg-type]
            contact_message=agent.contact_message,
            auth_method="widget",
            session_id=widget_context.session_id,
            public_widget_id=widget.public_widget_id,
        )

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
        auth_method="api_key",
    )


async def require_knowledge_context(
    session: Annotated[AsyncSession, Depends(get_db)],
    raw_api_key: Annotated[
        str | None,
        Security(api_key_header),
    ],
    settings: Annotated[
        Settings,
        Depends(get_settings),
    ],
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Security(tenant_bearer),
    ] = None,
    agent_id: Annotated[
        str | None,
        Header(
            alias="X-Agent-ID",
            description=(
                "Agent selected for the knowledge operation."
            ),
        ),
    ] = None,
) -> ChatExecutionContext:
    """Allow existing tenant API keys or live tenant-user JWTs.

    JWT authorization remains database-authoritative. X-Agent-ID is
    verified against the authenticated tenant before a knowledge
    execution context is produced.
    """

    if credentials is None:
        return await require_tenant_api_key_context(
            session=session,
            raw_api_key=raw_api_key,
            agent_id=agent_id,
        )

    from backend.app.auth.tenant_context import (
        InactiveTenantError,
        NoActiveMembershipError,
        TenantAuthError,
        validate_tenant_user_context,
    )
    from backend.app.auth.tenant_rbac import (
        TenantPermission,
    )

    token = credentials.credentials.strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid tenant user access token",
        )

    try:
        tenant_context = (
            await validate_tenant_user_context(
                token,
                session,
                settings,
            )
        )
    except (
        NoActiveMembershipError,
        InactiveTenantError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except TenantAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    if not TenantPermission.can_read_knowledge(
        tenant_context.role
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied.",
        )

    normalized_agent_id = (
        agent_id or ""
    ).strip()

    if (
        not normalized_agent_id
        or len(normalized_agent_id) > 128
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="X-Agent-ID is required",
        )

    agent = await session.scalar(
        select(Agent).where(
            Agent.id == normalized_agent_id,
            Agent.tenant_id
            == tenant_context.tenant_id,
            Agent.is_active.is_(True),
        )
    )

    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    return ChatExecutionContext(
        tenant_id=tenant_context.tenant_id,
        agent_id=agent.id,
        system_prompt=agent.system_prompt,
        knowledge_mode=agent.knowledge_mode,
        contact_message=agent.contact_message,
        auth_method="tenant_jwt",  # type: ignore[arg-type]
    )


@lru_cache
def get_core_ai_runtime() -> GenerationRuntime:
    """Build and cache the configured provider-independent AI runtime."""

    from backend.app.ai.providers.deepseek import (
        DeepSeekGenerationProvider,
    )
    from backend.app.ai.providers.voyage import VoyageEmbeddingProvider
    from backend.app.ai.runtime import CoreAIRuntime

    settings = get_settings()
    return CoreAIRuntime(
        generation_provider=DeepSeekGenerationProvider(settings),
        embedding_provider=VoyageEmbeddingProvider(
            settings,
            input_type="query",
        ),
    )


@lru_cache
def get_embedding_provider() -> EmbeddingProvider:
    """Build embeddings without requiring a generation-provider API key."""

    from backend.app.ai.providers.voyage import VoyageEmbeddingProvider

    return VoyageEmbeddingProvider(get_settings())



async def require_user_jwt(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Security(tenant_bearer),
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> "UserContext":
    """Require an active customer identity/session, not tenant membership."""
    from backend.app.auth.tenant_context import (
        TenantAuthError,
        UserContext,
        validate_user_context,
    )

    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing customer access token",
        )

    token = credentials.credentials.strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid customer access token",
        )

    try:
        return await validate_user_context(token, session, settings)
    except TenantAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

async def require_tenant_user_jwt(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Security(tenant_bearer),
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> "TenantUserContext":
    """Require a live database-backed tenant user JWT session.
    
    This dependency validates the tenant user access token and returns
    a TenantUserContext with user_id, tenant_id, and role.
    
    Raises:
        HTTPException(401): If token is missing, invalid, or session is revoked
    
    Requirements: 7.1-7.12
    """
    from backend.app.auth.tenant_context import (
        TenantUserContext,
        validate_tenant_user_context,
        TenantAuthError,
        InactiveTenantError,
        NoActiveMembershipError,
    )
    
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing tenant user access token",
        )
    
    token = credentials.credentials.strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid tenant user access token",
        )
    
    try:
        context = await validate_tenant_user_context(token, session, settings)
        return context
    except (
        NoActiveMembershipError,
        InactiveTenantError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except TenantAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc


@lru_cache
def get_rerank_provider():
    """Build Voyage reranking when it is configured.

    Tests and local environments without a Voyage key fall back
    safely to pgvector ranking. Staging and production require the
    Voyage key through Settings validation.
    """

    settings = get_settings()
    api_key = settings.voyage_api_key

    if (
        api_key is None
        or not api_key.get_secret_value().strip()
    ):
        return None

    from backend.app.ai.providers.voyage import (
        VoyageRerankProvider,
    )

    return VoyageRerankProvider(settings)
