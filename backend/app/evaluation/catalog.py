"""Discover immutable file-backed Evaluation datasets."""

from pathlib import Path

from backend.app.evaluation.loader import (
    EvaluationDatasetError,
    load_evaluation_dataset,
)
from backend.app.evaluation.models import EvaluationDataset


DATASET_DIRECTORY = Path(__file__).resolve().parent / "datasets"


def list_evaluation_datasets() -> list[EvaluationDataset]:
    """Load every valid metadata/JSONL pair in stable order."""

    datasets: list[EvaluationDataset] = []
    for metadata_path in sorted(DATASET_DIRECTORY.glob("*.json")):
        records_path = metadata_path.with_suffix(".jsonl")
        if not records_path.is_file():
            continue
        datasets.append(
            load_evaluation_dataset(records_path, metadata_path)
        )
    return sorted(
        datasets,
        key=lambda item: (item.name, item.version),
    )


def get_evaluation_dataset(name: str, version: str) -> EvaluationDataset:
    """Resolve by validated metadata, never by user-controlled file paths."""

    for dataset in list_evaluation_datasets():
        if dataset.name == name and dataset.version == version:
            return dataset
    raise EvaluationDatasetError("Evaluation dataset not found")
