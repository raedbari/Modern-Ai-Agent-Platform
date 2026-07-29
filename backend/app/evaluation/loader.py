"""Load and validate evaluation datasets from JSONL files."""

import json
from pathlib import Path

from pydantic import ValidationError

from backend.app.evaluation.models import EvaluationCase


class EvaluationDatasetError(ValueError):
    """Raised when an evaluation dataset is invalid."""


def load_evaluation_cases(path: Path) -> list[EvaluationCase]:
    """Load validated evaluation cases from a JSONL file."""

    if path.suffix.lower() != ".jsonl":
        raise EvaluationDatasetError("Evaluation dataset must be a JSONL file")

    if not path.is_file():
        raise EvaluationDatasetError("Evaluation dataset does not exist")

    cases: list[EvaluationCase] = []
    seen_case_ids: set[str] = set()

    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise EvaluationDatasetError(
            "Evaluation dataset could not be read"
        ) from exc

    for line_number, raw_line in enumerate(lines, start=1):
        if not raw_line.strip():
            continue

        try:
            payload = json.loads(raw_line)
        except json.JSONDecodeError as exc:
            raise EvaluationDatasetError(
                f"Invalid JSON at line {line_number}"
            ) from exc

        if not isinstance(payload, dict):
            raise EvaluationDatasetError(
                f"Evaluation case at line {line_number} must be an object"
            )

        try:
            case = EvaluationCase.model_validate(payload)
        except ValidationError as exc:
            raise EvaluationDatasetError(
                f"Invalid evaluation case at line {line_number}"
            ) from exc

        if case.case_id in seen_case_ids:
            raise EvaluationDatasetError(
                f"Duplicate case_id at line {line_number}"
            )

        seen_case_ids.add(case.case_id)
        cases.append(case)

    if not cases:
        raise EvaluationDatasetError("Evaluation dataset contains no cases")

    return cases