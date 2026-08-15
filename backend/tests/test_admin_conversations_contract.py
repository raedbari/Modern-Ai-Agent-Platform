"""Contract checks for the administrative conversation read API."""

from backend.app.api.dependencies import (
    ROLE_PERMISSIONS,
)
from backend.app.main import create_app


COLLECTION_PATH = (
    "/api/admin/tenants/{tenant_id}/conversations"
)

DETAIL_PATH = (
    "/api/admin/tenants/{tenant_id}/conversations/"
    "{conversation_id}"
)

MESSAGES_PATH = (
    "/api/admin/tenants/{tenant_id}/conversations/"
    "{conversation_id}/messages"
)


def test_admin_conversation_permissions_follow_role_boundaries() -> None:
    assert {
        "conversations:read",
        "conversations:delete",
    }.issubset(
        ROLE_PERMISSIONS["super_admin"]
    )

    assert {
        "conversations:read",
        "conversations:delete",
    }.issubset(
        ROLE_PERMISSIONS["operator"]
    )

    assert (
        "conversations:read"
        in ROLE_PERMISSIONS["auditor"]
    )

    assert (
        "conversations:delete"
        not in ROLE_PERMISSIONS["auditor"]
    )


def test_admin_conversation_read_paths_are_registered() -> None:
    document = create_app().openapi()
    paths = document["paths"]

    for path in (
        COLLECTION_PATH,
        DETAIL_PATH,
        MESSAGES_PATH,
    ):
        assert path in paths
        assert "get" in paths[path]

        security = paths[path]["get"].get(
            "security",
            [],
        )

        assert security
        assert all(
            "TenantApiKey" not in entry
            for entry in security
        )


def test_existing_conversation_delete_contract_is_preserved() -> None:
    document = create_app().openapi()
    detail = document["paths"][
        DETAIL_PATH
    ]

    assert "get" in detail
    assert "delete" in detail
    assert "patch" not in detail


def test_conversation_collection_is_read_only() -> None:
    document = create_app().openapi()
    collection = document["paths"][
        COLLECTION_PATH
    ]

    assert "get" in collection
    assert "post" not in collection
    assert "patch" not in collection
    assert "delete" not in collection


def test_conversation_messages_are_read_only() -> None:
    document = create_app().openapi()
    messages = document["paths"][
        MESSAGES_PATH
    ]

    assert "get" in messages
    assert "post" not in messages
    assert "patch" not in messages
    assert "delete" not in messages
