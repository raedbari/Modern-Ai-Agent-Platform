"""Durable document-ingestion worker."""

from __future__ import annotations

import asyncio
import logging
import os
import socket
from typing import Any
from uuid import uuid4

from sqlalchemy import select

from backend.app.ai.ports import EmbeddingProvider
from backend.app.core.config import Settings, get_settings
from backend.app.db.base import AsyncSessionLocal
from backend.app.db.models import DocumentModel, IngestionJob
from backend.app.domain.models.enums import DocumentProcessingStatus
from backend.app.infrastructure.storage import LocalUploadStorage
from backend.app.operations.ingestion_runtime import build_ingestion_service
from backend.app.services.knowledge.ingestion_service import IngestionRequest
from backend.app.services.audit import AuditService
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
        if embedding_provider is not None:
            self._embedding_provider = embedding_provider
        else:
            from backend.app.ai.providers.voyage import VoyageEmbeddingProvider
            self._embedding_provider = VoyageEmbeddingProvider(settings)

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
        # Snapshot the job and document scope in a short read transaction.
        async with self._sessions() as session:
            job = await session.get(IngestionJob, job_id)

            if job is None or job.status != "processing":
                await session.rollback()
                return

            document = await session.get(
                DocumentModel,
                job.document_id,
            )

            if (
                document is None
                or document.tenant_id != job.tenant_id
                or document.knowledge_base_id
                != job.knowledge_base_id
                or document.agent_id != job.agent_id
            ):
                raise RuntimeError(
                    "Queued document scope is invalid."
                )

            storage_key = job.storage_key
            document_id = document.id
            filename = (
                job.source_filename
                or document.original_filename
            )
            mime_type = (
                job.source_mime_type
                or document.mime_type
            )
            source_name = (
                job.source_name
                or document.source_name
            )
            tenant_id = job.tenant_id
            agent_id = job.agent_id
            knowledge_base_id = job.knowledge_base_id
            was_active = (
                document.status
                == DocumentProcessingStatus.READY.value
            )

            await session.rollback()

        # Local storage and external embedding work must not hold a database
        # transaction open.
        content = await self._storage.read(storage_key)

        request = IngestionRequest(
            content=content,
            filename=filename,
            mime_type=mime_type,
            tenant_id=tenant_id,
            agent_id=agent_id,
            knowledge_base_id=knowledge_base_id,
            source_name=source_name,
        )

        async with self._sessions() as session:
            service = build_ingestion_service(
                session=session,
                runtime=self._embedding_provider,
                settings=self._settings,
            )

            document = await service.validate_reindex_target(
                document_id=document_id,
                request=request,
            )

            # End all validation reads before parsing and embeddings.
            await session.rollback()

            prepared = await service.prepare_reindex(
                document=document,
                request=request,
            )

            # Start a new short transaction only for final activation.
            job = await session.scalar(
                select(IngestionJob)
                .where(
                    IngestionJob.id == job_id,
                    IngestionJob.status == "processing",
                    IngestionJob.locked_by == self._worker_id,
                )
                .with_for_update()
            )

            if job is None:
                raise RuntimeError(
                    "The ingestion job is no longer owned "
                    "by this worker."
                )

            result = await service.activate_prepared_reindex(
                document_id=document_id,
                request=request,
                prepared=prepared,
            )

            event_type = (
                "knowledge_document_replaced"
                if was_active
                else "knowledge_document_activated"
            )

            await AuditService.write(
                session,
                event_type=event_type,
                outcome="success",
                admin_id=None,
                target_type="knowledge_document",
                target_id=document_id,
                detail={
                    "tenant_id": tenant_id,
                    "agent_id": agent_id,
                    "knowledge_base_id": knowledge_base_id,
                    "job_id": job_id,
                    "chunks_persisted": result.chunks_persisted,
                },
            )

            await IngestionJobService.mark_succeeded(
                session,
                job,
            )

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
                replacement_of_active_document = (
                    document.status
                    == DocumentProcessingStatus.READY.value
                )

                if not replacement_of_active_document:
                    if job.status == "failed":
                        document.status = (
                            DocumentProcessingStatus.FAILED.value
                        )
                        document.failure_reason = (
                            "Document processing failed."
                        )
                    else:
                        # New documents remain unavailable to RAG while the
                        # durable job waits for another processing attempt.
                        document.status = (
                            DocumentProcessingStatus.PENDING.value
                        )
                        document.failure_reason = None
            if job.status == "failed":
                await AuditService.write(
                    session,
                    event_type=(
                        "knowledge_document_processing_failed"
                    ),
                    outcome="failure",
                    admin_id=None,
                    target_type="knowledge_document",
                    target_id=job.document_id,
                    detail={
                        "tenant_id": job.tenant_id,
                        "agent_id": job.agent_id,
                        "knowledge_base_id":
                            job.knowledge_base_id,
                        "job_id": job.id,
                        "attempts": job.attempts,
                        "max_attempts": job.max_attempts,
                    },
                )

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
