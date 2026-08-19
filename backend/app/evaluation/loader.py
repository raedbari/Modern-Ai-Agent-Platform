"""Load and validate evaluation datasets from files and uploads."""

import csv
import io
import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from backend.app.evaluation.models import EvaluationCase, EvaluationDataset


class EvaluationDatasetError(ValueError):
    """Raised when an evaluation dataset is invalid."""


def _validation_message(
    exc: ValidationError,
    *,
    position: str,
) -> str:
    issue = exc.errors(include_url=False)[0]
    location = ".".join(str(part) for part in issue["loc"])
    suffix = f" field '{location}'" if location else ""
    return f"Invalid evaluation case at {position}{suffix}: {issue['msg']}"


def validate_evaluation_case_payloads(
    payloads: list[Any],
    *,
    positions: list[str] | None = None,
) -> list[EvaluationCase]:
    """Validate case objects with the canonical EvaluationCase schema."""

    cases: list[EvaluationCase] = []
    seen_case_ids: set[str] = set()
    for index, payload in enumerate(payloads, start=1):
        position = positions[index - 1] if positions else f"item {index}"
        if not isinstance(payload, dict):
            raise EvaluationDatasetError(
                f"Evaluation case at {position} must be an object"
            )
        try:
            case = EvaluationCase.model_validate(payload)
        except ValidationError as exc:
            raise EvaluationDatasetError(
                _validation_message(exc, position=position)
            ) from exc
        if case.case_id in seen_case_ids:
            raise EvaluationDatasetError(
                f"Duplicate case_id at {position}: '{case.case_id}'"
            )
        seen_case_ids.add(case.case_id)
        cases.append(case)
    if not cases:
        raise EvaluationDatasetError("Evaluation dataset contains no cases")
    return cases


def parse_evaluation_upload(
    content: bytes,
    *,
    file_name: str,
) -> list[EvaluationCase]:
    """Parse a JSON or CSV upload and validate every canonical case."""

    suffix = Path(file_name).suffix.lower()
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise EvaluationDatasetError(
            "Dataset file must use UTF-8 encoding"
        ) from exc

    if suffix == ".json":
        try:
            document = json.loads(text)
        except json.JSONDecodeError as exc:
            raise EvaluationDatasetError(
                f"Invalid JSON at line {exc.lineno}, column {exc.colno}"
            ) from exc
        if isinstance(document, dict):
            document = document.get("records", document.get("cases"))
        if not isinstance(document, list):
            raise EvaluationDatasetError(
                "JSON dataset must be an array, or an object with a "
                "records/cases array"
            )
        return validate_evaluation_case_payloads(document)

    if suffix == ".csv":
        try:
            reader = csv.DictReader(io.StringIO(text, newline=""))
            if reader.fieldnames is None:
                raise EvaluationDatasetError(
                    "CSV dataset must include a header row"
                )
            rows: list[dict[str, Any]] = []
            positions: list[str] = []
            for row_number, raw_row in enumerate(reader, start=2):
                if None in raw_row:
                    raise EvaluationDatasetError(
                        f"CSV row {row_number} has more values than headers"
                    )
                row = {
                    key.strip(): value.strip()
                    for key, value in raw_row.items()
                    if key is not None and value is not None and value.strip()
                }
                for json_field in ("expectations", "tags"):
                    if json_field not in row:
                        continue
                    try:
                        row[json_field] = json.loads(row[json_field])
                    except json.JSONDecodeError as exc:
                        raise EvaluationDatasetError(
                            f"CSV row {row_number} field '{json_field}' "
                            "must contain valid JSON"
                        ) from exc
                rows.append(row)
                positions.append(f"CSV row {row_number}")
        except csv.Error as exc:
            raise EvaluationDatasetError(f"Invalid CSV: {exc}") from exc
        return validate_evaluation_case_payloads(rows, positions=positions)

    raise EvaluationDatasetError("Dataset file must be JSON or CSV")


def load_evaluation_cases(path: Path) -> list[EvaluationCase]:
    """Load validated evaluation cases from a JSONL file."""

    if path.suffix.lower() != ".jsonl":
        raise EvaluationDatasetError("Evaluation dataset must be a JSONL file")

    if not path.is_file():
        raise EvaluationDatasetError("Evaluation dataset does not exist")

    payloads: list[Any] = []
    positions: list[str] = []

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

        payloads.append(payload)
        positions.append(f"line {line_number}")

    return validate_evaluation_case_payloads(payloads, positions=positions)


def load_evaluation_dataset(
    records_path: Path,
    metadata_path: Path,
) -> EvaluationDataset:
    """Load version metadata and validated JSONL records as one dataset."""

    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EvaluationDatasetError(
            "Evaluation dataset metadata could not be loaded"
        ) from exc
    if not isinstance(metadata, dict):
        raise EvaluationDatasetError(
            "Evaluation dataset metadata must be an object"
        )
    try:
        return EvaluationDataset.model_validate(
            {**metadata, "records": load_evaluation_cases(records_path)}
        )
    except ValidationError as exc:
        raise EvaluationDatasetError(
            "Evaluation dataset metadata is invalid"
        ) from exc
