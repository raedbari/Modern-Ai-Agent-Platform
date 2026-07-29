"""DeepSeek generation provider implemented with LangChain."""

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_deepseek import ChatDeepSeek

from backend.app.ai.contracts import (
    ChatMessage,
    GenerationRequest,
    GenerationResult,
)
from backend.app.core.config import Settings


class DeepSeekGenerationProvider:
    """Generate text through DeepSeek using LangChain."""

    def __init__(self, settings: Settings) -> None:
        if settings.deepseek_api_key is None:
            raise ValueError("DeepSeek API key is not configured")

        self._model_name = settings.deepseek_model
        self._model = ChatDeepSeek(
            model=settings.deepseek_model,
            api_key=settings.deepseek_api_key.get_secret_value(),
            api_base=str(settings.deepseek_base_url).rstrip("/"),
            timeout=settings.deepseek_timeout_seconds,
            max_retries=settings.deepseek_max_retries,
        )

    async def generate(
        self,
        request: GenerationRequest,
    ) -> GenerationResult:
        """Generate and normalize one DeepSeek response."""

        messages = [
            self._convert_message(message)
            for message in request.messages
        ]

        configured_model = self._model.bind(
            temperature=request.temperature,
            max_tokens=request.max_output_tokens,
        )

        response = await configured_model.ainvoke(messages)

        if not isinstance(response.content, str):
            raise TypeError("DeepSeek returned non-text content")

        usage = response.usage_metadata or {}
        metadata = response.response_metadata or {}

        return GenerationResult(
            content=response.content,
            model=metadata.get("model_name", self._model_name),
            finish_reason=metadata.get("finish_reason"),
            prompt_tokens=usage.get("input_tokens", 0),
            completion_tokens=usage.get("output_tokens", 0),
        )

    @staticmethod
    def _convert_message(message: ChatMessage) -> BaseMessage:
        """Convert our internal message into a LangChain message."""

        if message.role == "system":
            return SystemMessage(content=message.content)

        if message.role == "user":
            return HumanMessage(content=message.content)

        return AIMessage(content=message.content)