"""Tests for evaluation dataset loading."""

import json

import pytest

from backend.app.evaluation.loader import (
    EvaluationDatasetError,
    load_evaluation_cases,
)


def test_loads_valid_arabic_and_english_cases(tmp_path):
    dataset = tmp_path / "cases.jsonl"

    cases = [
        {
            "case_id": "arabic-001",
            "tenant_id": "tenant-1",
            "agent_id": "agent-1",
            "user_input": "مرحبا",
            "expectations": {
                "expected_language": "ar",
                "required_substrings": ["أهلاً"],
            },
            "tags": ["smoke", "arabic"],
        },
        {
            "case_id": "english-001",
            "tenant_id": "tenant-1",
            "agent_id": "agent-1",
            "user_input": "Hello",
            "expectations": {
                "expected_language": "en",
            },
        },
    ]

    dataset.write_text(
        "\n".join(json.dumps(case, ensure_ascii=False) for case in cases),
        encoding="utf-8",
    )

    loaded = load_evaluation_cases(dataset)

    assert len(loaded) == 2
    assert loaded[0].case_id == "arabic-001"
    assert loaded[0].user_input == "مرحبا"
    assert loaded[1].expectations.expected_language == "en"


def test_rejects_invalid_json_without_exposing_content(tmp_path):
    dataset = tmp_path / "invalid.jsonl"
    dataset.write_text('{"secret": "private-value"', encoding="utf-8")

    with pytest.raises(
        EvaluationDatasetError,
        match="Invalid JSON at line 1",
    ) as error:
        load_evaluation_cases(dataset)

    assert "private-value" not in str(error.value)


def test_rejects_duplicate_case_ids(tmp_path):
    dataset = tmp_path / "duplicates.jsonl"

    case = {
        "case_id": "duplicate-001",
        "tenant_id": "tenant-1",
        "agent_id": "agent-1",
        "user_input": "Hello",
    }

    dataset.write_text(
        "\n".join([json.dumps(case), json.dumps(case)]),
        encoding="utf-8",
    )

    with pytest.raises(
        EvaluationDatasetError,
        match="Duplicate case_id at line 2",
    ):
        load_evaluation_cases(dataset)


def test_rejects_empty_dataset(tmp_path):
    dataset = tmp_path / "empty.jsonl"
    dataset.write_text("\n\n", encoding="utf-8")

    with pytest.raises(
        EvaluationDatasetError,
        match="contains no cases",
    ):
        load_evaluation_cases(dataset)