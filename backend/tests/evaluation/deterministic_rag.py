"""Deterministic provider/repository adapters for full-RAG evaluation tests."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

from backend.app.ai.chat_workflow import INSUFFICIENT_EVIDENCE_SENTINEL
from backend.app.ai.contracts import (
    EmbeddingRequest,
    EmbeddingResult,
    GenerationRequest,
    GenerationResult,
)
from backend.app.ai.ports import RerankRequest, RerankResult
from backend.app.domain.models.chunk import Chunk
from backend.app.domain.models.knowledge_base import KnowledgeBase
from backend.app.telemetry import InMemoryTelemetrySink

_INTENTS = (
    ("refund", "return", "returned", "استرجاع"),
    ("domestic",),
    ("international",),
    ("warranty", "electronics", "water damage"),
    ("onboarding", "verify email", "upload knowledge"),
    ("track", "tracking", "تتبع", "أتتبع"),
    ("premium", "49 test credits"),
    ("updated", "2026-01-15"),
    ("address", "dispatch"),
    ("privacy", "retained", "support chats"),
    ("sustainability", "2030"),
    ("world cup",),
    ("launch code", "blue-orchid", "tenant b"),
)


def deterministic_vector(text: str) -> list[float]:
    """Map controlled semantic intents to a stable normalized vector."""

    normalized = text.casefold()
    vector = [
        1.0 if any(term in normalized for term in terms) else 0.0
        for terms in _INTENTS
    ]
    length = math.sqrt(sum(value * value for value in vector))
    return [value / length for value in vector] if length else vector


def _similarity(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


def dataset_directory() -> Path:
    return Path(__file__).parents[2] / "app" / "evaluation" / "datasets"


def load_controlled_payloads() -> list[dict[str, object]]:
    path = dataset_directory() / "golden_questions_v1.jsonl"
    return [json.loads(line) for line in path.read_text().splitlines() if line]


class DeterministicEmbeddingProvider:
    def __init__(self) -> None:
        self.requests: list[EmbeddingRequest] = []

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        self.requests.append(request)
        vectors = [deterministic_vector(text) for text in request.texts]
        return EmbeddingResult(
            embeddings=vectors,
            model="deterministic-embedding-v1",
            dimension=len(_INTENTS),
        )


class TenantScopedFixtureRepositories:
    """Both repository ports over immutable controlled fixture records."""

    def __init__(self) -> None:
        fixture_path = dataset_directory() / "golden_questions_v1_knowledge.jsonl"
        payloads = [
            json.loads(line)
            for line in fixture_path.read_text().splitlines()
            if line
        ]
        self.chunks = [
            Chunk(
                id=f"chunk-{payload['document_id']}",
                tenant_id=str(payload["tenant_id"]),
                agent_id=str(payload["agent_id"]),
                knowledge_base_id=str(payload["knowledge_base_id"]),
                document_id=str(payload["document_id"]),
                source_name=str(payload["source_name"]),
                page_number=0,
                chunk_index=0,
                content=str(payload["content"]),
                content_hash=f"fixture-{payload['document_id']}",
            )
            for payload in payloads
        ]
        self.search_calls: list[dict[str, object]] = []
        self.scope_calls: list[tuple[str, str]] = []

    async def list_for_agent(
        self,
        agent_id: str,
        tenant_id: str,
    ) -> list[KnowledgeBase]:
        self.scope_calls.append((tenant_id, agent_id))
        kb_ids = {
            chunk.knowledge_base_id
            for chunk in self.chunks
            if chunk.tenant_id == tenant_id and chunk.agent_id == agent_id
        }
        return [
            KnowledgeBase(id=kb_id, tenant_id=tenant_id, name="Fixture KB")
            for kb_id in sorted(kb_ids)
        ]

    async def semantic_search(
        self,
        query_embedding: list[float],
        tenant_id: str,
        agent_id: str,
        knowledge_base_id: str,
        top_k: int,
        min_similarity: float,
    ) -> list[tuple[Chunk, float]]:
        self.search_calls.append(
            {
                "tenant_id": tenant_id,
                "agent_id": agent_id,
                "knowledge_base_id": knowledge_base_id,
            }
        )
        scored = [
            (chunk, _similarity(query_embedding, deterministic_vector(chunk.content)))
            for chunk in self.chunks
            if chunk.tenant_id == tenant_id
            and chunk.agent_id == agent_id
            and chunk.knowledge_base_id == knowledge_base_id
        ]
        return [
            pair
            for pair in sorted(scored, key=lambda pair: pair[1], reverse=True)
            if pair[1] >= min_similarity
        ][:top_k]


class DeterministicRerankProvider:
    def __init__(self) -> None:
        self.requests: list[RerankRequest] = []

    async def rerank(self, request: RerankRequest) -> RerankResult:
        self.requests.append(request)
        query_vector = deterministic_vector(request.query)
        scored = [
            (index, _similarity(query_vector, deterministic_vector(document)))
            for index, document in enumerate(request.documents)
        ]
        ranked = sorted(scored, key=lambda pair: (-pair[1], pair[0]))
        limit = request.top_k or len(ranked)
        selected = ranked[:limit]
        return RerankResult(
            ranked_indices=[index for index, _ in selected],
            scores=[score for _, score in selected],
        )


class DeterministicGenerationProvider:
    """Answer only when every controlled expected source was supplied."""

    def __init__(self) -> None:
        self.requests: list[GenerationRequest] = []
        self._cases = {
            (
                str(payload["tenant_id"]),
                str(payload["agent_id"]),
                str(payload["user_input"]),
            ): payload
            for payload in load_controlled_payloads()
        }

    async def generate(self, request: GenerationRequest) -> GenerationResult:
        self.requests.append(request)
        question = request.messages[-1].content
        payload = self._cases[
            (request.context.tenant_id, request.context.agent_id, question)
        ]
        expectations = payload["expectations"]
        if not isinstance(expectations, dict):
            raise TypeError("controlled expectations must be an object")
        if expectations.get("answerable") is not True:
            content = INSUFFICIENT_EVIDENCE_SENTINEL
        else:
            evidence = "\n".join(
                message.content
                for message in request.messages
                if message.role == "system"
            )
            citation_by_document = {
                document_id: citation_id
                for citation_id, document_id in re.findall(
                    r"\[(S\d+)\].*?document=([^;\n]+)",
                    evidence,
                )
            }
            expected_sources = expectations.get("expected_source_ids", [])
            if not all(source in citation_by_document for source in expected_sources):
                content = INSUFFICIENT_EVIDENCE_SENTINEL
            else:
                citations = " ".join(
                    f"[{citation_by_document[source]}]"
                    for source in expected_sources
                )
                content = f"{expectations['expected_answer']} {citations}".strip()
        return GenerationResult(
            content=content,
            model="deterministic-generation-v1",
            finish_reason="stop",
            prompt_tokens=17,
            completion_tokens=9,
        )
