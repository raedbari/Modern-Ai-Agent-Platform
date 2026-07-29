"""Execute evaluation cases through the Core AI Runtime."""

from time import perf_counter

from backend.app.ai.contracts import (
    ChatMessage,
    GenerationRequest,
    RuntimeContext,
)
from backend.app.ai.runtime import CoreAIRuntime
from backend.app.evaluation.models import (
    EvaluationCase,
    EvaluationCaseResult,
    EvaluationChecks,
)


class EvaluationRunner:
    """Runs deterministic evaluation cases through CoreAIRuntime."""

    def __init__(self, runtime: CoreAIRuntime) -> None:
        self._runtime = runtime

    async def run_case(
        self,
        case: EvaluationCase,
    ) -> EvaluationCaseResult:
        """Execute and evaluate one case without exposing provider errors."""

        request = GenerationRequest(
            context=RuntimeContext(
                tenant_id=case.tenant_id,
                agent_id=case.agent_id,
            ),
            messages=[
                ChatMessage(
                    role="user",
                    content=case.user_input,
                )
            ],
        )

        started_at = perf_counter()

        try:
            generation = await self._runtime.generate(request)
        except Exception:
            latency_ms = (perf_counter() - started_at) * 1000

            return EvaluationCaseResult(
                case_id=case.case_id,
                tenant_id=case.tenant_id,
                agent_id=case.agent_id,
                status="error",
                latency_ms=latency_ms,
                checks=EvaluationChecks(),
                error_code="generation_failed",
            )

        latency_ms = (perf_counter() - started_at) * 1000
        content = generation.content

        checks = EvaluationChecks(
            language_matches=_matches_expected_language(
                content=content,
                expected_language=case.expectations.expected_language,
            ),
            required_substrings_present=all(
                required in content
                for required in case.expectations.required_substrings
            ),
            forbidden_substrings_absent=all(
                forbidden not in content
                for forbidden in case.expectations.forbidden_substrings
            ),
            latency_within_limit=(
                latency_ms <= case.expectations.max_latency_ms
                if case.expectations.max_latency_ms is not None
                else None
            ),
        )

        passed = all(
            check is not False
            for check in (
                checks.language_matches,
                checks.required_substrings_present,
                checks.forbidden_substrings_absent,
                checks.latency_within_limit,
            )
        )

        return EvaluationCaseResult(
            case_id=case.case_id,
            tenant_id=case.tenant_id,
            agent_id=case.agent_id,
            status="passed" if passed else "failed",
            response_content=content,
            model=generation.model,
            finish_reason=generation.finish_reason,
            prompt_tokens=generation.prompt_tokens,
            completion_tokens=generation.completion_tokens,
            latency_ms=latency_ms,
            checks=checks,
        )

    async def run(
        self,
        cases: list[EvaluationCase],
    ) -> list[EvaluationCaseResult]:
        """Execute evaluation cases in stable dataset order."""

        return [await self.run_case(case) for case in cases]


def _matches_expected_language(
    content: str,
    expected_language: str | None,
) -> bool | None:
    """Perform a basic deterministic script-level language check."""

    if expected_language is None:
        return None

    has_arabic = any(
        "\u0600" <= character <= "\u06ff"
        for character in content
    )
    has_latin = any(character.isascii() and character.isalpha() for character in content)

    if expected_language == "ar":
        return has_arabic

    if expected_language in {"en", "de"}:
        return has_latin and not has_arabic

    return False