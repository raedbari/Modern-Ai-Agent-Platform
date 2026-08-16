"""Provider-independent, privacy-safe telemetry for the controlled pilot."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field


LOGGER = logging.getLogger("maap.pilot_telemetry")

AnswerStatus = Literal[
    "grounded",
    "generated",
    "insufficient_knowledge",
    "temporarily_unavailable",
    "failed",
]


class AITelemetryEvent(BaseModel):
    """Bounded metadata for one important AI request.

    The contract deliberately has no prompt, message, response, document,
    credential, or arbitrary metadata fields.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    request_id: str = Field(min_length=1, max_length=128)
    tenant_id: str = Field(min_length=1, max_length=128)
    product_id: str = Field(min_length=1, max_length=128)
    agent_id: str = Field(min_length=1, max_length=128)
    conversation_id: str | None = Field(default=None, max_length=128)
    provider: str | None = Field(default=None, max_length=128)
    model: str | None = Field(default=None, max_length=256)
    prompt_version: str | None = Field(default=None, max_length=128)
    knowledge_version: str | None = Field(default=None, max_length=128)
    retrieval_count: int | None = Field(default=None, ge=0)
    rerank_count: int | None = Field(default=None, ge=0)
    source_count: int | None = Field(default=None, ge=0)
    answer_status: AnswerStatus
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    latency_ms: float = Field(ge=0)
    error_type: str | None = Field(default=None, max_length=128)
    timestamp: datetime


class TelemetrySink(Protocol):
    """Replaceable output port for provider-independent AI telemetry."""

    def emit(self, event: AITelemetryEvent) -> None:
        """Accept one validated telemetry event."""
        ...


class StructuredLoggingTelemetrySink:
    """Pilot sink that writes one JSON object through application logging."""

    def emit(self, event: AITelemetryEvent) -> None:
        LOGGER.info(
            "ai_telemetry %s",
            json.dumps(
                event.model_dump(mode="json"),
                separators=(",", ":"),
                sort_keys=True,
            ),
        )


class InMemoryTelemetrySink:
    """Small replaceable sink for tests and local composition."""

    def __init__(self) -> None:
        self.events: list[AITelemetryEvent] = []

    def emit(self, event: AITelemetryEvent) -> None:
        self.events.append(event)


def emit_safely(sink: TelemetrySink, event: AITelemetryEvent) -> None:
    """Keep telemetry sink failure from changing the customer response."""

    try:
        sink.emit(event)
    except Exception:
        LOGGER.warning(
            "Pilot telemetry sink rejected request_id=%s tenant_id=%s",
            event.request_id,
            event.tenant_id,
            exc_info=True,
        )


def utc_now() -> datetime:
    """Return an aware UTC timestamp for telemetry construction."""

    return datetime.now(timezone.utc)
