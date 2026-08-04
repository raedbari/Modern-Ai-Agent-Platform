"""Contract checks for the administrative knowledge read API."""

from backend.app.api.dependencies import (
    ROLE_PERMISSIONS,
)
from backend.app.main import create_app


EXPECTED_READ_PATHS = {
    "/api/admin/tenants/{tenant_id}/knowledge-bases",
    (
        "/api/admin/tenants/{tenant_id}/knowledge-bases/"
        "{knowledge_base_id}"
    ),
    (
        "/api/admin/tenants/{tenant_id}/knowledge-bases/"
        "{knowledge_base_id}/documents"
    ),
    (
        "/api/admin/tenants/{tenant_id}/knowledge-bases/"
        "{knowledge_base_id}/ingestion-jobs"
    ),
}


def test_admin_knowledge_permissions_follow_role_boundaries() -> None:
    assert {
        "knowledge:read",
        "knowledge:write",
        "knowledge:delete",
    }.issubset(
        ROLE_PERMISSIONS["super_admin"]
    )

    assert {
        "knowledge:read",
        "knowledge:write",
    }.issubset(
        ROLE_PERMISSIONS["operator"]
    )

    assert (
        "knowledge:delete"
        not in ROLE_PERMISSIONS["operator"]
    )

    assert (
        "knowledge:read"
        in ROLE_PERMISSIONS["auditor"]
    )

    assert (
        "knowledge:write"
        not in ROLE_PERMISSIONS["auditor"]
    )

    assert (
        "knowledge:delete"
        not in ROLE_PERMISSIONS["auditor"]
    )


def test_admin_knowledge_read_paths_are_registered() -> None:
    document = create_app().openapi()
    paths = document["paths"]

    assert EXPECTED_READ_PATHS.issubset(
        paths
    )

    for path in EXPECTED_READ_PATHS:
        operation = paths[path]["get"]

        security = operation.get(
            "security",
            [],
        )

        assert security
        assert all(
            "TenantApiKey" not in entry
            for entry in security
        )


def test_admin_knowledge_phase2a_routes_are_registered() -> None:
    document = create_app().openapi()
    paths = document["paths"]

    collection = paths[
        "/api/admin/tenants/{tenant_id}/knowledge-bases"
    ]

    assert "get" in collection
    assert "post" in collection

    detail = paths[
        (
            "/api/admin/tenants/{tenant_id}/knowledge-bases/"
            "{knowledge_base_id}"
        )
    ]

    assert "get" in detail
    assert "patch" in detail
    assert "delete" not in detail
