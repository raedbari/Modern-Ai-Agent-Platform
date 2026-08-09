"""Tenant user lifecycle operations with session invalidation.

This module provides operations for tenant user lifecycle events that require
session invalidation, such as password changes, account deactivation, and 
membership status changes.

Requirements: 9.1-9.3, 10.1-10.3, 11.1-11.4, 12.1-12.3
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.config import Settings
from backend.app.db.models import Tenant, TenantMembership, User, UserRefreshSession
from backend.app.operations.tenant_session_ops import revoke_all_user_sessions


# ============================================================================
# Task 8.1: Password Change Session Invalidation
# ============================================================================

async def change_tenant_user_password(
    session: AsyncSession,
    *,
    user_id: str,
    current_password: str,
    new_password: str,
    settings: Settings,
) -> None:
    """Change tenant user password and revoke all sessions.
    
    Steps:
    1. Load User record
    2. Verify current password
    3. Validate new password strength
    4. Hash and store new password
    5. Revoke all active UserRefreshSessions
    
    After password change, all sessions are invalidated to prevent
    unauthorized access if the old password was compromised.
    
    Args:
        session: Database session
        user_id: User ID
        current_password: Current password for verification
        new_password: New password to set
        settings: Application settings
        
    Raises:
        ValueError: If user not found or current password incorrect
        
    Requirements: 9.1-9.3
    """
    # Load user
    user = await session.get(User, user_id)
    if user is None:
        raise ValueError("User not found")
    
    # Verify current password
    from backend.app.auth.password import verify_password
    if not verify_password(current_password, user.hashed_password):
        raise ValueError("Current password is incorrect")
    
    # Hash new password
    from backend.app.auth.password import hash_password
    user.hashed_password = hash_password(new_password, settings)
    
    # Revoke all sessions for this user
    await revoke_all_user_sessions(session, user_id)
    
    # Note: Caller must commit the session


# ============================================================================
# Task 8.2: User Deactivation Session Invalidation
# ============================================================================

async def deactivate_tenant_user(
    session: AsyncSession,
    *,
    user_id: str,
) -> None:
    """Deactivate tenant user and revoke all sessions.
    
    When a user account is deactivated (is_active=False), all their
    active sessions must be revoked immediately to prevent further access.
    
    Args:
        session: Database session
        user_id: User ID to deactivate
        
    Raises:
        ValueError: If user not found
        
    Requirements: 10.1-10.3
    """
    # Load user
    user = await session.get(User, user_id)
    if user is None:
        raise ValueError("User not found")
    
    # Set inactive
    user.is_active = False
    
    # Revoke all sessions
    await revoke_all_user_sessions(session, user_id)
    
    # Note: Caller must commit the session


# ============================================================================
# Task 8.3: Membership Status Change Session Invalidation
# ============================================================================

async def update_membership_status(
    session: AsyncSession,
    *,
    membership_id: str,
    new_status: str,
) -> None:
    """Update membership status and revoke sessions if suspended/revoked.
    
    When a membership status changes from 'active' to 'suspended' or 'revoked',
    all UserRefreshSessions for that user in that tenant must be revoked.
    
    Note: This revokes ALL user sessions (across all tenants), not just
    sessions for the specific tenant, to ensure complete security.
    
    Args:
        session: Database session
        membership_id: TenantMembership ID
        new_status: New status ('active', 'suspended', or 'revoked')
        
    Raises:
        ValueError: If membership not found or invalid status
        
    Requirements: 11.1-11.4
    """
    # Validate status
    if new_status not in ("active", "suspended", "revoked"):
        raise ValueError(f"Invalid membership status: {new_status}")
    
    # Load membership
    membership = await session.get(TenantMembership, membership_id)
    if membership is None:
        raise ValueError("Membership not found")
    
    old_status = membership.status
    
    # Update status
    membership.status = new_status
    
    # If changing from active to suspended/revoked, revoke sessions
    if old_status == "active" and new_status in ("suspended", "revoked"):
        await revoke_all_user_sessions(session, membership.user_id)
    
    # Note: Caller must commit the session


# ============================================================================
# Task 8.4: Tenant Deactivation Session Invalidation
# ============================================================================

async def deactivate_tenant(
    session: AsyncSession,
    *,
    tenant_id: str,
) -> None:
    """Deactivate tenant and revoke all member sessions.
    
    When a tenant is deactivated (is_active=False), all sessions for
    all members of that tenant must be revoked immediately.
    
    Steps:
    1. Load Tenant record
    2. Set is_active=False
    3. Query all TenantMemberships for this tenant
    4. For each membership, revoke all user sessions
    
    Args:
        session: Database session
        tenant_id: Tenant ID to deactivate
        
    Raises:
        ValueError: If tenant not found
        
    Requirements: 12.1-12.3
    """
    # Load tenant
    tenant = await session.get(Tenant, tenant_id)
    if tenant is None:
        raise ValueError("Tenant not found")
    
    # Set inactive
    tenant.is_active = False
    
    # Get all memberships for this tenant
    memberships = list(
        (
            await session.scalars(
                select(TenantMembership).where(
                    TenantMembership.tenant_id == tenant_id
                )
            )
        ).all()
    )
    
    # Revoke sessions for each member
    for membership in memberships:
        await revoke_all_user_sessions(session, membership.user_id)
    
    # Note: Caller must commit the session
