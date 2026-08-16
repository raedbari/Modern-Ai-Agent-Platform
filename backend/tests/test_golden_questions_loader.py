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

    def test_dataset_has_minimum_cases(self, dataset_path):
        cases = []
        with open(dataset_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    cases.append(json.loads(line))
        assert len(cases) >= 20

    def test_all_cases_have_required_fields(self, dataset_path):
        with open(dataset_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    case = json.loads(line)
                    assert 'case_id' in case
                    assert 'user_input' in case
                    assert 'tenant_id' in case
                    assert 'agent_id' in case
