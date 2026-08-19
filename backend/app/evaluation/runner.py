"""Execute evaluation cases through the production ChatWorkflow boundary."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from time import perf_counter
from uuid import uuid4

from backend.app.ai.chat_workflow import ChatWorkflow
from backend.app.auth.context import ChatExecutionContext
from backend.app.evaluation.models import (
    EvaluationCase,
    EvaluationCaseResult,
    EvaluationChecks,
    EvaluationRun,
    EvaluationRunConfiguration,
    RAGMetrics,
)
from backend.app.evaluation.report import build_evaluation_summary


class EvaluationRunner:
    """Run controlled cases through the same workflow used by production chat."""

    def __init__(
        self,
        workflow: ChatWorkflow,
        configuration: EvaluationRunConfiguration,
        *,
        execution_context: ChatExecutionContext | None = None,
    ) -> None:
        self._workflow = workflow
        self._configuration = configuration
        self._execution_context = execution_context

    async def run_case(self, case: EvaluationCase) -> EvaluationCaseResult:
        """Execute one full RAG case and derive metrics from its observation."""

        started_at = perf_counter()
        try:
            context = (
                replace(
                    self._execution_context,
                    tenant_id=case.tenant_id,
                    agent_id=case.agent_id,
                    request_id=str(uuid4()),
                    product_id="athkachatbots",
                    prompt_version=self._configuration.prompt_version,
                    knowledge_version=self._configuration.knowledge_version,
                    model_provider=self._configuration.model_provider,
                )
                if self._execution_context is not None
                else ChatExecutionContext(
                    tenant_id=case.tenant_id,
                    agent_id=case.agent_id,
                    system_prompt="Use verified evaluation evidence only.",
                    request_id=str(uuid4()),
                    product_id="athkachatbots",
                    prompt_version=self._configuration.prompt_version,
                    knowledge_version=self._configuration.knowledge_version,
                    model_provider=self._configuration.model_provider,
                    knowledge_mode="required",
                )
            )
            execution = await self._workflow.execute(
                context=context,
                message=case.user_input,
            )
        except Exception:
            latency_ms = (perf_counter() - started_at) * 1000
            return EvaluationCaseResult(
                case_id=case.case_id,
                tenant_id=case.tenant_id,
                agent_id=case.agent_id,
                status="error",
                latency_ms=latency_ms,
                checks=EvaluationChecks(),
                rag_metrics=RAGMetrics(
                    failure=True,
                    answer_status="error",
                    retrieval_status="not_measured",
                    rerank_status="not_measured",
                    groundedness_status="not_measured",
                    citation_status="not_measured",
                ),
                prompt_version=self._configuration.prompt_version,
                knowledge_version=self._configuration.knowledge_version,
                model_provider=self._configuration.model_provider,
                answer_status="error",
                error_code="pipeline_failed",
            )

        latency_ms = (perf_counter() - started_at) * 1000
        content = execution.reply
        expectations = case.expectations
        supplied_ids = [source.document_id for source in execution.supplied_sources]
        cited_ids = [source.document_id for source in execution.cited_sources]
        expected_ids = expectations.expected_source_ids
        expected_source_presence = (
            all(source_id in supplied_ids for source_id in expected_ids)
            if expected_ids
            else None
        )
        correctly_cited = [
            source_id for source_id in expected_ids if source_id in cited_ids
        ]
        citation_accuracy = (
            not execution.invalid_citation_ids
            and all(source_id in cited_ids for source_id in expected_ids)
            if expectations.answerable is True
            else None
        )
        correct_refusal = (
            execution.answer_status == "insufficient_knowledge"
            if expectations.answerable is False
            else None
        )
        expected_facts_present = (
            all(_contains(content, fact) for fact in expectations.expected_facts)
            if expectations.expected_facts
            else None
        )
        forbidden_claims_absent = (
            all(not _contains(content, claim) for claim in expectations.forbidden_claims)
            if expectations.forbidden_claims
            else None
        )
        groundedness = (
            bool(expected_facts_present)
            and forbidden_claims_absent is not False
            if expectations.answerable is True and expectations.expected_facts
            else None
        )
        expected_source_position = next(
            (
                position
                for position, source_id in enumerate(supplied_ids, start=1)
                if source_id in expected_ids
            ),
            None,
        )

        checks = EvaluationChecks(
            language_matches=_matches_expected_language(
                content=content,
                expected_language=(
                    expectations.expected_language or case.language
                ),
            ),
            required_substrings_present=all(
                _contains(content, required)
                for required in expectations.required_substrings
            ),
            forbidden_substrings_absent=all(
                not _contains(content, forbidden)
                for forbidden in expectations.forbidden_substrings
            ),
            latency_within_limit=(
                latency_ms <= expectations.max_latency_ms
                if expectations.max_latency_ms is not None
                else None
            ),
            expected_facts_present=expected_facts_present,
            forbidden_claims_absent=forbidden_claims_absent,
        )
        rag_metrics = RAGMetrics(
            retrieval_hit=bool(execution.supplied_sources),
            retrieval_count=execution.retrieval_count,
            top_similarity_score=(
                execution.supplied_sources[0].similarity_score
                if execution.supplied_sources
                else None
            ),
            expected_source_position=expected_source_position,
            rerank_count=execution.rerank_count,
            has_citations=bool(execution.cited_sources),
            citation_count=len(execution.cited_sources),
            answer_status=execution.answer_status,
            top_k_source_presence=expected_source_presence,
            groundedness=groundedness,
            correct_refusal=correct_refusal,
            citation_accuracy=citation_accuracy,
            failure=False,
            retrieval_status="measured",
            rerank_status=(
                "measured"
                if execution.rerank_count is not None
                else "not_measured"
            ),
            groundedness_status=(
                "measured" if groundedness is not None else "not_measured"
            ),
            citation_status=(
                "measured"
                if expectations.answerable is True
                else "not_measured"
            ),
            supplied_source_ids=supplied_ids,
            cited_source_ids=cited_ids,
            invalid_citation_ids=list(execution.invalid_citation_ids),
            correctly_cited_expected_source_ids=correctly_cited,
        )
        passed = all(
            value is not False
            for value in (
                checks.language_matches,
                checks.required_substrings_present,
                checks.forbidden_substrings_absent,
                checks.latency_within_limit,
                checks.expected_facts_present,
                checks.forbidden_claims_absent,
                expected_source_presence,
                citation_accuracy,
                correct_refusal,
            )
        )
        return EvaluationCaseResult(
            case_id=case.case_id,
            tenant_id=case.tenant_id,
            agent_id=case.agent_id,
            status="passed" if passed else "failed",
            response_content=content,
            model=execution.model,
            finish_reason=execution.finish_reason,
            prompt_tokens=execution.prompt_tokens,
            completion_tokens=execution.completion_tokens,
            latency_ms=latency_ms,
            checks=checks,
            rag_metrics=rag_metrics,
            prompt_version=self._configuration.prompt_version,
            knowledge_version=self._configuration.knowledge_version,
            model_provider=self._configuration.model_provider,
            answer_status=execution.answer_status,
        )

    async def run(
        self,
        cases: list[EvaluationCase],
        *,
        run_id: str | None = None,
    ) -> EvaluationRun:
        """Execute a stable case sequence as one versioned evaluation run."""

        started_at = datetime.now(timezone.utc)
        results = [await self.run_case(case) for case in cases]
        completed_at = datetime.now(timezone.utc)
        return EvaluationRun(
            run_id=run_id or str(uuid4()),
            configuration=self._configuration,
            started_at=started_at,
            completed_at=completed_at,
            status=(
                "failed" if any(result.status == "error" for result in results)
                else "completed"
            ),
            results=results,
            summary=build_evaluation_summary(results),
        )


def _contains(content: str, expected: str) -> bool:
    return expected.casefold() in content.casefold()


def _matches_expected_language(
    content: str,
    expected_language: str | None,
) -> bool | None:
    if expected_language is None:
        return None
    has_arabic = any("\u0600" <= character <= "\u06ff" for character in content)
    has_latin = any(character.isascii() and character.isalpha() for character in content)
    if expected_language == "ar":
        return has_arabic
    if expected_language in {"en", "de"}:
        return has_latin and not has_arabic
    return False
