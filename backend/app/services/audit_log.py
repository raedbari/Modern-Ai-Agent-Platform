"""Business logic for audit logging with security sanitization.

This service ensures that sensitive data (passwords, tokens, secrets)
is never stored in audit logs. All data is sanitized before persistence.
"""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import AdminAuditEvent
from backend.app.operations import audit_log as audit_repo

LOGGER = logging.getLogger(__name__)

# Sensitive field patterns that should be redacted
SENSITIVE_FIELD_PATTERNS = {
    "password",
    "secret",
    "token",
    "key",
    "digest",
    "authorization",
    "credential",
    "api_key",
    "access_token",
    "refresh_token",
    "client_secret",
    "key_digest",
    "raw_key",
    "password_hash",
}

REDACTED_VALUE = "[REDACTED]"


def _is_sensitive_field(field_name: str) -> bool:
    """Check if a field name contains sensitive data patterns.
    
    Args:
        field_name: The field name to check (case-insensitive)
    
    Returns:
        True if the field is sensitive
    """
    field_lower = field_name.lower()
    return any(pattern in field_lower for pattern in SENSITIVE_FIELD_PATTERNS)


def _sanitize_dict(data: dict[str, Any] | None) -> dict[str, Any] | None:
    """Recursively sanitize a dictionary by redacting sensitive fields.
    
    Args:
        data: Dictionary to sanitize
    
    Returns:
        Sanitized dictionary with sensitive values redacted
    """
    if data is None:
        return None
    
    sanitized = {}
    for key, value in data.items():
        if _is_sensitive_field(key):
            sanitized[key] = REDACTED_VALUE
        elif isinstance(value, dict):
            sanitized[key] = _sanitize_dict(value)
        elif isinstance(value, list):
            sanitized[key] = [
                _sanitize_dict(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            sanitized[key] = value
    
    return sanitized


def _sanitize_changed_fields(
    changed_fields: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Sanitize changed fields to remove sensitive data.
    
    This is specifically for field change tracking where we want to
    preserve the structure but redact sensitive values.
    
    Args:
        changed_fields: Dictionary of changed fields with old/new values
    
    Returns:
        Sanitized dictionary
    """
    return _sanitize_dict(changed_fields)


def _sanitize_metadata(
    metadata: dict[str, Any] | None,
) -> dict[str, Any] | None:
    """Sanitize metadata to remove sensitive data.
    
    Args:
        metadata: Metadata dictionary
    
    Returns:
        Sanitized metadata
    """
    return _sanitize_dict(metadata)


async def log_event(
    session: AsyncSession,
    *,
    actor_admin_id: str | None,
    actor_username: str,
    actor_role: str,
    action: str,
    tenant_id: str | None = None,
    resource_type: str,
    resource_id: str | None = None,
    changed_fields: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    ip_address: str | None = None,
    request_id: str | None = None,
    success: bool = True,
    error_message: str | None = None,
) -> AdminAuditEvent:
    """Log an administrative action with automatic sanitization.
    
    This is the main entry point for creating audit log entries.
    All sensitive data is automatically sanitized before storage.
    
    Args:
        session: Database session
        actor_admin_id: ID of the admin performing the action
        actor_username: Username of the admin
        actor_role: Role of the admin (super_admin, auditor, operator)
        action: Action performed (e.g., 'tenant.deleted')
        tenant_id: Associated tenant ID if applicable
        resource_type: Type of resource affected
        resource_id: ID of the affected resource
        changed_fields: Fields that were changed (will be sanitized)
        metadata: Additional context (will be sanitized)
        ip_address: IP address of the request
        request_id: Unique request identifier
        success: Whether the operation succeeded
        error_message: Error message if failed
    
    Returns:
        The created audit event
    
    Example:
        >>> await log_event(
        ...     session=session,
        ...     actor_admin_id="admin-123",
        ...     actor_username="admin@example.com",
        ...     actor_role="super_admin",
        ...     action="tenant.deleted",
        ...     resource_type="tenant",
        ...     resource_id="tenant-456",
        ...     success=True,
        ... )
    """
    # Sanitize sensitive data
    sanitized_changed_fields = _sanitize_changed_fields(changed_fields)
    sanitized_metadata = _sanitize_metadata(metadata)
    
    try:
        event = await audit_repo.create_audit_event(
            session,
            actor_admin_id=actor_admin_id,
            actor_username=actor_username,
            actor_role=actor_role,
            action=action,
            tenant_id=tenant_id,
            resource_type=resource_type,
            resource_id=resource_id,
            changed_fields=sanitized_changed_fields,
            metadata=sanitized_metadata,
            ip_address=ip_address,
            request_id=request_id,
            success=success,
            error_message=error_message,
        )
        LOGGER.info(
            "Audit event created: action=%s, actor=%s, resource=%s/%s, success=%s",
            action,
            actor_username,
            resource_type,
            resource_id or "N/A",
            success,
        )
        return event
    except Exception:
        LOGGER.exception(
            "Failed to create audit event: action=%s, actor=%s",
            action,
            actor_username,
        )
        raise


async def list_events(
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
) -> tuple[list[AdminAuditEvent], int]:
    """List audit events with filtering and pagination.
    
    Args:
        session: Database session
        actor_admin_id: Filter by admin ID
        action: Filter by action type
        tenant_id: Filter by tenant
        resource_type: Filter by resource type
        start_date: Filter events after this date
        end_date: Filter events before this date
        skip: Number of records to skip
        limit: Maximum number of records to return
    
    Returns:
        Tuple of (events list, total count)
    """
    filters = {
        "actor_admin_id": actor_admin_id,
        "action": action,
        "tenant_id": tenant_id,
        "resource_type": resource_type,
        "start_date": start_date,
        "end_date": end_date,
    }
    
    events = await audit_repo.list_audit_events(
        session,
        **filters,
        skip=skip,
        limit=limit,
    )
    
    total = await audit_repo.count_audit_events(session, **filters)
    
    return events, total


async def get_event_by_id(
    session: AsyncSession,
    event_id: str,
) -> AdminAuditEvent | None:
    """Retrieve a single audit event by ID.
    
    Args:
        session: Database session
        event_id: The audit event ID
    
    Returns:
        The audit event if found, None otherwise
    """
    return await audit_repo.get_audit_event_by_id(session, event_id)
