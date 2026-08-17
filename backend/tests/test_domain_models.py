"""Tests for domain model entities and enumerations.

Covers:
- Successful construction with valid data.
- Validation errors for every invariant on every model.
- Enum values and membership.
"""

import pytest
from datetime import datetime, timezone

from backend.app.domain.models.enums import DocumentProcessingStatus, KnowledgeBaseStatus
from backend.app.domain.models.tenant import Tenant
from backend.app.domain.models.agent import Agent
from backend.app.domain.models.knowledge_base import KnowledgeBase
from backend.app.domain.models.document import Document
from backend.app.domain.models.chunk import Chunk


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _document(**overrides) -> Document:
    """Return a valid Document, applying any field overrides."""
    defaults = dict(
        id="doc-1",
        tenant_id="tenant-1",
        knowledge_base_id="kb-1",
        source_name="upload",
        original_filename="report.pdf",
        mime_type="application/pdf",
        file_size_bytes=1024,
        content_hash="abc123",
    )
    defaults.update(overrides)
    return Document(**defaults)


def _chunk(**overrides) -> Chunk:
    """Return a valid Chunk, applying any field overrides."""
    defaults = dict(
        id="chunk-1",
        tenant_id="tenant-1",
        agent_id="agent-1",
        knowledge_base_id="kb-1",
        document_id="doc-1",
        source_name="upload",
        page_number=0,
        chunk_index=0,
        content="Some text content.",
        content_hash="abc123",
    )
    defaults.update(overrides)
    return Chunk(**defaults)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TestDocumentProcessingStatus:
    def test_all_statuses_present(self) -> None:
        statuses = {s.value for s in DocumentProcessingStatus}
        assert statuses == {"pending", "processing", "ready", "failed", "superseded", "archived"}

    def test_values_are_lowercase_strings(self) -> None:
        for status in DocumentProcessingStatus:
            assert status.value == status.value.lower()

    def test_is_string_subclass(self) -> None:
        assert isinstance(DocumentProcessingStatus.PENDING, str)


class TestKnowledgeBaseStatus:
    def test_all_statuses_present(self) -> None:
        statuses = {s.value for s in KnowledgeBaseStatus}
        assert statuses == {"active", "inactive"}

    def test_is_string_subclass(self) -> None:
        assert isinstance(KnowledgeBaseStatus.ACTIVE, str)


# ---------------------------------------------------------------------------
# Tenant
# ---------------------------------------------------------------------------

class TestTenant:
    def test_valid_construction(self) -> None:
        t = Tenant(id="t-1", display_name="Acme Corp")
        assert t.id == "t-1"
        assert t.display_name == "Acme Corp"

    def test_empty_id_raises(self) -> None:
        with pytest.raises(ValueError, match="Tenant.id"):
            Tenant(id="", display_name="Acme")

    def test_whitespace_id_raises(self) -> None:
        with pytest.raises(ValueError, match="Tenant.id"):
            Tenant(id="   ", display_name="Acme")

    def test_empty_display_name_raises(self) -> None:
        with pytest.raises(ValueError, match="Tenant.display_name"):
            Tenant(id="t-1", display_name="")

    def test_whitespace_display_name_raises(self) -> None:
        with pytest.raises(ValueError, match="Tenant.display_name"):
            Tenant(id="t-1", display_name="   ")


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class TestAgent:
    def test_valid_construction_no_kb(self) -> None:
        a = Agent(id="a-1", tenant_id="t-1")
        assert a.id == "a-1"
        assert a.tenant_id == "t-1"
        assert a.knowledge_base_ids == []

    def test_valid_construction_with_kbs(self) -> None:
        a = Agent(id="a-1", tenant_id="t-1", knowledge_base_ids=["kb-1", "kb-2"])
        assert len(a.knowledge_base_ids) == 2

    def test_empty_id_raises(self) -> None:
        with pytest.raises(ValueError, match="Agent.id"):
            Agent(id="", tenant_id="t-1")

    def test_empty_tenant_id_raises(self) -> None:
        with pytest.raises(ValueError, match="Agent.tenant_id"):
            Agent(id="a-1", tenant_id="")

    def test_empty_kb_id_in_list_raises(self) -> None:
        with pytest.raises(ValueError, match="knowledge_base_ids"):
            Agent(id="a-1", tenant_id="t-1", knowledge_base_ids=["kb-1", ""])

    def test_whitespace_kb_id_in_list_raises(self) -> None:
        with pytest.raises(ValueError, match="knowledge_base_ids"):
            Agent(id="a-1", tenant_id="t-1", knowledge_base_ids=["  "])

    def test_default_kb_list_is_independent_per_instance(self) -> None:
        """Mutable default must not be shared across instances."""
        a1 = Agent(id="a-1", tenant_id="t-1")
        a2 = Agent(id="a-2", tenant_id="t-1")
        a1.knowledge_base_ids.append("kb-x")
        assert a2.knowledge_base_ids == []


