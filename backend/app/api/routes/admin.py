"""Temporary internal administrative lifecycle API."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Response,
    status,
)
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import require_admin_access, require_permission
from backend.app.api.schemas.admin import (
    AgentAdminResponse,
    ApiKeyAdminResponse,
    LifecycleStatusUpdate,
    RevokeAllApiKeysResponse,
    TenantAdminResponse,
)
from backend.app.core.config import Settings, get_settings
from backend.app.db.base import get_db
from backend.app.infrastructure.storage import LocalUploadStorage
from backend.app.operations.admin_lifecycle import (
    AdminLifecycleConflictError,
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
)

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
    session: Annotated[AsyncSession, Depends(get_db)],
) -> TenantAdminResponse:
    try:
        item = await set_tenant_active(
            session,
            tenant_id=tenant_id,
            is_active=payload.is_active,
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
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> Response:
    if confirm != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Confirmation must exactly match tenant_id",
        )
    try:
        result = await delete_tenant(session, tenant_id=tenant_id)
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
    "/tenants/{tenant_id}/agents/{agent_id}/status",
    response_model=AgentAdminResponse,
    dependencies=[Depends(require_permission("agents:write"))],
)
async def update_agent_status(
    tenant_id: str,
    agent_id: str,
    payload: LifecycleStatusUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AgentAdminResponse:
    try:
        item = await set_agent_active(
            session,
            tenant_id=tenant_id,
            agent_id=agent_id,
            is_active=payload.is_active,
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
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
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
    session: Annotated[AsyncSession, Depends(get_db)],
) -> ApiKeyAdminResponse:
    try:
        item = await revoke_api_key(
            session,
            tenant_id=tenant_id,
            key_id=key_id,
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
    session: Annotated[AsyncSession, Depends(get_db)],
) -> RevokeAllApiKeysResponse:
    try:
        revoked_count = await revoke_all_api_keys(
            session,
            tenant_id=tenant_id,
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
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    try:
        await delete_conversation(
            session,
            tenant_id=tenant_id,
            conversation_id=conversation_id,
        )
        await session.commit()
    except AdminResourceNotFoundError as exc:
        await session.rollback()
        raise _not_found(exc) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
