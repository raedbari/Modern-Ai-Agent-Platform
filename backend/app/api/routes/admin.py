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

from backend.app.api.dependencies import require_admin_access, AdminRole
from backend.app.api.schemas.admin import (
    AgentAdminResponse,
    ApiKeyAdminResponse,
    LifecycleStatusUpdate,
    RevokeAllApiKeysResponse,
    TenantAdminResponse,
)
from backend.app.core.config import Settings, get_settings
from backend.app.db.base import get_db
from backend.app.db.models import Agent
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
from backend.app.services import audit_log as audit_service

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin_access)],
)
LOGGER = logging.getLogger(__name__)


async def _log_audit_event(
    session: AsyncSession,
    auth_result: tuple[str, AdminRole],
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    tenant_id: str | None = None,
    changed_fields: dict | None = None,
    success: bool = True,
    error_message: str | None = None,
) -> None:
    """Helper to log audit events for admin operations.
    
    Args:
        session: Database session
        auth_result: Tuple of (admin_key, admin_role) from auth
        action: Action performed
        resource_type: Type of resource
        resource_id: ID of resource
        tenant_id: Tenant ID if applicable
        changed_fields: Fields that were changed
        success: Whether operation succeeded
        error_message: Error message if failed
    """
    _, admin_role = auth_result
    
    try:
        await audit_service.log_event(
            session,
            actor_admin_id=None,  # TODO: Extract from admin session when auth is implemented
            actor_username="admin",  # TODO: Extract from admin session
            actor_role=admin_role.value,
            action=action,
            tenant_id=tenant_id,
            resource_type=resource_type,
            resource_id=resource_id,
            changed_fields=changed_fields,
            ip_address=None,  # TODO: Extract from Request object
            request_id=None,  # TODO: Extract from Request object or generate
            success=success,
            error_message=error_message,
        )
    except Exception:
        # Don't fail the main operation if audit logging fails
        LOGGER.exception("Failed to create audit log for action: %s", action)


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


@router.get("/tenants", response_model=list[TenantAdminResponse])
async def get_tenants(
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[TenantAdminResponse]:
    return [_tenant_response(item) for item in await list_tenants(session)]


@router.get(
    "/tenants/{tenant_id}",
    response_model=TenantAdminResponse,
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
)
async def update_tenant_status(
    tenant_id: str,
    payload: LifecycleStatusUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
    auth_result: Annotated[tuple[str, AdminRole], Depends(require_admin_access)],
) -> TenantAdminResponse:
    try:
        old_item = await require_tenant(session, tenant_id)
        old_status = old_item.is_active
        
        item = await set_tenant_active(
            session,
            tenant_id=tenant_id,
            is_active=payload.is_active,
        )
        await session.commit()
        await session.refresh(item)
        
        # Log audit event
        await _log_audit_event(
            session,
            auth_result,
            action="tenant.status_changed",
            resource_type="tenant",
            resource_id=tenant_id,
            tenant_id=tenant_id,
            changed_fields={
                "is_active": {
                    "old": old_status,
                    "new": payload.is_active,
                }
            },
            success=True,
        )
        await session.commit()
    except AdminResourceNotFoundError as exc:
        await session.rollback()
        raise _not_found(exc) from exc
    except Exception as exc:
        await _log_audit_event(
            session,
            auth_result,
            action="tenant.status_changed",
            resource_type="tenant",
            resource_id=tenant_id,
            tenant_id=tenant_id,
            success=False,
            error_message=str(exc),
        )
        await session.rollback()
        raise
    return _tenant_response(item)


@router.delete(
    "/tenants/{tenant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def permanently_delete_tenant(
    tenant_id: str,
    confirm: Annotated[str, Query(min_length=1, max_length=128)],
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    auth_result: Annotated[tuple[str, AdminRole], Depends(require_admin_access)],
) -> Response:
    if confirm != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Confirmation must exactly match tenant_id",
        )
    try:
        result = await delete_tenant(session, tenant_id=tenant_id)
        await session.commit()
        
        # Log audit event
        await _log_audit_event(
            session,
            auth_result,
            action="tenant.deleted",
            resource_type="tenant",
            resource_id=tenant_id,
            tenant_id=tenant_id,
            success=True,
        )
        await session.commit()
    except AdminResourceNotFoundError as exc:
        await session.rollback()
        raise _not_found(exc) from exc
    except AdminLifecycleConflictError as exc:
        await session.rollback()
        raise _conflict(exc) from exc
    except Exception as exc:
        await _log_audit_event(
            session,
            auth_result,
            action="tenant.deleted",
            resource_type="tenant",
            resource_id=tenant_id,
            tenant_id=tenant_id,
            success=False,
            error_message=str(exc),
        )
        await session.rollback()
        raise
    await _cleanup_storage(settings, result.storage_keys)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/tenants/{tenant_id}/agents",
    response_model=list[AgentAdminResponse],
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
)
async def update_agent_status(
    tenant_id: str,
    agent_id: str,
    payload: LifecycleStatusUpdate,
    session: Annotated[AsyncSession, Depends(get_db)],
    auth_result: Annotated[tuple[str, AdminRole], Depends(require_admin_access)],
) -> AgentAdminResponse:
    try:
        # Get old status before update
        old_item = await session.get(Agent, agent_id)
        old_status = old_item.is_active if old_item else None
        
        item = await set_agent_active(
            session,
            tenant_id=tenant_id,
            agent_id=agent_id,
            is_active=payload.is_active,
        )
        await session.commit()
        await session.refresh(item)
        
        # Log audit event
        await _log_audit_event(
            session,
            auth_result,
            action="agent.status_changed",
            resource_type="agent",
            resource_id=agent_id,
            tenant_id=tenant_id,
            changed_fields={
                "is_active": {
                    "old": old_status,
                    "new": payload.is_active,
                }
            },
            success=True,
        )
        await session.commit()
    except AdminResourceNotFoundError as exc:
        await session.rollback()
        raise _not_found(exc) from exc
    except Exception as exc:
        await _log_audit_event(
            session,
            auth_result,
            action="agent.status_changed",
            resource_type="agent",
            resource_id=agent_id,
            tenant_id=tenant_id,
            success=False,
            error_message=str(exc),
        )
        await session.rollback()
        raise
    return _agent_response(item)


