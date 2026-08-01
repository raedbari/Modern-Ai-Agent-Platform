"""Durable document-ingestion worker."""

from __future__ import annotations

import asyncio
import logging
import os
import socket
from typing import Any
from uuid import uuid4

from backend.app.ai.ports import EmbeddingProvider
from backend.app.ai.providers.ollama import OllamaEmbeddingProvider
from backend.app.core.config import Settings, get_settings
from backend.app.db.base import AsyncSessionLocal
from backend.app.db.models import DocumentModel, IngestionJob
from backend.app.domain.models.enums import DocumentProcessingStatus
from backend.app.infrastructure.storage import LocalUploadStorage
from backend.app.operations.ingestion_runtime import build_ingestion_service
from backend.app.services.knowledge.ingestion_service import IngestionRequest
from backend.app.services.knowledge.job_service import IngestionJobService

LOGGER = logging.getLogger("maap.ingestion_worker")


class IngestionWorker:
    """Claim jobs, process retained source files, and persist outcomes."""

    def __init__(
        self,
        *,
        settings: Settings,
        worker_id: str | None = None,
        session_factory: Any = AsyncSessionLocal,
        embedding_provider: EmbeddingProvider | None = None,
        storage: LocalUploadStorage | None = None,
    ) -> None:
        self._settings = settings
        self._worker_id = worker_id or (
            f"{socket.gethostname()}:{os.getpid()}:{uuid4().hex[:8]}"
        )
        self._sessions = session_factory
        self._storage = storage or LocalUploadStorage(
            settings.upload_storage_root
        )
        self._embedding_provider = (
            embedding_provider or OllamaEmbeddingProvider(settings)
        )

    async def recover_stale_jobs(self) -> int:
        async with self._sessions() as session:
            recovered = await IngestionJobService.recover_stale(
                session,
                lock_timeout_seconds=(
                    self._settings.ingestion_job_lock_timeout_seconds
                ),
            )
            await session.commit()
            return recovered

    async def process_one(self) -> bool:
        """Process one available job; return False when the queue is empty."""

        async with self._sessions() as session:
            job = await IngestionJobService.claim_next(
                session,
                worker_id=self._worker_id,
            )
            if job is None:
                await session.rollback()
                return False
            job_id = job.id
            await session.commit()

        try:
            await self._process_claimed(job_id)
        except Exception:
            LOGGER.exception("Ingestion job %s failed", job_id)
            await self._record_failure(job_id)
        return True

    async def _process_claimed(self, job_id: str) -> None:
        async with self._sessions() as session:
            job = await session.get(IngestionJob, job_id)
            if job is None or job.status != "processing":
                return
            document = await session.get(DocumentModel, job.document_id)
            if (
                document is None
                or document.tenant_id != job.tenant_id
                or document.knowledge_base_id != job.knowledge_base_id
                or document.agent_id != job.agent_id
            ):
                raise RuntimeError("Queued document scope is invalid.")

            content = await self._storage.read(job.storage_key)
            service = build_ingestion_service(
                session=session,
                runtime=self._embedding_provider,
                settings=self._settings,
            )
            await service.reindex(
                document_id=document.id,
                request=IngestionRequest(
                    content=content,
                    filename=document.original_filename,
                    mime_type=document.mime_type,
                    tenant_id=job.tenant_id,
                    agent_id=job.agent_id,
                    knowledge_base_id=job.knowledge_base_id,
                    source_name=document.source_name,
                ),
            )
            await IngestionJobService.mark_succeeded(session, job)
            await session.commit()

    async def _record_failure(self, job_id: str) -> None:
        async with self._sessions() as session:
            job = await session.get(IngestionJob, job_id)
            if job is None:
                return
            document = await session.get(DocumentModel, job.document_id)
            await IngestionJobService.mark_failed_or_retry(
                session,
                job,
                safe_error="Document processing failed.",
            )
            if document is not None and document.tenant_id == job.tenant_id:
                if job.status == "failed":
                    document.status = DocumentProcessingStatus.FAILED.value
                    document.failure_reason = "Document processing failed."
                else:
                    # Do not expose a temporary Ollama failure as a terminal
                    # document failure while the durable job will retry.
                    document.status = DocumentProcessingStatus.PENDING.value
                    document.failure_reason = None
            await session.commit()

    async def run_forever(self) -> None:
        """Poll forever with bounded idle waits and periodic stale recovery."""

        recovered = await self.recover_stale_jobs()
        if recovered:
            LOGGER.warning("Recovered %s stale ingestion job(s)", recovered)

        cycles = 0
        while True:
            worked = await self.process_one()
            cycles += 1
            if cycles % 30 == 0:
                await self.recover_stale_jobs()
            if not worked:
                await asyncio.sleep(
                    self._settings.ingestion_worker_poll_seconds
                )


async def _main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    await IngestionWorker(settings=get_settings()).run_forever()


if __name__ == "__main__":
    asyncio.run(_main())
