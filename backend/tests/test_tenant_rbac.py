"""Unit tests for tenant RBAC permission module.

Tests the role-based permission matrix and fail-closed security behavior.

Requirements: 5, 6
"""

import pytest

from backend.app.auth.tenant_rbac import (
    TenantPermission,
    get_role_permissions,
    RolePermissions,
)


class TestGetRolePermissions:
    """Test the get_role_permissions function."""
    
    def test_tenant_owner_has_all_permissions(self):
        """Tenant owner role should have all permissions."""
        perms = get_role_permissions("tenant_owner")
        
        assert perms.can_manage_agents is True
        assert perms.can_read_agents is True
        assert perms.can_manage_knowledge is True
        assert perms.can_read_knowledge is True
        assert perms.can_manage_conversations is True
        assert perms.can_read_conversations is True
        assert perms.can_manage_widget_settings is True
    
    def test_tenant_admin_has_all_permissions(self):
        """Tenant admin role should have all permissions."""
        perms = get_role_permissions("tenant_admin")
        
        assert perms.can_manage_agents is True
        assert perms.can_read_agents is True
        assert perms.can_manage_knowledge is True
        assert perms.can_read_knowledge is True
        assert perms.can_manage_conversations is True
        assert perms.can_read_conversations is True
        assert perms.can_manage_widget_settings is True
    
    def test_knowledge_editor_has_knowledge_and_read_conversation_permissions(self):
        """Knowledge editor should manage agents/KB, read conversations, no conversation management."""
        perms = get_role_permissions("knowledge_editor")
        
        assert perms.can_manage_agents is True
        assert perms.can_read_agents is True
        assert perms.can_manage_knowledge is True
        assert perms.can_read_knowledge is True
        assert perms.can_manage_conversations is False
        assert perms.can_read_conversations is True
        assert perms.can_manage_widget_settings is True
    
    def test_conversation_viewer_has_read_only_permissions(self):
        """Conversation viewer should have read-only access to agents and conversations."""
        perms = get_role_permissions("conversation_viewer")
        
        assert perms.can_manage_agents is False
        assert perms.can_read_agents is True
        assert perms.can_manage_knowledge is False
        assert perms.can_read_knowledge is False
        assert perms.can_manage_conversations is False
        assert perms.can_read_conversations is True
        assert perms.can_manage_widget_settings is False
    
    def test_billing_manager_has_no_permissions(self):
        """Billing manager role is reserved for future use and has no permissions in Phase 2."""
        perms = get_role_permissions("billing_manager")
        
        assert perms.can_manage_agents is False
        assert perms.can_read_agents is False
        assert perms.can_manage_knowledge is False
        assert perms.can_read_knowledge is False
        assert perms.can_manage_conversations is False
        assert perms.can_read_conversations is False
        assert perms.can_manage_widget_settings is False
    
    def test_unknown_role_has_no_permissions_fail_closed(self):
        """Unknown roles should have no permissions (fail closed security)."""
        perms = get_role_permissions("unknown_role")
        
        assert perms.can_manage_agents is False
        assert perms.can_read_agents is False
        assert perms.can_manage_knowledge is False
        assert perms.can_read_knowledge is False
        assert perms.can_manage_conversations is False
        assert perms.can_read_conversations is False
        assert perms.can_manage_widget_settings is False
    
    def test_empty_string_role_has_no_permissions(self):
        """Empty string role should have no permissions."""
        perms = get_role_permissions("")
        
        assert perms.can_manage_agents is False
        assert perms.can_read_agents is False
        assert perms.can_manage_knowledge is False
        assert perms.can_read_knowledge is False
        assert perms.can_manage_conversations is False
        assert perms.can_read_conversations is False
        assert perms.can_manage_widget_settings is False
    
    def test_typo_in_role_has_no_permissions(self):
        """Role names with typos should have no permissions (fail closed)."""
        perms = get_role_permissions("tenent_owner")  # Typo: tenent instead of tenant
        
        assert perms.can_manage_agents is False
        assert perms.can_read_agents is False
    
    def test_case_sensitive_role_names(self):
        """Role names are case-sensitive; wrong case should fail closed."""
        perms = get_role_permissions("TENANT_OWNER")  # Wrong case
        
        assert perms.can_manage_agents is False
        assert perms.can_read_agents is False


