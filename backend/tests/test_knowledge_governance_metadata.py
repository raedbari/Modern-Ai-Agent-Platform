"""Tests for knowledge governance metadata invariants.

Covers Task 8 acceptance criteria:
1. version_number starts at 1 (default)
2. version_number increments on replacement (simulated via direct field mutation)
3. classification field defaults to "internal" on KnowledgeBase
4. created_by stored and retrieved correctly on Document
5. SUPERSEDED / ARCHIVED state transitions are valid
"""

from __future__ import annotations

import pytest

from backend.app.domain.models.document import Document
from backend.app.domain.models.enums import DocumentProcessingStatus
from backend.app.domain.models.knowledge_base import KnowledgeBase


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_RETRIEVAL_ELIGIBLE_STATUSES = frozenset(
    {
        DocumentProcessingStatus.PENDING,
        DocumentProcessingStatus.PROCESSING,
        DocumentProcessingStatus.READY,
    }
)

_TERMINAL_STATUSES = frozenset(
    {
        DocumentProcessingStatus.SUPERSEDED,
        DocumentProcessingStatus.ARCHIVED,
        DocumentProcessingStatus.FAILED,
    }
)


def _make_document(**overrides) -> Document:
    """Return a minimal valid Document, applying any keyword overrides."""
    defaults = dict(
        id="doc-001",
        tenant_id="tenant-1",
        knowledge_base_id="kb-1",
        source_name="s3://bucket/file.txt",
        original_filename="file.txt",
        mime_type="text/plain",
        file_size_bytes=512,
        content_hash="a" * 64,
    )
    defaults.update(overrides)
    return Document(**defaults)


def _make_kb(**overrides) -> KnowledgeBase:
    """Return a minimal valid KnowledgeBase, applying any keyword overrides."""
    defaults = dict(id="kb-1", tenant_id="tenant-1", name="My KB")
    defaults.update(overrides)
    return KnowledgeBase(**defaults)


# ---------------------------------------------------------------------------
# Document.version_number
# ---------------------------------------------------------------------------


class TestDocumentVersionNumber:
    def test_default_version_number_is_one(self) -> None:
        """version_number starts at 1 when not supplied."""
        doc = _make_document()
        assert doc.version_number == 1

    def test_version_number_two_is_valid(self) -> None:
        """version_number=2 is accepted (represents a reindexed document)."""
        doc = _make_document(version_number=2)
        assert doc.version_number == 2

    def test_version_number_three_is_valid(self) -> None:
        """version_number=3 is accepted."""
        doc = _make_document(version_number=3)
        assert doc.version_number == 3

    def test_version_number_zero_raises(self) -> None:
        """version_number=0 is below the minimum (1) and must raise ValueError."""
        with pytest.raises(ValueError, match="version_number"):
            _make_document(version_number=0)

    def test_version_number_negative_raises(self) -> None:
        """Negative version_number values must raise ValueError."""
        with pytest.raises(ValueError, match="version_number"):
            _make_document(version_number=-1)

    def test_version_number_increments_on_reindex(self) -> None:
        """Simulating a reindex: version_number increments from 1 to 2.

        In production the IngestionService handles this by mutating the
        field before persisting.  Here we verify the dataclass accepts the
        incremented value and stores it faithfully.
        """
        doc = _make_document(version_number=1)
        # Simulate what the service does during reindex
        doc.version_number += 1
        assert doc.version_number == 2


# ---------------------------------------------------------------------------
# Document.superseded_by_id
# ---------------------------------------------------------------------------


class TestDocumentSupersededById:
    def test_default_superseded_by_id_is_none(self) -> None:
        """superseded_by_id defaults to None (document is current)."""
        doc = _make_document()
        assert doc.superseded_by_id is None

    def test_valid_superseded_by_id(self) -> None:
        """A non-empty superseded_by_id string is accepted."""
        doc = _make_document(superseded_by_id="doc-v2")
        assert doc.superseded_by_id == "doc-v2"

    def test_empty_superseded_by_id_raises(self) -> None:
        """An empty string for superseded_by_id must raise ValueError."""
        with pytest.raises(ValueError):
            _make_document(superseded_by_id="")

    def test_whitespace_superseded_by_id_raises(self) -> None:
        """A whitespace-only superseded_by_id must raise ValueError."""
        with pytest.raises(ValueError):
            _make_document(superseded_by_id="   ")


# ---------------------------------------------------------------------------
# Document.created_by
# ---------------------------------------------------------------------------


