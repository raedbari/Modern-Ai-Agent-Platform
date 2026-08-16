"""Tests for Golden Questions dataset loading."""
import json
import pytest
from pathlib import Path

class TestGoldenQuestionsDataset:
    @pytest.fixture
    def dataset_path(self):
        return Path(__file__).parent.parent / "app" / "evaluation" / "datasets" / "golden_questions_v1.jsonl"

    def test_dataset_file_exists(self, dataset_path):
        assert dataset_path.exists()

    def test_dataset_is_valid_jsonl(self, dataset_path):
        with open(dataset_path, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if line.strip():
                    json.loads(line)  # Should not raise

    def test_dataset_has_exactly_twenty_cases(self, dataset_path):
        cases = []
        with open(dataset_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    cases.append(json.loads(line))
        assert len(cases) == 20
        assert len({case["case_id"] for case in cases}) == 20

    def test_all_cases_have_required_fields(self, dataset_path):
        with open(dataset_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    case = json.loads(line)
                    assert 'case_id' in case
                    assert 'user_input' in case
                    assert 'tenant_id' in case
                    assert 'agent_id' in case
                    assert case.get("category")
                    assert case.get("difficulty") in {"easy", "medium", "hard"}
                    assert case.get("language") in {"ar", "en", "de"}
                    expectations = case["expectations"]
                    assert isinstance(expectations.get("answerable"), bool)
                    if expectations["answerable"]:
                        assert expectations.get("expected_answer")
                        assert expectations.get("expected_facts")
                        assert expectations.get("expected_source_ids")

    def test_controlled_knowledge_fixtures_are_tenant_and_agent_scoped(
        self,
        dataset_path,
    ):
        fixture_path = dataset_path.with_name(
            "golden_questions_v1_knowledge.jsonl"
        )
        fixtures = [
            json.loads(line)
            for line in fixture_path.read_text(encoding="utf-8").splitlines()
            if line
        ]

        assert fixtures
        assert all(item.get("tenant_id") for item in fixtures)
        assert all(item.get("agent_id") for item in fixtures)
        assert all(item.get("knowledge_base_id") for item in fixtures)
        assert all(item.get("document_id") for item in fixtures)