@router.delete(
    "/tenants/{tenant_id}/agents/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def permanently_delete_agent(
    tenant_id: str,
    agent_id: str,
    confirm: Annotated[str, Query(min_length=1, max_length=128)],
    session: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    auth_result: Annotated[tuple[str, AdminRole], Depends(require_admin_access)],
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
        
        # Log audit event
        await _log_audit_event(
            session,
            auth_result,
            action="agent.deleted",
            resource_type="agent",
            resource_id=agent_id,
            tenant_id=tenant_id,
            success=True,
        )
        await session.commit()
    except AdminResourceNotFoundError as exc:
        await session.rollback()
        raise _not_found(exc) from exc
    except AdminLifecycleConflictError as exc:
        await session.rollback()
        raise _conflict(exc) from exc
    except Exception as exc:
        await _log_audit_event(
            session,
            auth_result,
            action="agent.deleted",
            resource_type="agent",
            resource_id=agent_id,
            tenant_id=tenant_id,
            success=False,
            error_message=str(exc),
        )
        await session.rollback()
        raise
    await _cleanup_storage(settings, result.storage_keys)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/tenants/{tenant_id}/api-keys",
    response_model=list[ApiKeyAdminResponse],
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
)
async def revoke_one_api_key(
    tenant_id: str,
    key_id: str,
    session: Annotated[AsyncSession, Depends(get_db)],
    auth_result: Annotated[tuple[str, AdminRole], Depends(require_admin_access)],
) -> ApiKeyAdminResponse:
    try:
        item = await revoke_api_key(
            session,
            tenant_id=tenant_id,
            key_id=key_id,
        )
        await session.commit()
        await session.refresh(item)
        
        # Log audit event
        await _log_audit_event(
            session,
            auth_result,
            action="api_key.revoked",
            resource_type="api_key",
            resource_id=key_id,
            tenant_id=tenant_id,
            success=True,
        )
        await session.commit()
    except AdminResourceNotFoundError as exc:
        await session.rollback()
        raise _not_found(exc) from exc
    except Exception as exc:
        await _log_audit_event(
            session,
            auth_result,
            action="api_key.revoked",
            resource_type="api_key",
            resource_id=key_id,
            tenant_id=tenant_id,
            success=False,
            error_message=str(exc),
        )
        await session.rollback()
        raise
    return _api_key_response(item)


@router.post(
    "/tenants/{tenant_id}/api-keys/revoke-all",
    response_model=RevokeAllApiKeysResponse,
)
async def revoke_tenant_api_keys(
    tenant_id: str,
    session: Annotated[AsyncSession, Depends(get_db)],
    auth_result: Annotated[tuple[str, AdminRole], Depends(require_admin_access)],
) -> RevokeAllApiKeysResponse:
    try:
        revoked_count = await revoke_all_api_keys(
            session,
            tenant_id=tenant_id,
        )
        await session.commit()
        
        # Log audit event
        await _log_audit_event(
            session,
            auth_result,
            action="api_keys.bulk_revoked",
            resource_type="api_key",
            tenant_id=tenant_id,
            metadata={"revoked_count": revoked_count},
            success=True,
        )
        await session.commit()
    except AdminResourceNotFoundError as exc:
        await session.rollback()
        raise _not_found(exc) from exc
    except Exception as exc:
        await _log_audit_event(
            session,
            auth_result,
            action="api_keys.bulk_revoked",
            resource_type="api_key",
            tenant_id=tenant_id,
            success=False,
            error_message=str(exc),
        )
        await session.rollback()
        raise
    return RevokeAllApiKeysResponse(revoked_count=revoked_count)


@router.delete(
    "/tenants/{tenant_id}/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def permanently_delete_conversation(
    tenant_id: str,
    conversation_id: str,
    session: Annotated[AsyncSession, Depends(get_db)],
    auth_result: Annotated[tuple[str, AdminRole], Depends(require_admin_access)],
) -> Response:
    try:
        await delete_conversation(
            session,
            tenant_id=tenant_id,
            conversation_id=conversation_id,
        )
        await session.commit()
        
        # Log audit event
        await _log_audit_event(
            session,
            auth_result,
            action="conversation.deleted",
            resource_type="conversation",
            resource_id=conversation_id,
            tenant_id=tenant_id,
            success=True,
        )
        await session.commit()
    except AdminResourceNotFoundError as exc:
        await session.rollback()
        raise _not_found(exc) from exc
    except Exception as exc:
        await _log_audit_event(
            session,
            auth_result,
            action="conversation.deleted",
            resource_type="conversation",
            resource_id=conversation_id,
            tenant_id=tenant_id,
            success=False,
            error_message=str(exc),
        )
        await session.rollback()
        raise
    return Response(status_code=status.HTTP_204_NO_CONTENT)