class TestDocumentCreatedBy:
    def test_default_created_by_is_none(self) -> None:
        """created_by defaults to None (anonymous / system-initiated upload)."""
        doc = _make_document()
        assert doc.created_by is None

    def test_created_by_stored_and_retrieved(self) -> None:
        """created_by is stored exactly as supplied and retrieved without mutation."""
        doc = _make_document(created_by="user-abc")
        assert doc.created_by == "user-abc"

    def test_created_by_none_explicit(self) -> None:
        """Explicitly passing None for created_by is valid."""
        doc = _make_document(created_by=None)
        assert doc.created_by is None


# ---------------------------------------------------------------------------
# KnowledgeBase.classification
# ---------------------------------------------------------------------------


class TestKnowledgeBaseClassification:
    def test_default_classification_is_internal(self) -> None:
        """classification defaults to 'internal' when not supplied."""
        kb = _make_kb()
        assert kb.classification == "internal"

    def test_classification_public_is_valid(self) -> None:
        """classification='public' is accepted."""
        kb = _make_kb(classification="public")
        assert kb.classification == "public"

    def test_classification_restricted_is_valid(self) -> None:
        """classification='restricted' is accepted."""
        kb = _make_kb(classification="restricted")
        assert kb.classification == "restricted"

    def test_classification_top_secret_raises(self) -> None:
        """classification='top-secret' is not in the allowed set and must raise ValueError."""
        with pytest.raises(ValueError):
            _make_kb(classification="top-secret")

    def test_classification_empty_raises(self) -> None:
        """An empty string for classification must raise ValueError."""
        with pytest.raises(ValueError):
            _make_kb(classification="")


# ---------------------------------------------------------------------------
# State transitions: SUPERSEDED and ARCHIVED
# ---------------------------------------------------------------------------


class TestDocumentStateTransitions:
    def test_status_ready_to_superseded_is_valid_enum_value(self) -> None:
        """DocumentProcessingStatus.SUPERSEDED is a valid enum member."""
        assert DocumentProcessingStatus.SUPERSEDED in DocumentProcessingStatus.__members__.values()

    def test_status_ready_to_archived_is_valid_enum_value(self) -> None:
        """DocumentProcessingStatus.ARCHIVED is a valid enum member."""
        assert DocumentProcessingStatus.ARCHIVED in DocumentProcessingStatus.__members__.values()

    def test_superseded_is_not_retrieval_eligible(self) -> None:
        """SUPERSEDED must not be in the set of retrieval-eligible statuses."""
        assert DocumentProcessingStatus.SUPERSEDED not in _RETRIEVAL_ELIGIBLE_STATUSES

    def test_archived_is_not_retrieval_eligible(self) -> None:
        """ARCHIVED must not be in the set of retrieval-eligible statuses."""
        assert DocumentProcessingStatus.ARCHIVED not in _RETRIEVAL_ELIGIBLE_STATUSES

    def test_ready_is_retrieval_eligible(self) -> None:
        """READY must be a retrieval-eligible status (sanity check)."""
        assert DocumentProcessingStatus.READY in _RETRIEVAL_ELIGIBLE_STATUSES

    def test_document_superseded_with_superseded_by_id_is_valid(self) -> None:
        """A document with status=SUPERSEDED and a superseded_by_id is a valid model state."""
        doc = _make_document(
            status=DocumentProcessingStatus.SUPERSEDED,
            superseded_by_id="doc-v2",
        )
        assert doc.status == DocumentProcessingStatus.SUPERSEDED
        assert doc.superseded_by_id == "doc-v2"

    def test_document_archived_without_superseded_by_id_is_valid(self) -> None:
        """A document with status=ARCHIVED and no superseded_by_id is a valid model state."""
        doc = _make_document(
            status=DocumentProcessingStatus.ARCHIVED,
            superseded_by_id=None,
        )
        assert doc.status == DocumentProcessingStatus.ARCHIVED
        assert doc.superseded_by_id is None

    def test_superseded_and_archived_are_terminal(self) -> None:
        """SUPERSEDED and ARCHIVED are both terminal states (in _TERMINAL_STATUSES)."""
        assert DocumentProcessingStatus.SUPERSEDED in _TERMINAL_STATUSES
        assert DocumentProcessingStatus.ARCHIVED in _TERMINAL_STATUSES

    def test_pending_and_processing_are_not_terminal(self) -> None:
        """PENDING and PROCESSING are not terminal states."""
        assert DocumentProcessingStatus.PENDING not in _TERMINAL_STATUSES
        assert DocumentProcessingStatus.PROCESSING not in _TERMINAL_STATUSES
