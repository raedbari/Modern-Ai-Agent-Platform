"""Administrator read endpoints for tenant-scoped conversations."""

from __future__ import annotations

from collections import defaultdict
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import (
    require_admin_access,
    require_permission,
)
from backend.app.api.schemas.admin_conversations import (
    ConversationAdminListResponse,
    ConversationAdminResponse,
    MessageAdminListResponse,
    MessageAdminResponse,
)
from backend.app.db.base import get_db
from backend.app.db.models import (
    Agent,
    Conversation,
    Message,
)
from backend.app.operations.admin_lifecycle import (
    AdminResourceNotFoundError,
    require_agent,
    require_tenant,
)


router = APIRouter(
    prefix="/api/admin/tenants/{tenant_id}/conversations",
    tags=["admin-conversations"],
    dependencies=[
        Depends(require_admin_access),
    ],
)


def _not_found(
    detail: str,
) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=detail,
    )


def _preview(
    content: str | None,
    *,
    maximum: int = 240,
) -> str | None:
    if content is None:
        return None

    normalized = " ".join(
        content.split()
    ).strip()

    if not normalized:
        return None

    if len(normalized) <= maximum:
        return normalized

    return (
        normalized[: maximum - 1].rstrip()
        + "..."
    )


async def _require_conversation(
    session: AsyncSession,
    *,
    tenant_id: str,
    conversation_id: str,
) -> Conversation:
    conversation = await session.scalar(
        select(Conversation).where(
            Conversation.tenant_id == tenant_id,
            Conversation.id == conversation_id,
        )
    )

    if conversation is None:
        raise _not_found(
            "Conversation not found."
        )

    return conversation


async def _conversation_support_data(
    session: AsyncSession,
    *,
    tenant_id: str,
    conversation_ids: list[str],
) -> tuple[
    dict[str, dict[str, int]],
    dict[str, tuple[str, str]],
]:
    if not conversation_ids:
        return {}, {}

    role_counts: dict[
        str,
        dict[str, int],
    ] = defaultdict(
        lambda: defaultdict(int)
    )

    count_rows = (
        await session.execute(
            select(
                Message.conversation_id,
                Message.role,
                func.count(Message.id),
            )
            .where(
                Message.tenant_id == tenant_id,
                Message.conversation_id.in_(
                    conversation_ids
                ),
            )
            .group_by(
                Message.conversation_id,
                Message.role,
            )
        )
    ).all()

    for conversation_id, role, count in count_rows:
        role_counts[
            conversation_id
        ][role] = int(count)

    ranked_messages = (
        select(
            Message.conversation_id.label(
                "conversation_id"
            ),
            Message.role.label("role"),
            Message.content.label("content"),
            func.row_number()
            .over(
                partition_by=(
                    Message.conversation_id
                ),
                order_by=(
                    Message.created_at.desc(),
                    Message.id.desc(),
                ),
            )
            .label("row_number"),
        )
        .where(
            Message.tenant_id == tenant_id,
            Message.conversation_id.in_(
                conversation_ids
            ),
        )
        .subquery()
    )

    last_rows = (
        await session.execute(
            select(
                ranked_messages.c.conversation_id,
                ranked_messages.c.role,
                ranked_messages.c.content,
            ).where(
                ranked_messages.c.row_number == 1
            )
        )
    ).all()

    last_messages = {
        conversation_id: (
            role,
            content,
        )
        for (
            conversation_id,
            role,
            content,
        ) in last_rows
    }

    return role_counts, last_messages


def _conversation_response(
    conversation: Conversation,
    *,
    agent_name: str,
    role_counts: dict[str, int],
    last_message: tuple[str, str] | None,
) -> ConversationAdminResponse:
    message_count = sum(
        role_counts.values()
    )

    return ConversationAdminResponse(
        id=conversation.id,
        tenant_id=conversation.tenant_id,
        agent_id=conversation.agent_id,
        agent_name=agent_name,
        user_identifier=(
            conversation.user_identifier
        ),
        metadata=conversation.metadata_json,
        message_count=message_count,
        user_message_count=role_counts.get(
            "user",
            0,
        ),
        assistant_message_count=(
            role_counts.get(
                "assistant",
                0,
            )
        ),
        last_message_role=(
            last_message[0]
            if last_message is not None
            else None
        ),
        last_message_preview=(
            _preview(last_message[1])
            if last_message is not None
            else None
        ),
        created_at=conversation.created_at,
        updated_at=conversation.updated_at,
    )


