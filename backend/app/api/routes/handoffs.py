"""Trusted, tenant- and agent-scoped handoff management API."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.api.dependencies import require_chat_context
from backend.app.api.schemas.handoffs import (
    HandoffResponse,
    HandoffUpdate,
)
from backend.app.auth.context import ChatExecutionContext
from backend.app.db.base import get_db
from backend.app.db.models import Handoff

router = APIRouter(prefix="/api/handoffs", tags=["handoffs"])


def _response(item: Handoff) -> HandoffResponse:
    return HandoffResponse(
        id=item.id,
        conversation_id=item.conversation_id,
        trigger_message_id=item.trigger_message_id,
        reason=item.reason,
        status=item.status,
        assigned_to=item.assigned_to,
        resolution_note=item.resolution_note,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


async def _get_scoped(
    session: AsyncSession,
    context: ChatExecutionContext,
    handoff_id: str,
) -> Handoff:
    item = await session.scalar(
        select(Handoff).where(
            Handoff.id == handoff_id,
            Handoff.tenant_id == context.tenant_id,
            Handoff.agent_id == context.agent_id,
        )
    )
    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Handoff not found",
        )
    return item


@router.get("", response_model=list[HandoffResponse])
async def list_handoffs(
    context: Annotated[
        ChatExecutionContext,
        Depends(require_chat_context),
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
    handoff_status: Annotated[
        Literal["open", "assigned", "closed"] | None,
        Query(alias="status"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> list[HandoffResponse]:
    """List handoffs inside the authenticated tenant and selected agent."""

    statement = select(Handoff).where(
        Handoff.tenant_id == context.tenant_id,
        Handoff.agent_id == context.agent_id,
    )
    if handoff_status is not None:
        statement = statement.where(Handoff.status == handoff_status)
    rows = list(
        (
            await session.scalars(
                statement.order_by(
                    Handoff.updated_at.desc(),
                    Handoff.id,
                ).limit(limit)
            )
        ).all()
    )
    return [_response(item) for item in rows]


@router.get("/{handoff_id}", response_model=HandoffResponse)
async def get_handoff(
    handoff_id: str,
    context: Annotated[
        ChatExecutionContext,
        Depends(require_chat_context),
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> HandoffResponse:
    """Return one scoped handoff without leaking cross-tenant existence."""

    return _response(await _get_scoped(session, context, handoff_id))


@router.patch("/{handoff_id}", response_model=HandoffResponse)
async def update_handoff(
    handoff_id: str,
    payload: HandoffUpdate,
    context: Annotated[
        ChatExecutionContext,
        Depends(require_chat_context),
    ],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> HandoffResponse:
    """Assign, reopen, or close one handoff."""

    if not payload.has_changes():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="At least one field is required",
        )
    item = await _get_scoped(session, context, handoff_id)
    if item.status == "closed" and payload.status not in {None, "closed"}:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Closed handoffs cannot be reopened",
        )

    if "assigned_to" in payload.model_fields_set:
        item.assigned_to = payload.assigned_to
    if "resolution_note" in payload.model_fields_set:
        item.resolution_note = payload.resolution_note
    if payload.status is not None:
        item.status = payload.status

    if item.status == "assigned" and not item.assigned_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="assigned_to is required for assigned handoffs",
        )
    item.updated_at = datetime.now(timezone.utc)
    await session.commit()
    return _response(item)