class TestTenantPermissionStaticMethods:
    """Test the TenantPermission static check class."""
    
    def test_can_manage_agents_tenant_owner(self):
        """Tenant owner can manage agents."""
        assert TenantPermission.can_manage_agents("tenant_owner") is True
    
    def test_can_manage_agents_tenant_admin(self):
        """Tenant admin can manage agents."""
        assert TenantPermission.can_manage_agents("tenant_admin") is True
    
    def test_can_manage_agents_knowledge_editor(self):
        """Knowledge editor can manage agents."""
        assert TenantPermission.can_manage_agents("knowledge_editor") is True
    
    def test_can_manage_agents_conversation_viewer(self):
        """Conversation viewer cannot manage agents."""
        assert TenantPermission.can_manage_agents("conversation_viewer") is False
    
    def test_can_manage_agents_billing_manager(self):
        """Billing manager cannot manage agents."""
        assert TenantPermission.can_manage_agents("billing_manager") is False
    
    def test_can_manage_agents_unknown_role(self):
        """Unknown role cannot manage agents."""
        assert TenantPermission.can_manage_agents("unknown") is False
    
    def test_can_read_agents_all_known_roles_except_billing(self):
        """All roles except billing_manager can read agents."""
        assert TenantPermission.can_read_agents("tenant_owner") is True
        assert TenantPermission.can_read_agents("tenant_admin") is True
        assert TenantPermission.can_read_agents("knowledge_editor") is True
        assert TenantPermission.can_read_agents("conversation_viewer") is True
        assert TenantPermission.can_read_agents("billing_manager") is False
    
    def test_can_manage_knowledge_restricted_roles(self):
        """Only owner, admin, and knowledge_editor can manage knowledge."""
        assert TenantPermission.can_manage_knowledge("tenant_owner") is True
        assert TenantPermission.can_manage_knowledge("tenant_admin") is True
        assert TenantPermission.can_manage_knowledge("knowledge_editor") is True
        assert TenantPermission.can_manage_knowledge("conversation_viewer") is False
        assert TenantPermission.can_manage_knowledge("billing_manager") is False
    
    def test_can_read_knowledge_restricted_roles(self):
        """Only owner, admin, and knowledge_editor can read knowledge."""
        assert TenantPermission.can_read_knowledge("tenant_owner") is True
        assert TenantPermission.can_read_knowledge("tenant_admin") is True
        assert TenantPermission.can_read_knowledge("knowledge_editor") is True
        assert TenantPermission.can_read_knowledge("conversation_viewer") is False
        assert TenantPermission.can_read_knowledge("billing_manager") is False
    
    def test_can_manage_conversations_admin_only(self):
        """Only owner and admin can manage (delete) conversations."""
        assert TenantPermission.can_manage_conversations("tenant_owner") is True
        assert TenantPermission.can_manage_conversations("tenant_admin") is True
        assert TenantPermission.can_manage_conversations("knowledge_editor") is False
        assert TenantPermission.can_manage_conversations("conversation_viewer") is False
        assert TenantPermission.can_manage_conversations("billing_manager") is False
    
    def test_can_read_conversations_all_except_billing(self):
        """All roles except billing_manager can read conversations."""
        assert TenantPermission.can_read_conversations("tenant_owner") is True
        assert TenantPermission.can_read_conversations("tenant_admin") is True
        assert TenantPermission.can_read_conversations("knowledge_editor") is True
        assert TenantPermission.can_read_conversations("conversation_viewer") is True
        assert TenantPermission.can_read_conversations("billing_manager") is False
    
    def test_can_manage_widget_settings_restricted_roles(self):
        """Only owner, admin, and knowledge_editor can manage widget settings."""
        assert TenantPermission.can_manage_widget_settings("tenant_owner") is True
        assert TenantPermission.can_manage_widget_settings("tenant_admin") is True
        assert TenantPermission.can_manage_widget_settings("knowledge_editor") is True
        assert TenantPermission.can_manage_widget_settings("conversation_viewer") is False
        assert TenantPermission.can_manage_widget_settings("billing_manager") is False


class TestRolePermissionsDataclass:
    """Test the RolePermissions dataclass."""
    
    def test_default_permissions_are_false(self):
        """RolePermissions with no arguments should have all permissions False."""
        perms = RolePermissions()
        
        assert perms.can_manage_agents is False
        assert perms.can_read_agents is False
        assert perms.can_manage_knowledge is False
        assert perms.can_read_knowledge is False
        assert perms.can_manage_conversations is False
        assert perms.can_read_conversations is False
        assert perms.can_manage_widget_settings is False
    
    def test_permissions_are_immutable(self):
        """RolePermissions should be frozen (immutable)."""
        perms = RolePermissions(can_manage_agents=True)
        
        with pytest.raises(AttributeError):
            perms.can_manage_agents = False  # type: ignore
    
    def test_custom_permissions(self):
        """RolePermissions should accept custom permission values."""
        perms = RolePermissions(
            can_read_agents=True,
            can_read_conversations=True
        )
        
        assert perms.can_read_agents is True
        assert perms.can_read_conversations is True
        assert perms.can_manage_agents is False


