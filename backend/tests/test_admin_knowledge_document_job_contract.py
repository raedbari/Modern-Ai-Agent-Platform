"""Contracts for administrative document job endpoints."""

from backend.app.api.dependencies import ROLE_PERMISSIONS
from backend.app.api.schemas.admin_knowledge import (
    DocumentJobAdminResponse,
)
from backend.app.main import create_app

UPLOAD_PATH = (
    "/api/admin/tenants/{tenant_id}/knowledge-bases/"
    "{knowledge_base_id}/documents"
)
REPLACE_PATH = (
    "/api/admin/tenants/{tenant_id}/knowledge-bases/"
    "{knowledge_base_id}/documents/{document_id}/replace"
)


def test_admin_document_job_paths_are_registered() -> None:
    paths = create_app().openapi()["paths"]
    for path in (UPLOAD_PATH, REPLACE_PATH):
        operation = paths[path]["post"]
        assert operation["responses"]["202"]
        security = operation.get("security", [])
        assert security
        assert all(
            "TenantApiKey" not in entry
            for entry in security
        )


def test_admin_document_jobs_require_write_permission() -> None:
    assert "knowledge:write" in ROLE_PERMISSIONS["super_admin"]
    assert "knowledge:write" in ROLE_PERMISSIONS["operator"]
    assert "knowledge:write" not in ROLE_PERMISSIONS["auditor"]


def test_document_job_response_allows_duplicate_without_job() -> None:
    response = DocumentJobAdminResponse(
        document_id="document-a",
        document_status="ready",
        duplicate=True,
        job=None,
    )
    assert response.duplicate is True
    assert response.job is None


def test_active_job_unique_index_is_in_model_metadata() -> None:
    from backend.app.db.models import IngestionJob

    indexes = {
        index.name: index
        for index in IngestionJob.__table__.indexes
    }
    assert "uq_ingestion_jobs_active_document" in indexes
    assert indexes["uq_ingestion_jobs_active_document"].unique is True