# ---------------------------------------------------------------------------
# KnowledgeBase
# ---------------------------------------------------------------------------

class TestKnowledgeBase:
    def test_valid_construction_defaults(self) -> None:
        kb = KnowledgeBase(id="kb-1", tenant_id="t-1", name="Support Docs")
        assert kb.description == ""
        assert kb.status == KnowledgeBaseStatus.ACTIVE

    def test_valid_construction_full(self) -> None:
        kb = KnowledgeBase(
            id="kb-1",
            tenant_id="t-1",
            name="Support Docs",
            description="Customer support knowledge base",
            status=KnowledgeBaseStatus.INACTIVE,
        )
        assert kb.status == KnowledgeBaseStatus.INACTIVE

    def test_empty_id_raises(self) -> None:
        with pytest.raises(ValueError, match="KnowledgeBase.id"):
            KnowledgeBase(id="", tenant_id="t-1", name="Docs")

    def test_empty_tenant_id_raises(self) -> None:
        with pytest.raises(ValueError, match="KnowledgeBase.tenant_id"):
            KnowledgeBase(id="kb-1", tenant_id="", name="Docs")

    def test_empty_name_raises(self) -> None:
        with pytest.raises(ValueError, match="KnowledgeBase.name"):
            KnowledgeBase(id="kb-1", tenant_id="t-1", name="")

    def test_whitespace_name_raises(self) -> None:
        with pytest.raises(ValueError, match="KnowledgeBase.name"):
            KnowledgeBase(id="kb-1", tenant_id="t-1", name="   ")

    # --- governance: classification ---

    def test_default_classification_is_internal(self) -> None:
        kb = KnowledgeBase(id="kb-1", tenant_id="t-1", name="Docs")
        assert kb.classification == "internal"

    def test_classification_public_is_valid(self) -> None:
        kb = KnowledgeBase(id="kb-1", tenant_id="t-1", name="Docs", classification="public")
        assert kb.classification == "public"

    def test_classification_restricted_is_valid(self) -> None:
        kb = KnowledgeBase(id="kb-1", tenant_id="t-1", name="Docs", classification="restricted")
        assert kb.classification == "restricted"

    def test_invalid_classification_raises(self) -> None:
        with pytest.raises(ValueError, match="KnowledgeBase.classification"):
            KnowledgeBase(id="kb-1", tenant_id="t-1", name="Docs", classification="top-secret")

    def test_empty_classification_raises(self) -> None:
        with pytest.raises(ValueError, match="KnowledgeBase.classification"):
            KnowledgeBase(id="kb-1", tenant_id="t-1", name="Docs", classification="")


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------

