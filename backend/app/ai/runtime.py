"""Core AI Runtime orchestration using LangGraph."""

from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from backend.app.ai.contracts import (
    EmbeddingRequest,
    EmbeddingResult,
    GenerationRequest,
    GenerationResult,
)
from backend.app.ai.ports import EmbeddingProvider, GenerationProvider


class RuntimeState(TypedDict):
    """State passed through the generation graph."""

    request: GenerationRequest
    result: GenerationResult | None


class CoreAIRuntime:
    """Provider-independent runtime for generation and embeddings."""

    def __init__(
        self,
        generation_provider: GenerationProvider,
        embedding_provider: EmbeddingProvider,
    ) -> None:
        self._generation_provider = generation_provider
        self._embedding_provider = embedding_provider

        graph = StateGraph(RuntimeState)
        graph.add_node("generate", self._generate_node)
        graph.add_edge(START, "generate")
        graph.add_edge("generate", END)

        self._graph = graph.compile()

    async def _generate_node(
        self,
        state: RuntimeState,
    ) -> dict[str, GenerationResult]:
        result = await self._generation_provider.generate(state["request"])
        return {"result": result}

    async def generate(
        self,
        request: GenerationRequest,
    ) -> GenerationResult:
        state = await self._graph.ainvoke(
            {
                "request": request,
                "result": None,
            }
        )

        result = state.get("result")
        if result is None:
            raise RuntimeError("Generation graph returned no result")

        return result

    async def embed(
        self,
        request: EmbeddingRequest,
    ) -> EmbeddingResult:
        return await self._embedding_provider.embed(request)