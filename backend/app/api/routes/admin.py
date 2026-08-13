"""Temporary internal administrative lifecycle API."""

from __future__ import annotations

import logging
from typing import Annotated
from uuid import uuid4

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import require_admin_access, require_permission
from backend.app.api.schemas.admin import (
    AgentAdminCreate,
    AgentAdminResponse,
    AgentConfigResponse,
    AgentConfigUpdate,
    ApiKeyAdminResponse,
    LifecycleStatusUpdate,
    RevokeAllApiKeysResponse,
    TenantAdminCreate,
    TenantAdminResponse,
)
from backend.app.auth.admin_context import AdminContext
from backend.app.core.client_ip import get_client_ip
from backend.app.core.config import Settings, get_settings
from backend.app.db.base import get_db
from backend.app.db.models import Tenant
from backend.app.infrastructure.database.tenant_repositories import (
    TenantScopedAgentRepository,
)
from backend.app.infrastructure.storage import LocalUploadStorage
from backend.app.operations.admin_lifecycle import (
    AdminLifecycleConflictError,
    AdminLifecycleValidationError,
    AdminResourceNotFoundError,
    delete_agent,
    delete_conversation,
    delete_tenant,
    list_agents,
    list_api_keys,
    list_tenants,
    require_tenant,
    revoke_all_api_keys,
    revoke_api_key,
    set_agent_active,
    set_tenant_active,
    update_agent_config,
)
from backend.app.services.audit import AuditService

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin_access)],
)
LOGGER = logging.getLogger(__name__)


def _tenant_response(item) -> TenantAdminResponse:
    return TenantAdminResponse(
        id=item.id,
        name=item.name,
        is_active=item.is_active,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _agent_response(item) -> AgentAdminResponse:
    return AgentAdminResponse(
        id=item.id,
        tenant_id=item.tenant_id,
        name=item.name,
        is_active=item.is_active,
        knowledge_mode=item.knowledge_mode,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )



def _agent_config_response(item) -> AgentConfigResponse:
    return AgentConfigResponse(
        id=item.id,
        tenant_id=item.tenant_id,
        name=item.name,
        system_prompt=item.system_prompt,
        knowledge_mode=item.knowledge_mode,
        contact_message=item.contact_message,
        is_active=item.is_active,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def _api_key_response(item) -> ApiKeyAdminResponse:
    return ApiKeyAdminResponse(
        key_id=item.key_id,
        tenant_id=item.tenant_id,
        name=item.name,
        is_active=item.is_active,
        created_at=item.created_at,
        expires_at=item.expires_at,
        revoked_at=item.revoked_at,
        last_used_at=item.last_used_at,
    )


def _not_found(exc: AdminResourceNotFoundError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=str(exc),
    )


def _conflict(exc: AdminLifecycleConflictError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=str(exc),
    )


async def _cleanup_storage(
    settings: Settings,
    storage_keys: tuple[str, ...],
) -> None:
    storage = LocalUploadStorage(settings.upload_storage_root)
    for storage_key in storage_keys:
        try:
            await storage.delete(storage_key)
        except Exception:
            LOGGER.exception(
                "Could not delete retained upload object %s",
                storage_key,
            )


async def _audit_mutation(
    session: AsyncSession,
    *,
    context: AdminContext | None,
    request: Request,
    settings: Settings,
    event_type: str,
    target_type: str,
    target_id: str,
    detail: dict | None = None,
) -> None:
    await AuditService.write(
        session,
        event_type=event_type,
        outcome="success",
        admin_id=context.admin_id if context is not None else None,
        target_type=target_type,
        target_id=target_id,
        client_ip=get_client_ip(request, settings),
        detail=detail,
    )


@router.post(
    "/tenants",
    response_model=TenantAdminResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("tenants:write"))],
)
async def create_managed_tenant(
    payload: TenantAdminCreate,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    context: Annotated[
        AdminContext | None,
        Depends(require_admin_access),
    ],
) -> TenantAdminResponse:
    tenant = Tenant(
        id=str(uuid4()),
        name=payload.name,
        is_active=payload.is_active,
    )
    session.add(tenant)
    await session.flush()

    await _audit_mutation(
        session,
        context=context,
        request=request,
        settings=settings,
        event_type="tenant_created",
        target_type="tenant",
        target_id=tenant.id,
        detail={
            "name": tenant.name,
            "is_active": tenant.is_active,
            "managed_by_admin": True,
        },
    )
    await session.commit()
    await session.refresh(tenant)
    return _tenant_response(tenant)


@router.get("/tenants", response_model=list[TenantAdminResponse],
            dependencies=[Depends(require_permission("tenants:read"))])