@router.get(
    "",
    response_model=(
        ConversationAdminListResponse
    ),
    dependencies=[
        Depends(
            require_permission(
                "conversations:read"
            )
        )
    ],
)
async def list_admin_conversations(
    tenant_id: str,
    session: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
    agent_id: Annotated[
        str | None,
        Query(
            min_length=1,
            max_length=128,
        ),
    ] = None,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=200,
        ),
    ] = 100,
    offset: Annotated[
        int,
        Query(
            ge=0,
        ),
    ] = 0,
) -> ConversationAdminListResponse:
    try:
        await require_tenant(
            session,
            tenant_id,
        )

        if agent_id is not None:
            await require_agent(
                session,
                tenant_id=tenant_id,
                agent_id=agent_id,
            )
    except AdminResourceNotFoundError as exc:
        raise _not_found(
            str(exc)
        ) from exc

    filters = [
        Conversation.tenant_id == tenant_id,
    ]

    if agent_id is not None:
        filters.append(
            Conversation.agent_id == agent_id
        )

    total = int(
        await session.scalar(
            select(
                func.count(
                    Conversation.id
                )
            ).where(*filters)
        )
        or 0
    )

    rows = (
        await session.execute(
            select(
                Conversation,
                Agent.name,
            )
            .join(
                Agent,
                (
                    Agent.tenant_id
                    == Conversation.tenant_id
                )
                & (
                    Agent.id
                    == Conversation.agent_id
                ),
            )
            .where(*filters)
            .order_by(
                Conversation.updated_at.desc(),
                Conversation.created_at.desc(),
                Conversation.id,
            )
            .offset(offset)
            .limit(limit)
        )
    ).all()

    conversation_ids = [
        conversation.id
        for conversation, _ in rows
    ]

    role_counts, last_messages = (
        await _conversation_support_data(
            session,
            tenant_id=tenant_id,
            conversation_ids=(
                conversation_ids
            ),
        )
    )

    items = [
        _conversation_response(
            conversation,
            agent_name=agent_name,
            role_counts=role_counts.get(
                conversation.id,
                {},
            ),
            last_message=last_messages.get(
                conversation.id
            ),
        )
        for conversation, agent_name in rows
    ]

    return ConversationAdminListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{conversation_id}",
    response_model=ConversationAdminResponse,
    dependencies=[
        Depends(
            require_permission(
                "conversations:read"
            )
        )
    ],
)
async def read_admin_conversation(
    tenant_id: str,
    conversation_id: str,
    session: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
) -> ConversationAdminResponse:
    try:
        await require_tenant(
            session,
            tenant_id,
        )
    except AdminResourceNotFoundError as exc:
        raise _not_found(
            str(exc)
        ) from exc

    row = (
        await session.execute(
            select(
                Conversation,
                Agent.name,
            )
            .join(
                Agent,
                (
                    Agent.tenant_id
                    == Conversation.tenant_id
                )
                & (
                    Agent.id
                    == Conversation.agent_id
                ),
            )
            .where(
                Conversation.tenant_id
                == tenant_id,
                Conversation.id
                == conversation_id,
            )
        )
    ).one_or_none()

    if row is None:
        raise _not_found(
            "Conversation not found."
        )

    conversation, agent_name = row

    role_counts, last_messages = (
        await _conversation_support_data(
            session,
            tenant_id=tenant_id,
            conversation_ids=[
                conversation.id
            ],
        )
    )

    return _conversation_response(
        conversation,
        agent_name=agent_name,
        role_counts=role_counts.get(
            conversation.id,
            {},
        ),
        last_message=last_messages.get(
            conversation.id
        ),
    )


@router.get(
    "/{conversation_id}/messages",
    response_model=MessageAdminListResponse,
    dependencies=[
        Depends(
            require_permission(
                "conversations:read"
            )
        )
    ],
)
async def list_admin_conversation_messages(
    tenant_id: str,
    conversation_id: str,
    session: Annotated[
        AsyncSession,
        Depends(get_db),
    ],
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=500,
        ),
    ] = 200,
    offset: Annotated[
        int,
        Query(
            ge=0,
        ),
    ] = 0,
) -> MessageAdminListResponse:
    await _require_conversation(
        session,
        tenant_id=tenant_id,
        conversation_id=conversation_id,
    )

    total = int(
        await session.scalar(
            select(
                func.count(Message.id)
            ).where(
                Message.tenant_id
                == tenant_id,
                Message.conversation_id
                == conversation_id,
            )
        )
        or 0
    )

    messages = list(
        (
            await session.scalars(
                select(Message)
                .where(
                    Message.tenant_id
                    == tenant_id,
                    Message.conversation_id
                    == conversation_id,
                )
                .order_by(
                    Message.created_at,
                    Message.id,
                )
                .offset(offset)
                .limit(limit)
            )
        ).all()
    )

    return MessageAdminListResponse(
        items=[
            MessageAdminResponse(
                id=message.id,
                tenant_id=message.tenant_id,
                conversation_id=(
                    message.conversation_id
                ),
                role=message.role,
                content=message.content,
                metadata=message.metadata_json,
                created_at=message.created_at,
            )
            for message in messages
        ],
        total=total,
        limit=limit,
        offset=offset,
    )
