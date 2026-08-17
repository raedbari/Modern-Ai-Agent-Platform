"""Controlled-pilot telemetry contracts and production chat integration."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from backend.app.telemetry import AITelemetryEvent, InMemoryTelemetrySink


def _event(**overrides) -> AITelemetryEvent:
    values = {
        "request_id": "request-a",
        "tenant_id": "tenant-a",
        "product_id": "athkachatbots",
        "agent_id": "agent-a",
        "conversation_id": "conversation-a",
        "provider": "provider-a",
        "model": "model-a",
        "prompt_version": None,
        "knowledge_version": None,
        "retrieval_count": 3,
        "rerank_count": None,
        "source_count": 2,
        "answer_status": "grounded",
        "input_tokens": 11,
        "output_tokens": 7,
        "latency_ms": 12.5,
        "error_type": None,
        "timestamp": datetime.now(timezone.utc),
    }
    values.update(overrides)
    return AITelemetryEvent(**values)


def test_in_memory_sink_is_replaceable_and_tenant_scoped() -> None:
    sink = InMemoryTelemetrySink()
    event = _event()

    sink.emit(event)

    assert sink.events == [event]
    assert sink.events[0].tenant_id == "tenant-a"
    assert sink.events[0].request_id == "request-a"


def test_event_contract_forbids_sensitive_raw_content() -> None:
    sensitive_fields = {
        "prompt": "raw customer prompt",
        "message": "raw customer message",
        "response": "raw model answer",
        "document": "raw customer document",
        "api_key": "secret-token",
    }

    for field, value in sensitive_fields.items():
        with pytest.raises(ValidationError):
            _event(**{field: value})

    serialized = _event().model_dump_json()
    assert "raw customer" not in serialized
    assert "secret-token" not in serialized