async def get_tenants(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[TenantAdminResponse]:
    return [_tenant_response(item) for item in await list_tenants(session)]


@router.get(
    "/tenants/{tenant_id}",
    response_model=TenantAdminResponse,
    dependencies=[Depends(require_permission("tenants:read"))],
)
async def get_tenant(
    tenant_id: str,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TenantAdminResponse:
    try:
        item = await require_tenant(session, tenant_id)
    except AdminResourceNotFoundError as exc:
        raise _not_found(exc) from exc
    return _tenant_response(item)


@router.patch(
    "/tenants/{tenant_id}/status",
    response_model=TenantAdminResponse,
    dependencies=[Depends(require_permission("tenants:write"))],
)
async def update_tenant_status(
    tenant_id: str,
    payload: LifecycleStatusUpdate,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    context: Annotated[
        AdminContext | None,
        Depends(require_admin_access),
    ],
) -> TenantAdminResponse:
    try:
        item = await set_tenant_active(
            session,
            tenant_id=tenant_id,
            is_active=payload.is_active,
        )
        await _audit_mutation(
            session,
            context=context,
            request=request,
            settings=settings,
            event_type="tenant_status_changed",
            target_type="tenant",
            target_id=tenant_id,
            detail={"is_active": payload.is_active},
        )
        await session.commit()
        await session.refresh(item)
    except AdminResourceNotFoundError as exc:
        await session.rollback()
        raise _not_found(exc) from exc
    return _tenant_response(item)


@router.delete(
    "/tenants/{tenant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("tenants:delete"))],
)
async def permanently_delete_tenant(
    tenant_id: str,
    confirm: Annotated[str, Query(min_length=1, max_length=128)],
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    context: Annotated[
        AdminContext | None,
        Depends(require_admin_access),
    ],
) -> Response:
    if confirm != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Confirmation must exactly match tenant_id",
        )
    try:
        result = await delete_tenant(session, tenant_id=tenant_id)
        await _audit_mutation(
            session,
            context=context,
            request=request,
            settings=settings,
            event_type="tenant_deleted",
            target_type="tenant",
            target_id=tenant_id,
        )
        await session.commit()
    except AdminResourceNotFoundError as exc:
        await session.rollback()
        raise _not_found(exc) from exc
    except AdminLifecycleConflictError as exc:
        await session.rollback()
        raise _conflict(exc) from exc
    await _cleanup_storage(settings, result.storage_keys)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/tenants/{tenant_id}/agents",
    response_model=AgentAdminResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("agents:write"))],
)
async def create_managed_agent(
    tenant_id: str,
    payload: AgentAdminCreate,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    context: Annotated[
        AdminContext | None,
        Depends(require_admin_access),
    ],
) -> AgentAdminResponse:
    try:
        await require_tenant(session, tenant_id)
        repo = TenantScopedAgentRepository(session)
        agent = await repo.create(
            tenant_id=tenant_id,
            name=payload.name,
            system_prompt=payload.system_prompt,
            knowledge_mode=payload.knowledge_mode,
            contact_message=payload.contact_message,
        )
        await _audit_mutation(
            session,
            context=context,
            request=request,
            settings=settings,
            event_type="agent_created",
            target_type="agent",
            target_id=agent.id,
            detail={
                "tenant_id": tenant_id,
                "knowledge_mode": payload.knowledge_mode,
                "managed_by_admin": True,
            },
        )
        await session.commit()
        await session.refresh(agent)
    except AdminResourceNotFoundError as exc:
        await session.rollback()
        raise _not_found(exc) from exc

    return _agent_response(agent)


