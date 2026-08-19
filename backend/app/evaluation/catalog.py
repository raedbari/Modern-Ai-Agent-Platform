"""Discover built-in and durable uploaded Evaluation datasets."""

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import EvaluationDatasetRecord

from backend.app.evaluation.loader import (
    EvaluationDatasetError,
    load_evaluation_dataset,
)
from backend.app.evaluation.models import EvaluationDataset


DATASET_DIRECTORY = Path(__file__).resolve().parent / "datasets"


def _list_builtin_datasets() -> list[EvaluationDataset]:
    """Load every valid built-in metadata/JSONL pair in stable order."""

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


def _from_record(row: EvaluationDatasetRecord) -> EvaluationDataset:
    return EvaluationDataset.model_validate(
        {
            "name": row.name,
            "owner": row.owner,
            "domain": row.domain,
            "version": row.version,
            "status": row.status,
            "classification": row.classification,
            "records": row.records_json,
        }
    )


async def list_evaluation_datasets(
    session: AsyncSession,
) -> list[EvaluationDataset]:
    """List built-in datasets and uploaded versions in stable order."""

    uploaded = [
        _from_record(row)
        for row in (
            await session.scalars(
                select(EvaluationDatasetRecord).order_by(
                    EvaluationDatasetRecord.name,
                    EvaluationDatasetRecord.version,
                )
            )
        ).all()
    ]
    return sorted(
        [*_list_builtin_datasets(), *uploaded],
        key=lambda item: (item.name, item.version),
    )


async def get_evaluation_dataset(
    session: AsyncSession,
    name: str,
    version: str,
) -> EvaluationDataset:
    """Resolve by validated metadata, never by user-controlled file paths."""

    for dataset in _list_builtin_datasets():
        if dataset.name == name and dataset.version == version:
            return dataset
    row = await session.get(EvaluationDatasetRecord, (name, version))
    if row is not None:
        return _from_record(row)
    raise EvaluationDatasetError("Evaluation dataset not found")
