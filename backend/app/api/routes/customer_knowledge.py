"""Customer-facing tenant-wide Knowledge Base routes."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import require_tenant_user_jwt
from backend.app.api.routes.knowledge import _knowledge_response
from backend.app.api.schemas.knowledge import KnowledgeBaseResponse
from backend.app.auth.tenant_context import TenantUserContext
from backend.app.auth.tenant_rbac import TenantPermission, require_tenant_permission
from backend.app.db.base import get_db
from backend.app.infrastructure.database.repositories import (
    SQLAlchemyKnowledgeBaseRepository,
)


router = APIRouter(tags=["customer-knowledge"])


@router.get(
    "/api/customer/knowledge-bases",
    response_model=list[KnowledgeBaseResponse],
    dependencies=[
        Depends(require_tenant_permission(TenantPermission.can_read_knowledge))
    ],
)
async def list_customer_knowledge_bases(
    context: Annotated[TenantUserContext, Depends(require_tenant_user_jwt)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[KnowledgeBaseResponse]:
    repository = SQLAlchemyKnowledgeBaseRepository(session)
    items = await repository.list_by_tenant(context.tenant_id)
    return [_knowledge_response(item) for item in items]


@router.put(
    "/api/customer/agents/{agent_id}/knowledge-bases/{knowledge_base_id}",
    response_model=KnowledgeBaseResponse,
    dependencies=[
        Depends(require_tenant_permission(TenantPermission.can_manage_knowledge))
    ],
)
async def assign_customer_knowledge_base(
    agent_id: str,
    knowledge_base_id: str,
    context: Annotated[TenantUserContext, Depends(require_tenant_user_jwt)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> KnowledgeBaseResponse:
    repository = SQLAlchemyKnowledgeBaseRepository(session)
    assigned = await repository.assign_to_agent(
        knowledge_base_id=knowledge_base_id,
        agent_id=agent_id,
        tenant_id=context.tenant_id,
    )
    if not assigned:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent or knowledge base not found.",
        )

    item = await repository.get_by_id(knowledge_base_id, context.tenant_id)
    if item is None:  # Defensive: the scoped assignment succeeded above.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Knowledge base not found.",
        )
    await session.commit()
    return _knowledge_response(item)