@router.get(
    "/tenants/{tenant_id}/agents",
    response_model=list[AgentAdminResponse],
    dependencies=[Depends(require_permission("agents:read"))],
)
async def get_agents(
    tenant_id: str,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[AgentAdminResponse]:
    try:
        items = await list_agents(session, tenant_id=tenant_id)
    except AdminResourceNotFoundError as exc:
        raise _not_found(exc) from exc
    return [_agent_response(item) for item in items]


@router.patch(
    "/tenants/{tenant_id}/agents/{agent_id}/config",
    response_model=AgentConfigResponse,
    dependencies=[Depends(require_permission("agents:write"))],
)
async def update_agent_configuration(
    tenant_id: str,
    agent_id: str,
    payload: AgentConfigUpdate,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    context: Annotated[
        AdminContext | None,
        Depends(require_admin_access),
    ],
) -> AgentConfigResponse:
    """Update editable configuration for one tenant-scoped agent."""

    try:
        item = await update_agent_config(
            session,
            tenant_id=tenant_id,
            agent_id=agent_id,
            update=payload,
        )

        changed_fields = sorted(payload.model_fields_set)

        await _audit_mutation(
            session,
            context=context,
            request=request,
            settings=settings,
            event_type="agent_config_updated",
            target_type="agent",
            target_id=agent_id,
            detail={
                "tenant_id": tenant_id,
                "changed_fields": changed_fields,
            },
        )

        await session.commit()
        await session.refresh(item)

    except AdminLifecycleValidationError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc

    except AdminResourceNotFoundError as exc:
        await session.rollback()
        raise _not_found(exc) from exc

    return _agent_config_response(item)



@router.patch(
    "/tenants/{tenant_id}/agents/{agent_id}/status",
    response_model=AgentAdminResponse,
    dependencies=[Depends(require_permission("agents:write"))],
)
async def update_agent_status(
    tenant_id: str,
    agent_id: str,
    payload: LifecycleStatusUpdate,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    context: Annotated[
        AdminContext | None,
        Depends(require_admin_access),
    ],
) -> AgentAdminResponse:
    try:
        item = await set_agent_active(
            session,
            tenant_id=tenant_id,
            agent_id=agent_id,
            is_active=payload.is_active,
        )
        await _audit_mutation(
            session,
            context=context,
            request=request,
            settings=settings,
            event_type="agent_status_changed",
            target_type="agent",
            target_id=agent_id,
            detail={"tenant_id": tenant_id, "is_active": payload.is_active},
        )
        await session.commit()
        await session.refresh(item)
    except AdminResourceNotFoundError as exc:
        await session.rollback()
        raise _not_found(exc) from exc
    return _agent_response(item)


@router.delete(
    "/tenants/{tenant_id}/agents/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("agents:delete"))],
)
async def permanently_delete_agent(
    tenant_id: str,
    agent_id: str,
    confirm: Annotated[str, Query(min_length=1, max_length=128)],
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    context: Annotated[
        AdminContext | None,
        Depends(require_admin_access),
    ],
) -> Response:
    if confirm != agent_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Confirmation must exactly match agent_id",
        )
    try:
        result = await delete_agent(
            session,
            tenant_id=tenant_id,
            agent_id=agent_id,
        )
        await _audit_mutation(
            session,
            context=context,
            request=request,
            settings=settings,
            event_type="agent_deleted",
            target_type="agent",
            target_id=agent_id,
            detail={"tenant_id": tenant_id},
        )
        await session.commit()
    except AdminResourceNotFoundError as exc:
        await session.rollback()
        raise _not_found(exc) from exc
    except AdminLifecycleConflictError as exc:
        await session.rollback()
        raise _conflict(exc) from exc
    await _cleanup_storage(settings, result.storage_keys)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/tenants/{tenant_id}/api-keys",
    response_model=list[ApiKeyAdminResponse],
    dependencies=[Depends(require_permission("api_keys:read"))],
)
async def get_api_keys(
    tenant_id: str,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[ApiKeyAdminResponse]:
    try:
        items = await list_api_keys(session, tenant_id=tenant_id)
    except AdminResourceNotFoundError as exc:
        raise _not_found(exc) from exc
    return [_api_key_response(item) for item in items]


@router.post(
    "/tenants/{tenant_id}/api-keys/{key_id}/revoke",
    response_model=ApiKeyAdminResponse,
    dependencies=[Depends(require_permission("api_keys:revoke"))],
)
async def revoke_one_api_key(
    tenant_id: str,
    key_id: str,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    context: Annotated[
        AdminContext | None,
        Depends(require_admin_access),
    ],
) -> ApiKeyAdminResponse:
    try:
        item = await revoke_api_key(
            session,
            tenant_id=tenant_id,
            key_id=key_id,
        )
        await _audit_mutation(
            session,
            context=context,
            request=request,
            settings=settings,
            event_type="api_key_revoked",
            target_type="api_key",
            target_id=key_id,
            detail={"tenant_id": tenant_id},
        )
        await session.commit()
        await session.refresh(item)
    except AdminResourceNotFoundError as exc:
        await session.rollback()
        raise _not_found(exc) from exc
    return _api_key_response(item)


@router.post(
    "/tenants/{tenant_id}/api-keys/revoke-all",
    response_model=RevokeAllApiKeysResponse,
    dependencies=[Depends(require_permission("api_keys:revoke"))],
)
async def revoke_tenant_api_keys(
    tenant_id: str,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    context: Annotated[
        AdminContext | None,
        Depends(require_admin_access),
    ],
) -> RevokeAllApiKeysResponse:
    try:
        revoked_count = await revoke_all_api_keys(
            session,
            tenant_id=tenant_id,
        )
        await _audit_mutation(
            session,
            context=context,
            request=request,
            settings=settings,
            event_type="api_keys_revoked_all",
            target_type="tenant",
            target_id=tenant_id,
            detail={"revoked_count": revoked_count},
        )
        await session.commit()
    except AdminResourceNotFoundError as exc:
        await session.rollback()
        raise _not_found(exc) from exc
    return RevokeAllApiKeysResponse(revoked_count=revoked_count)


@router.delete(
    "/tenants/{tenant_id}/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("conversations:delete"))],
)
async def permanently_delete_conversation(
    tenant_id: str,
    conversation_id: str,
    request: Request,
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    context: Annotated[
        AdminContext | None,
        Depends(require_admin_access),
    ],
) -> Response:
    try:
        await delete_conversation(
            session,
            tenant_id=tenant_id,
            conversation_id=conversation_id,
        )
        await _audit_mutation(
            session,
            context=context,
            request=request,
            settings=settings,
            event_type="conversation_deleted",
            target_type="conversation",
            target_id=conversation_id,
            detail={"tenant_id": tenant_id},
        )
        await session.commit()
    except AdminResourceNotFoundError as exc:
        await session.rollback()
        raise _not_found(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
