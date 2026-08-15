"""Contract checks for administrative knowledge mutations."""

import pytest
from pydantic import ValidationError

from backend.app.api.dependencies import ROLE_PERMISSIONS
from backend.app.api.schemas.admin_knowledge import (
    KnowledgeBaseAdminCreate,
    KnowledgeBaseAdminUpdate,
    KnowledgeBaseAgentAssignmentsUpdate,
)
from backend.app.main import create_app

COLLECTION_PATH = "/api/admin/tenants/{tenant_id}/knowledge-bases"
DETAIL_PATH = (
    "/api/admin/tenants/{tenant_id}/knowledge-bases/{knowledge_base_id}"
)
ASSIGNMENTS_PATH = (
    "/api/admin/tenants/{tenant_id}/knowledge-bases/"
    "{knowledge_base_id}/agents"
)


def test_knowledge_mutation_permissions_follow_role_boundaries() -> None:
    assert "knowledge:write" in ROLE_PERMISSIONS["super_admin"]
    assert "knowledge:write" in ROLE_PERMISSIONS["operator"]
    assert "knowledge:write" not in ROLE_PERMISSIONS["auditor"]


def test_knowledge_mutation_paths_are_registered() -> None:
    paths = create_app().openapi()["paths"]
    assert "post" in paths[COLLECTION_PATH]
    assert "patch" in paths[DETAIL_PATH]
    assert "put" in paths[ASSIGNMENTS_PATH]

    for path, method in (
        (COLLECTION_PATH, "post"),
        (DETAIL_PATH, "patch"),
        (ASSIGNMENTS_PATH, "put"),
    ):
        security = paths[path][method].get("security", [])
        assert security
        assert all("TenantApiKey" not in entry for entry in security)


def test_knowledge_create_schema_is_strict() -> None:
    payload = KnowledgeBaseAdminCreate(
        name="Support",
        description="Verified support data.",
        assigned_agent_ids=["agent-a", "agent-b"],
    )
    assert payload.status == "active"

    with pytest.raises(ValidationError):
        KnowledgeBaseAdminCreate(
            name="Support",
            assigned_agent_ids=["agent-a", "agent-a"],
        )

    with pytest.raises(ValidationError):
        KnowledgeBaseAdminCreate(name="Support", unexpected=True)


def test_knowledge_update_detects_empty_payload() -> None:
    assert KnowledgeBaseAdminUpdate().has_changes() is False
    assert KnowledgeBaseAdminUpdate(status="inactive").has_changes() is True


def test_assignment_schema_allows_detach_all_but_rejects_duplicates() -> None:
    detached = KnowledgeBaseAgentAssignmentsUpdate(agent_ids=[])
    assert detached.agent_ids == []

    with pytest.raises(ValidationError):
        KnowledgeBaseAgentAssignmentsUpdate(
            agent_ids=["agent-a", "agent-a"],
        )
