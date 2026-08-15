"""Contracts for immutable ingestion-job source metadata."""

from inspect import signature

from backend.app.db.models import IngestionJob
from backend.app.services.knowledge.job_service import IngestionJobService


def test_ingestion_job_model_exposes_source_metadata() -> None:
    columns = IngestionJob.__table__.columns

    assert "source_filename" in columns
    assert "source_mime_type" in columns
    assert "source_name" in columns
    assert columns["source_filename"].nullable is True
    assert columns["source_mime_type"].nullable is True
    assert columns["source_name"].nullable is True


def test_enqueue_accepts_source_metadata_and_external_job_id() -> None:
    parameters = signature(IngestionJobService.enqueue).parameters

    assert "source_filename" in parameters
    assert "source_mime_type" in parameters
    assert "source_name" in parameters
    assert "job_id" in parameters
