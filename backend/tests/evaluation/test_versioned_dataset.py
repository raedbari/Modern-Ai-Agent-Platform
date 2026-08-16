"""Tests for reusable, versioned evaluation contracts."""

import json
from pathlib import Path

from backend.app.evaluation.loader import load_evaluation_dataset
from backend.app.evaluation.models import (
    EvaluationRunConfiguration,
    ExperimentComparison,
)


def test_golden_questions_v1_has_versioned_metadata() -> None:
    dataset_dir = (
        Path(__file__).parents[2] / "app" / "evaluation" / "datasets"
    )

    dataset = load_evaluation_dataset(
        dataset_dir / "golden_questions_v1.jsonl",
        dataset_dir / "golden_questions_v1.json",
    )

    assert dataset.name == "golden-questions"
    assert dataset.version == "v1"
    assert dataset.classification == "synthetic-test-data"
    assert len(dataset.records) == 20
    assert all(case.expectations.answerable is not None for case in dataset.records)
    assert all(case.category != "general" for case in dataset.records)
    assert any("tenant-isolation" in case.tags for case in dataset.records)
    assert any(case.expectations.expected_language == "ar" for case in dataset.records)


def test_minimal_experiment_record_is_serializable() -> None:
    base = EvaluationRunConfiguration(
        dataset_name="golden-questions",
        dataset_version="v1",
        agent_version="agent-v1",
        prompt_version="v1",
        knowledge_version="kb-v1",
        model_provider="deepseek",
        model_name="deepseek-chat",
    )
    comparison = ExperimentComparison(
        experiment_id="prompt-v1-v2",
        dataset_name="golden-questions",
        dataset_version="v1",
        configuration_a=base,
        configuration_b=base.model_copy(update={"prompt_version": "v2"}),
        metrics_a={"pass_rate": 80.0},
        metrics_b={"pass_rate": 85.0},
    )

    assert json.loads(comparison.model_dump_json())["metrics_b"]["pass_rate"] == 85.0
