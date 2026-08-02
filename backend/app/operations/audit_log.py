"""Data access layer for admin audit events.

This module provides repository functions for creating and querying
audit log entries. All audit events are append-only - no updates or
deletes are permitted.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import AdminAuditEvent


async def create_audit_event(
    session: AsyncSession,
    *,
    actor_admin_id: str | None,
    actor_username: str,
    actor_role: str,
    action: str,
    tenant_id: str | None,
    resource_type: str,
    resource_id: str | None,
    changed_fields: dict[str, Any] | None,
    metadata: dict[str, Any] | None,
    ip_address: str | None,
    request_id: str | None,
    success: bool,
    error_message: str | None = None,
) -> AdminAuditEvent:
    """Create a new audit event record.
    
    This is an append-only operation. Once created, audit events
    cannot be modified or deleted.
    
    Args:
        session: Database session
        actor_admin_id: ID of the admin performing the action (optional)
        actor_username: Username of the admin
        actor_role: Role of the admin (super_admin, auditor, operator)
        action: Action performed (e.g., 'tenant.deleted')
        tenant_id: Associated tenant ID if applicable
        resource_type: Type of resource affected (e.g., 'tenant', 'agent')
        resource_id: ID of the affected resource
        changed_fields: Dictionary of fields that were changed
        metadata: Additional context data
        ip_address: IP address of the request
        request_id: Unique request identifier for tracing
        success: Whether the operation succeeded
        error_message: Error message if the operation failed
    
    Returns:
        The created audit event
    """
    event = AdminAuditEvent(
        id=str(uuid.uuid4()),
        actor_admin_id=actor_admin_id,
        actor_username=actor_username,
        actor_role=actor_role,
        action=action,
        tenant_id=tenant_id,
        resource_type=resource_type,
        resource_id=resource_id,
        changed_fields=changed_fields,
        metadata_json=metadata,
        ip_address=ip_address,
        request_id=request_id,
        success=success,
        error_message=error_message,
    )
    session.add(event)
    await session.flush()
    await session.refresh(event)
    return event


async def list_audit_events(
    session: AsyncSession,
    *,
    actor_admin_id: str | None = None,
    action: str | None = None,
    tenant_id: str | None = None,
    resource_type: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
    skip: int = 0,
    limit: int = 100,
) -> list[AdminAuditEvent]:
    """List audit events with optional filtering.
    
    Args:
        session: Database session
        actor_admin_id: Filter by admin ID
        action: Filter by action type
        tenant_id: Filter by tenant
        resource_type: Filter by resource type
        start_date: Filter events after this date
        end_date: Filter events before this date
        skip: Number of records to skip (pagination)
        limit: Maximum number of records to return
    
    Returns:
        List of matching audit events, ordered by created_at desc
    """
    query = select(AdminAuditEvent)
    
    if actor_admin_id is not None:
        query = query.where(AdminAuditEvent.actor_admin_id == actor_admin_id)
    
    if action is not None:
        query = query.where(AdminAuditEvent.action == action)
    
    if tenant_id is not None:
        query = query.where(AdminAuditEvent.tenant_id == tenant_id)
    
    if resource_type is not None:
        query = query.where(AdminAuditEvent.resource_type == resource_type)
    
    if start_date is not None:
        query = query.where(AdminAuditEvent.created_at >= start_date)
    
    if end_date is not None:
        query = query.where(AdminAuditEvent.created_at <= end_date)
    
    query = (
        query.order_by(AdminAuditEvent.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    
    result = await session.execute(query)
    return list(result.scalars().all())


async def count_audit_events(
    session: AsyncSession,
    *,
    actor_admin_id: str | None = None,
    action: str | None = None,
    tenant_id: str | None = None,
    resource_type: str | None = None,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> int:
    """Count audit events matching the given filters.
    
    Args:
        session: Database session
        actor_admin_id: Filter by admin ID
        action: Filter by action type
        tenant_id: Filter by tenant
        resource_type: Filter by resource type
        start_date: Filter events after this date
        end_date: Filter events before this date
    
    Returns:
        Count of matching events
    """
    query = select(func.count()).select_from(AdminAuditEvent)
    
    if actor_admin_id is not None:
        query = query.where(AdminAuditEvent.actor_admin_id == actor_admin_id)
    
    if action is not None:
        query = query.where(AdminAuditEvent.action == action)
    
    if tenant_id is not None:
        query = query.where(AdminAuditEvent.tenant_id == tenant_id)
    
    if resource_type is not None:
        query = query.where(AdminAuditEvent.resource_type == resource_type)
    
    if start_date is not None:
        query = query.where(AdminAuditEvent.created_at >= start_date)
    
    if end_date is not None:
        query = query.where(AdminAuditEvent.created_at <= end_date)
    
    result = await session.execute(query)
    return result.scalar_one()


async def get_audit_event_by_id(
    session: AsyncSession,
    event_id: str,
) -> AdminAuditEvent | None:
    """Retrieve a single audit event by its ID.
    
    Args:
        session: Database session
        event_id: The audit event ID
    
    Returns:
        The audit event if found, None otherwise
    """
    result = await session.execute(
        select(AdminAuditEvent).where(AdminAuditEvent.id == event_id)
    )
    return result.scalar_one_or_none()
