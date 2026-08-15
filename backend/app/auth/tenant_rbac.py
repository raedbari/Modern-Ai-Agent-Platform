"""Customer tenant RBAC.

Database membership state remains authoritative.
JWT role claims are never trusted for authorization.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Callable

from fastapi import Depends, HTTPException, status

from backend.app.auth.tenant_context import TenantUserContext
from backend.app.api.dependencies import require_tenant_user_jwt


@dataclass(frozen=True, slots=True)
class RolePermissions:
    can_manage_agents: bool = False
    can_read_agents: bool = False
    can_manage_knowledge: bool = False
    can_read_knowledge: bool = False
    can_manage_conversations: bool = False
    can_read_conversations: bool = False
    can_manage_widget_settings: bool = False


ROLE_PERMISSIONS: dict[str, RolePermissions] = {
    "tenant_owner": RolePermissions(
        can_manage_agents=True,
        can_read_agents=True,
        can_manage_knowledge=True,
        can_read_knowledge=True,
        can_manage_conversations=True,
        can_read_conversations=True,
        can_manage_widget_settings=True,
    ),
    "tenant_admin": RolePermissions(
        can_manage_agents=True,
        can_read_agents=True,
        can_manage_knowledge=True,
        can_read_knowledge=True,
        can_manage_conversations=True,
        can_read_conversations=True,
        can_manage_widget_settings=True,
    ),
    "knowledge_editor": RolePermissions(
        can_manage_agents=True,
        can_read_agents=True,
        can_manage_knowledge=True,
        can_read_knowledge=True,
        can_manage_conversations=False,
        can_read_conversations=True,
        can_manage_widget_settings=True,
    ),
    "conversation_viewer": RolePermissions(
        can_manage_agents=False,
        can_read_agents=True,
        can_manage_knowledge=False,
        can_read_knowledge=False,
        can_manage_conversations=False,
        can_read_conversations=True,
        can_manage_widget_settings=False,
    ),
    "billing_manager": RolePermissions(),
}


def get_role_permissions(role: str) -> RolePermissions:
    return ROLE_PERMISSIONS.get(
        role,
        RolePermissions(),
    )


class TenantPermission:

    @staticmethod
    def can_manage_agents(role: str) -> bool:
        return get_role_permissions(role).can_manage_agents

    @staticmethod
    def can_read_agents(role: str) -> bool:
        return get_role_permissions(role).can_read_agents

    @staticmethod
    def can_manage_knowledge(role: str) -> bool:
        return get_role_permissions(role).can_manage_knowledge

    @staticmethod
    def can_read_knowledge(role: str) -> bool:
        return get_role_permissions(role).can_read_knowledge

    @staticmethod
    def can_manage_conversations(role: str) -> bool:
        return get_role_permissions(role).can_manage_conversations

    @staticmethod
    def can_read_conversations(role: str) -> bool:
        return get_role_permissions(role).can_read_conversations

    @staticmethod
    def can_manage_widget_settings(role: str) -> bool:
        return (
            get_role_permissions(role)
            .can_manage_widget_settings
        )


def require_tenant_permission(
    checker: Callable[[str], bool],
):
    async def dependency(
        context: Annotated[
            TenantUserContext,
            Depends(require_tenant_user_jwt),
        ],
    ) -> None:
        if not checker(context.role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied.",
            )

    return dependency
