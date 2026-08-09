"""Customer-facing Agent API routes with JWT authentication."""

from __future__ import annotations

import logging
from typing import Annotated
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import require_tenant_user_jwt
from backend.app.auth.tenant_context import TenantUserContext
from backend.app.auth.tenant_rbac import TenantPermission, require_tenant_permission
from backend.app.db.base import get_db
from backend.app.infrastructure.database.tenant_repositories import (
    TenantScopedAgentRepository,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/customer/agents", tags=["customer-agents"])


# --- Schemas ---

class AgentCreateRequest(BaseModel):
    """Request schema for creating a new agent."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    system_prompt: str | None = Field(default=None, max_length=10_000)
    knowledge_mode: str = Field(default="preferred")
    contact_message: str | None = Field(default=None, max_length=1_000)

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: object) -> object:
        """Strip surrounding whitespace before length validation."""
        if isinstance(value, str):
            return value.strip()
        return value


class AgentUpdateRequest(BaseModel):
    """Request schema for updating an existing agent."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=255)
    system_prompt: str | None = Field(default=None, max_length=10_000)
    knowledge_mode: str | None = Field(default=None)
    contact_message: str | None = Field(default=None, max_length=1_000)

    @field_validator("name", mode="before")
    @classmethod
    def normalize_name(cls, value: object) -> object:
        """Strip surrounding whitespace before length validation."""
        if isinstance(value, str):
            return value.strip()
        return value


class AgentResponse(BaseModel):
    """Response schema for agent data."""

    id: str
    tenant_id: str
    name: str
    is_active: bool
    knowledge_mode: str
    system_prompt: str | None
    contact_message: str | None
    created_at: datetime
    updated_at: datetime


def _agent_response(agent) -> AgentResponse:
    """Convert database model to response schema."""
    return AgentResponse(
        id=agent.id,
        tenant_id=agent.tenant_id,
        name=agent.name,
        is_active=agent.is_active,
        knowledge_mode=agent.knowledge_mode,
        system_prompt=agent.system_prompt,
        contact_message=agent.contact_message,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
    )


# --- Routes ---

@router.post(
    "",
    response_model=AgentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_tenant_permission(TenantPermission.can_manage_agents))],
)
async def create_agent(
    request: AgentCreateRequest,
    context: Annotated[TenantUserContext, Depends(require_tenant_user_jwt)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AgentResponse:
    """
    Create a new agent for the authenticated tenant.
    
    Requires: knowledge_editor, tenant_admin, or tenant_owner role
    """
    repo = TenantScopedAgentRepository(session)
    
    agent = await repo.create(
        tenant_id=context.tenant_id,
        name=request.name,
        system_prompt=request.system_prompt,
        knowledge_mode=request.knowledge_mode,
        contact_message=request.contact_message,
    )
    
    logger.info(
        "Agent created",
        extra={
            "agent_id": agent.id,
            "tenant_id": context.tenant_id,
            "user_id": context.user_id,
        },
    )
    
    return _agent_response(agent)


@router.get(
    "",
    response_model=list[AgentResponse],
    dependencies=[Depends(require_tenant_permission(TenantPermission.can_read_agents))],
)
async def list_agents(
    context: Annotated[TenantUserContext, Depends(require_tenant_user_jwt)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[AgentResponse]:
    """
    List all agents for the authenticated tenant.
    
    Requires: Any approved role (tenant_owner, tenant_admin, knowledge_editor, conversation_viewer)
    """
    repo = TenantScopedAgentRepository(session)
    
    agents = await repo.list_by_tenant(context.tenant_id)
    
    return [_agent_response(agent) for agent in agents]


@router.get(
    "/{agent_id}",
    response_model=AgentResponse,
    dependencies=[Depends(require_tenant_permission(TenantPermission.can_read_agents))],
)
async def get_agent(
    agent_id: str,
    context: Annotated[TenantUserContext, Depends(require_tenant_user_jwt)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AgentResponse:
    """
    Get a specific agent by ID.
    
    Returns 404 if the agent doesn't exist or belongs to another tenant.
    Requires: Any approved role
    """
    repo = TenantScopedAgentRepository(session)
    
    agent = await repo.get_by_id(agent_id, context.tenant_id)
    
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )
    
    return _agent_response(agent)


@router.patch(
    "/{agent_id}",
    response_model=AgentResponse,
    dependencies=[Depends(require_tenant_permission(TenantPermission.can_manage_agents))],
)
async def update_agent(
    agent_id: str,
    request: AgentUpdateRequest,
    context: Annotated[TenantUserContext, Depends(require_tenant_user_jwt)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> AgentResponse:
    """
    Update an existing agent.
    
    Returns 404 if the agent doesn't exist or belongs to another tenant.
    Requires: knowledge_editor, tenant_admin, or tenant_owner role
    """
    repo = TenantScopedAgentRepository(session)
    
    # Build updates dict (only include fields that were provided)
    updates = {}
    if request.name is not None:
        updates["name"] = request.name
    if request.system_prompt is not None:
        updates["system_prompt"] = request.system_prompt
    if request.knowledge_mode is not None:
        updates["knowledge_mode"] = request.knowledge_mode
    if request.contact_message is not None:
        updates["contact_message"] = request.contact_message
    
    agent = await repo.update(agent_id, context.tenant_id, updates)
    
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )
    
    logger.info(
        "Agent updated",
        extra={
            "agent_id": agent_id,
            "tenant_id": context.tenant_id,
            "user_id": context.user_id,
            "updates": list(updates.keys()),
        },
    )
    
    return _agent_response(agent)


@router.delete(
    "/{agent_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_tenant_permission(TenantPermission.can_manage_agents))],
)
async def delete_agent(
    agent_id: str,
    context: Annotated[TenantUserContext, Depends(require_tenant_user_jwt)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    """
    Delete an agent.
    
    Returns 404 if the agent doesn't exist or belongs to another tenant.
    Requires: knowledge_editor, tenant_admin, or tenant_owner role
    """
    repo = TenantScopedAgentRepository(session)
    
    deleted = await repo.delete(agent_id, context.tenant_id)
    
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )
    
    logger.info(
        "Agent deleted",
        extra={
            "agent_id": agent_id,
            "tenant_id": context.tenant_id,
            "user_id": context.user_id,
        },
    )
    
    return Response(status_code=status.HTTP_204_NO_CONTENT)
