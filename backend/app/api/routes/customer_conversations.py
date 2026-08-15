"""Tenant-safe customer conversation read API."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import (
    require_tenant_user_jwt,
)
from backend.app.auth.tenant_context import (
    TenantUserContext,
)
from backend.app.auth.tenant_rbac import (
    TenantPermission,
    require_tenant_permission,
)
from backend.app.db.base import get_db
from backend.app.db.models import (
    Agent,
    Conversation,
    Message,
)


router = APIRouter(
    prefix="/api/customer/conversations",
    tags=["customer-conversations"],
)

can_read_conversations = (
    require_tenant_permission(
        TenantPermission.can_read_conversations
    )
)


class ConversationResponse(BaseModel):
    id: str
    tenant_id: str
    agent_id: str
    agent_name: str
    user_identifier: str | None
    metadata: dict[str, Any] | None
    message_count: int
    user_message_count: int
    assistant_message_count: int
    last_message_role: str | None
    last_message_preview: str | None
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    items: list[ConversationResponse]
    total: int
    limit: int
    offset: int


class MessageResponse(BaseModel):
    id: str
    tenant_id: str
    conversation_id: str
    role: str
    content: str
    metadata: dict[str, Any] | None
    created_at: datetime


class MessageListResponse(BaseModel):
    items: list[MessageResponse]
    total: int
    limit: int
    offset: int


async def _conversation_response(
    session: AsyncSession,
    conversation: Conversation,
) -> ConversationResponse:
    agent_name = await session.scalar(
        select(Agent.name).where(
            Agent.tenant_id
            == conversation.tenant_id,
            Agent.id
            == conversation.agent_id,
        )
    )

    messages = list(
        (
            await session.scalars(
                select(Message)
                .where(
                    Message.tenant_id
                    == conversation.tenant_id,
                    Message.conversation_id
                    == conversation.id,
                )
                .order_by(
                    Message.created_at,
                    Message.id,
                )
            )
        ).all()
    )

    last = (
        messages[-1]
        if messages
        else None
    )

    return ConversationResponse(
        id=conversation.id,
        tenant_id=conversation.tenant_id,
        agent_id=conversation.agent_id,
        agent_name=(
            agent_name
            or conversation.agent_id
        ),
        user_identifier=(
            conversation.user_identifier
        ),
        metadata=(
            conversation.metadata_json
        ),
        message_count=len(messages),
        user_message_count=sum(
            item.role == "user"
            for item in messages
        ),
        assistant_message_count=sum(
            item.role == "assistant"
            for item in messages
        ),
        last_message_role=(
            last.role if last else None
        ),
        last_message_preview=(
            last.content[:500]
            if last
            else None
        ),
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


async def _owned_conversation(
    session: AsyncSession,
    tenant_id: str,
    conversation_id: str,
) -> Conversation:
    conversation = await session.scalar(
        select(Conversation).where(
            Conversation.tenant_id
            == tenant_id,
            Conversation.id
            == conversation_id,
        )
    )

    if conversation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )

    return conversation


@router.get(
    "",
    response_model=ConversationListResponse,
)
async def list_customer_conversations(
    context: Annotated[
        TenantUserContext,
        Depends(require_tenant_user_jwt),
    ],
    session: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
    _permission: Annotated[
        None,
        Depends(can_read_conversations),
    ],
    agent_id: str | None = Query(
        default=None,
        max_length=128,
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=200,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
) -> ConversationListResponse:
    conditions = [
        Conversation.tenant_id
        == context.tenant_id,
    ]

    if agent_id:
        conditions.append(
            Conversation.agent_id
            == agent_id,
        )

    total = int(
        await session.scalar(
            select(func.count())
            .select_from(Conversation)
            .where(*conditions)
        )
        or 0
    )

    rows = list(
        (
            await session.scalars(
                select(Conversation)
                .where(*conditions)
                .order_by(
                    Conversation.updated_at.desc(),
                    Conversation.id,
                )
                .limit(limit)
                .offset(offset)
            )
        ).all()
    )

    items = [
        await _conversation_response(
            session,
            item,
        )
        for item in rows
    ]

    return ConversationListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{conversation_id}",
    response_model=ConversationResponse,
)
async def get_customer_conversation(
    conversation_id: str,
    context: Annotated[
        TenantUserContext,
        Depends(require_tenant_user_jwt),
    ],
    session: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
    _permission: Annotated[
        None,
        Depends(can_read_conversations),
    ],
) -> ConversationResponse:
    conversation = await _owned_conversation(
        session,
        context.tenant_id,
        conversation_id,
    )

    return await _conversation_response(
        session,
        conversation,
    )


@router.get(
    "/{conversation_id}/messages",
    response_model=MessageListResponse,
)
async def list_customer_messages(
    conversation_id: str,
    context: Annotated[
        TenantUserContext,
        Depends(require_tenant_user_jwt),
    ],
    session: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
    _permission: Annotated[
        None,
        Depends(can_read_conversations),
    ],
    limit: int = Query(
        default=200,
        ge=1,
        le=500,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
) -> MessageListResponse:
    await _owned_conversation(
        session,
        context.tenant_id,
        conversation_id,
    )

    total = int(
        await session.scalar(
            select(func.count())
            .select_from(Message)
            .where(
                Message.tenant_id
                == context.tenant_id,
                Message.conversation_id
                == conversation_id,
            )
        )
        or 0
    )

    rows = list(
        (
            await session.scalars(
                select(Message)
                .where(
                    Message.tenant_id
                    == context.tenant_id,
                    Message.conversation_id
                    == conversation_id,
                )
                .order_by(
                    Message.created_at,
                    Message.id,
                )
                .limit(limit)
                .offset(offset)
            )
        ).all()
    )

    return MessageListResponse(
        items=[
            MessageResponse(
                id=item.id,
                tenant_id=item.tenant_id,
                conversation_id=(
                    item.conversation_id
                ),
                role=item.role,
                content=item.content,
                metadata=item.metadata_json,
                created_at=item.created_at,
            )
            for item in rows
        ],
        total=total,
        limit=limit,
        offset=offset,
    )