class TestPermissionMatrixCompleteness:
    """Test that the permission matrix matches the design specification."""
    
    def test_tenant_owner_permissions_match_spec(self):
        """Verify tenant_owner has all 7 permissions as per design doc."""
        perms = get_role_permissions("tenant_owner")
        permission_count = sum([
            perms.can_manage_agents,
            perms.can_read_agents,
            perms.can_manage_knowledge,
            perms.can_read_knowledge,
            perms.can_manage_conversations,
            perms.can_read_conversations,
            perms.can_manage_widget_settings,
        ])
        assert permission_count == 7
    
    def test_tenant_admin_permissions_match_spec(self):
        """Verify tenant_admin has all 7 permissions as per design doc."""
        perms = get_role_permissions("tenant_admin")
        permission_count = sum([
            perms.can_manage_agents,
            perms.can_read_agents,
            perms.can_manage_knowledge,
            perms.can_read_knowledge,
            perms.can_manage_conversations,
            perms.can_read_conversations,
            perms.can_manage_widget_settings,
        ])
        assert permission_count == 7
    
    def test_knowledge_editor_permissions_match_spec(self):
        """Verify knowledge_editor has 6 permissions (no manage_conversations)."""
        perms = get_role_permissions("knowledge_editor")
        permission_count = sum([
            perms.can_manage_agents,
            perms.can_read_agents,
            perms.can_manage_knowledge,
            perms.can_read_knowledge,
            perms.can_manage_conversations,
            perms.can_read_conversations,
            perms.can_manage_widget_settings,
        ])
        assert permission_count == 6
        assert perms.can_manage_conversations is False
    
    def test_conversation_viewer_permissions_match_spec(self):
        """Verify conversation_viewer has 2 permissions (read agents and conversations)."""
        perms = get_role_permissions("conversation_viewer")
        permission_count = sum([
            perms.can_manage_agents,
            perms.can_read_agents,
            perms.can_manage_knowledge,
            perms.can_read_knowledge,
            perms.can_manage_conversations,
            perms.can_read_conversations,
            perms.can_manage_widget_settings,
        ])
        assert permission_count == 2
        assert perms.can_read_agents is True
        assert perms.can_read_conversations is True
    
    def test_billing_manager_permissions_match_spec(self):
        """Verify billing_manager has 0 permissions (reserved for future)."""
        perms = get_role_permissions("billing_manager")
        permission_count = sum([
            perms.can_manage_agents,
            perms.can_read_agents,
            perms.can_manage_knowledge,
            perms.can_read_knowledge,
            perms.can_manage_conversations,
            perms.can_read_conversations,
            perms.can_manage_widget_settings,
        ])
        assert permission_count == 0


class TestSecurityInvariants:
    """Test security-critical invariants."""
    
    def test_fail_closed_for_malicious_role_names(self):
        """Malicious or crafted role names should have no permissions."""
        malicious_roles = [
            "tenant_owner; DROP TABLE users;",
            "<script>alert('xss')</script>",
            "../../etc/passwd",
            "null",
            "undefined",
            "admin",
            "superuser",
            "root",
        ]
        
        for role in malicious_roles:
            perms = get_role_permissions(role)
            assert perms.can_manage_agents is False
            assert perms.can_manage_knowledge is False
            assert perms.can_manage_conversations is False
    
    def test_no_implicit_permission_escalation(self):
        """Lower privilege roles should not have permissions of higher roles."""
        # conversation_viewer should not have manage permissions
        viewer_perms = get_role_permissions("conversation_viewer")
        assert viewer_perms.can_manage_agents is False
        assert viewer_perms.can_manage_knowledge is False
        
        # knowledge_editor should not have manage_conversations
        editor_perms = get_role_permissions("knowledge_editor")
        assert editor_perms.can_manage_conversations is False
    
    def test_all_roles_are_distinct(self):
        """Each role should have a unique permission set."""
        roles = [
            "tenant_owner",
            "tenant_admin",
            "knowledge_editor",
            "conversation_viewer",
            "billing_manager",
        ]
        
        permission_sets = []
        for role in roles:
            perms = get_role_permissions(role)
            perm_tuple = (
                perms.can_manage_agents,
                perms.can_read_agents,
                perms.can_manage_knowledge,
                perms.can_read_knowledge,
                perms.can_manage_conversations,
                perms.can_read_conversations,
                perms.can_manage_widget_settings,
            )
            permission_sets.append(perm_tuple)
        
        # tenant_owner and tenant_admin have same permissions (both admin roles)
        # So we expect 4 unique permission sets
        unique_sets = set(permission_sets)
        assert len(unique_sets) == 4
