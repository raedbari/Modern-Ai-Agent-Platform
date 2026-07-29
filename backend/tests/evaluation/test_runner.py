"""Tests for the AI evaluation runner."""

from unittest.mock import AsyncMock

import pytest

from backend.app.ai.contracts import GenerationResult
from backend.app.ai.runtime import CoreAIRuntime
from backend.app.evaluation.models import (
    EvaluationCase,
    EvaluationExpectations,
)
from backend.app.evaluation.runner import EvaluationRunner


@pytest.mark.asyncio
async def test_runner_passes_context_and_evaluates_response():
    runtime = AsyncMock(spec=CoreAIRuntime)
    runtime.generate.return_value = GenerationResult(
        content="أهلاً بك في الخدمة",
        model="deepseek-chat",
        finish_reason="stop",
        prompt_tokens=8,
        completion_tokens=6,
    )

    case = EvaluationCase(
        case_id="arabic-001",
        tenant_id="tenant-1",
        agent_id="agent-7",
        user_input="مرحباً",
        expectations=EvaluationExpectations(
            expected_language="ar",
            required_substrings=["أهلاً"],
            forbidden_substrings=["خطأ"],
        ),
    )

    result = await EvaluationRunner(runtime).run_case(case)

    assert result.status == "passed"
    assert result.checks.language_matches is True
    assert result.checks.required_substrings_present is True
    assert result.checks.forbidden_substrings_absent is True
    assert result.prompt_tokens == 8
    assert result.completion_tokens == 6

    request = runtime.generate.await_args.args[0]
    assert request.context.tenant_id == "tenant-1"
    assert request.context.agent_id == "agent-7"
    assert request.messages[0].content == "مرحباً"


@pytest.mark.asyncio
async def test_runner_marks_failed_expectations():
    runtime = AsyncMock(spec=CoreAIRuntime)
    runtime.generate.return_value = GenerationResult(
        content="The requested phrase is missing.",
        model="test-model",
    )

    case = EvaluationCase(
        case_id="failed-001",
        tenant_id="tenant-1",
        agent_id="agent-1",
        user_input="Test",
        expectations=EvaluationExpectations(
            expected_language="en",
            required_substrings=["required answer"],
            forbidden_substrings=["secret"],
        ),
    )

    result = await EvaluationRunner(runtime).run_case(case)

    assert result.status == "failed"
    assert result.checks.language_matches is True
    assert result.checks.required_substrings_present is False


@pytest.mark.asyncio
async def test_runner_hides_provider_exception_details():
    runtime = AsyncMock(spec=CoreAIRuntime)
    runtime.generate.side_effect = RuntimeError(
        "DeepSeek secret-key database-password"
    )

    case = EvaluationCase(
        case_id="error-001",
        tenant_id="tenant-1",
        agent_id="agent-1",
        user_input="Hello",
    )

    result = await EvaluationRunner(runtime).run_case(case)

    assert result.status == "error"
    assert result.error_code == "generation_failed"
    assert result.response_content is None
    assert "secret-key" not in result.model_dump_json()
    assert "database-password" not in result.model_dump_json()