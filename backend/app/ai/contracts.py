"""Provider-independent contracts for the Core AI Runtime."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


Identifier = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=128),
]


class RuntimeContext(BaseModel):
    """Identifies and versions one provider-independent AI request."""

    model_config = ConfigDict(frozen=True)

    tenant_id: Identifier
    agent_id: Identifier
    request_id: Identifier | None = None
    product_id: Identifier | None = None
    conversation_id: Identifier | None = None
    prompt_version: Identifier | None = None
    knowledge_version: Identifier | None = None


class ChatMessage(BaseModel):
    """One provider-independent chat message."""

    role: Literal["system", "user", "assistant"]
    content: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1),
    ]


class GenerationRequest(BaseModel):
    """Input required to generate an AI response."""

    context: RuntimeContext
    messages: list[ChatMessage] = Field(min_length=1)
    temperature: float = Field(default=0.2, ge=0, le=2)
    max_output_tokens: int = Field(default=1024, gt=0)


class GenerationResult(BaseModel):
    """Normalized result returned by any generation provider."""

    content: str
    model: str
    finish_reason: str | None = None
    prompt_tokens: int = Field(default=0, ge=0)
    completion_tokens: int = Field(default=0, ge=0)


class EmbeddingRequest(BaseModel):
    """Texts that must be embedded for one tenant and agent.

    Attributes:
        context:    Tenant/agent scoping for the request.
        texts:      List of texts to embed (1–64 items).
        input_type: Voyage AI ``input_type`` hint.  Use ``"document"`` when
                    embedding document chunks for storage in the vector store,
                    and ``"query"`` when embedding a retrieval query.
                    Defaults to ``"document"`` (the safer default for storage).
    """

    context: RuntimeContext
    texts: list[str] = Field(min_length=1, max_length=64)
    input_type: Literal["document", "query"] = "document"


class EmbeddingResult(BaseModel):
    """Normalized embedding result."""

    embeddings: list[list[float]]
    model: str
    dimension: int = Field(gt=0)