class TestDocument:
    def test_valid_construction_defaults(self) -> None:
        doc = _document()
        assert doc.status == DocumentProcessingStatus.PENDING
        assert doc.agent_id is None
        assert doc.failure_reason is None
        assert isinstance(doc.created_at, datetime)
        assert isinstance(doc.updated_at, datetime)

    def test_valid_construction_with_agent(self) -> None:
        doc = _document(agent_id="agent-1")
        assert doc.agent_id == "agent-1"

    def test_timestamps_are_utc(self) -> None:
        doc = _document()
        assert doc.created_at.tzinfo == timezone.utc
        assert doc.updated_at.tzinfo == timezone.utc

    def test_empty_id_raises(self) -> None:
        with pytest.raises(ValueError, match="Document.id"):
            _document(id="")

    def test_empty_tenant_id_raises(self) -> None:
        with pytest.raises(ValueError, match="Document.tenant_id"):
            _document(tenant_id="")

    def test_empty_knowledge_base_id_raises(self) -> None:
        with pytest.raises(ValueError, match="Document.knowledge_base_id"):
            _document(knowledge_base_id="")

    def test_empty_source_name_raises(self) -> None:
        with pytest.raises(ValueError, match="Document.source_name"):
            _document(source_name="")

    def test_empty_original_filename_raises(self) -> None:
        with pytest.raises(ValueError, match="Document.original_filename"):
            _document(original_filename="")

    def test_empty_mime_type_raises(self) -> None:
        with pytest.raises(ValueError, match="Document.mime_type"):
            _document(mime_type="")

    def test_negative_file_size_raises(self) -> None:
        with pytest.raises(ValueError, match="file_size_bytes"):
            _document(file_size_bytes=-1)

    def test_zero_file_size_is_valid(self) -> None:
        doc = _document(file_size_bytes=0)
        assert doc.file_size_bytes == 0

    def test_empty_content_hash_raises(self) -> None:
        with pytest.raises(ValueError, match="Document.content_hash"):
            _document(content_hash="")

    def test_whitespace_agent_id_raises(self) -> None:
        with pytest.raises(ValueError, match="Document.agent_id"):
            _document(agent_id="   ")

    def test_none_agent_id_is_valid(self) -> None:
        doc = _document(agent_id=None)
        assert doc.agent_id is None

    def test_failure_status_with_reason(self) -> None:
        doc = _document(
            status=DocumentProcessingStatus.FAILED,
            failure_reason="Unsupported file format.",
        )
        assert doc.status == DocumentProcessingStatus.FAILED
        assert doc.failure_reason == "Unsupported file format."

    # --- governance: version_number ---

    def test_default_version_number_is_one(self) -> None:
        doc = _document()
        assert doc.version_number == 1

    def test_version_number_above_one_is_valid(self) -> None:
        doc = _document(version_number=5)
        assert doc.version_number == 5

    def test_version_number_zero_raises(self) -> None:
        with pytest.raises(ValueError, match="version_number"):
            _document(version_number=0)

    def test_version_number_negative_raises(self) -> None:
        with pytest.raises(ValueError, match="version_number"):
            _document(version_number=-3)

    # --- governance: superseded_by_id ---

    def test_default_superseded_by_id_is_none(self) -> None:
        doc = _document()
        assert doc.superseded_by_id is None

    def test_superseded_by_id_non_empty_string_is_valid(self) -> None:
        doc = _document(superseded_by_id="doc-2")
        assert doc.superseded_by_id == "doc-2"

    def test_superseded_by_id_whitespace_raises(self) -> None:
        with pytest.raises(ValueError, match="superseded_by_id"):
            _document(superseded_by_id="   ")

    def test_superseded_by_id_empty_string_raises(self) -> None:
        with pytest.raises(ValueError, match="superseded_by_id"):
            _document(superseded_by_id="")

    # --- governance: created_by ---

    def test_default_created_by_is_none(self) -> None:
        doc = _document()
        assert doc.created_by is None

    def test_created_by_string_is_valid(self) -> None:
        doc = _document(created_by="user-abc")
        assert doc.created_by == "user-abc"


# ---------------------------------------------------------------------------
# Chunk
# ---------------------------------------------------------------------------

class TestChunk:
    def test_valid_construction(self) -> None:
        c = _chunk()
        assert c.page_number == 0
        assert c.chunk_index == 0

    def test_empty_id_raises(self) -> None:
        with pytest.raises(ValueError, match="Chunk.id"):
            _chunk(id="")

    def test_empty_tenant_id_raises(self) -> None:
        with pytest.raises(ValueError, match="Chunk.tenant_id"):
            _chunk(tenant_id="")

    def test_empty_agent_id_raises(self) -> None:
        with pytest.raises(ValueError, match="Chunk.agent_id"):
            _chunk(agent_id="")

    def test_empty_knowledge_base_id_raises(self) -> None:
        with pytest.raises(ValueError, match="Chunk.knowledge_base_id"):
            _chunk(knowledge_base_id="")

    def test_empty_document_id_raises(self) -> None:
        with pytest.raises(ValueError, match="Chunk.document_id"):
            _chunk(document_id="")

    def test_empty_source_name_raises(self) -> None:
        with pytest.raises(ValueError, match="Chunk.source_name"):
            _chunk(source_name="")

    def test_negative_page_number_raises(self) -> None:
        with pytest.raises(ValueError, match="page_number"):
            _chunk(page_number=-1)

    def test_zero_page_number_is_valid(self) -> None:
        c = _chunk(page_number=0)
        assert c.page_number == 0

    def test_negative_chunk_index_raises(self) -> None:
        with pytest.raises(ValueError, match="chunk_index"):
            _chunk(chunk_index=-1)

    def test_zero_chunk_index_is_valid(self) -> None:
        c = _chunk(chunk_index=0)
        assert c.chunk_index == 0

    def test_empty_content_raises(self) -> None:
        with pytest.raises(ValueError, match="Chunk.content"):
            _chunk(content="")

    def test_whitespace_content_raises(self) -> None:
        with pytest.raises(ValueError, match="Chunk.content"):
            _chunk(content="   ")

    def test_empty_content_hash_raises(self) -> None:
        with pytest.raises(ValueError, match="Chunk.content_hash"):
            _chunk(content_hash="")
