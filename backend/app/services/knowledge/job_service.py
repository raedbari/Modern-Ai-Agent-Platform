"""Durable PostgreSQL-backed ingestion job queue."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models import IngestionJob


class IngestionJobService:
    """Enqueue and atomically claim document ingestion work."""

    @staticmethod
    async def enqueue(
        session: AsyncSession,
        *,
        tenant_id: str,
        agent_id: str,
        knowledge_base_id: str,
        document_id: str,
        storage_key: str,
        max_attempts: int,
    ) -> IngestionJob:
        if max_attempts <= 0:
            raise ValueError("max_attempts must be positive.")
        job = IngestionJob(
            id=str(uuid4()),
            tenant_id=tenant_id,
            agent_id=agent_id,
            knowledge_base_id=knowledge_base_id,
            document_id=document_id,
            storage_key=storage_key,
            max_attempts=max_attempts,
        )
        session.add(job)
        await session.flush()
        return job

    @staticmethod
    async def get_scoped(
        session: AsyncSession,
        *,
        job_id: str,
        tenant_id: str,
        agent_id: str,
        knowledge_base_id: str | None = None,
    ) -> IngestionJob | None:
        statement = select(IngestionJob).where(
            IngestionJob.id == job_id,
            IngestionJob.tenant_id == tenant_id,
            IngestionJob.agent_id == agent_id,
        )
        if knowledge_base_id is not None:
            statement = statement.where(
                IngestionJob.knowledge_base_id == knowledge_base_id
            )
        return await session.scalar(statement)

    @staticmethod
    async def claim_next(
        session: AsyncSession,
        *,
        worker_id: str,
    ) -> IngestionJob | None:
        """Claim one available job using row locking and SKIP LOCKED."""

        now = datetime.now(timezone.utc)
        statement = (
            select(IngestionJob)
            .where(
                IngestionJob.status == "pending",
                IngestionJob.available_at <= now,
            )
            .order_by(IngestionJob.available_at, IngestionJob.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        job = await session.scalar(statement)
        if job is None:
            return None

        job.status = "processing"
        job.attempts += 1
        job.locked_at = now
        job.locked_by = worker_id
        job.updated_at = now
        await session.flush()
        return job

    @staticmethod
    async def mark_succeeded(
        session: AsyncSession,
        job: IngestionJob,
    ) -> None:
        now = datetime.now(timezone.utc)
        job.status = "succeeded"
        job.locked_at = None
        job.locked_by = None
        job.last_error = None
        job.updated_at = now
        job.completed_at = now
        await session.flush()

    @staticmethod
    async def mark_failed_or_retry(
        session: AsyncSession,
        job: IngestionJob,
        *,
        safe_error: str,
    ) -> None:
        """Retry with bounded backoff or terminally fail the job."""

        now = datetime.now(timezone.utc)
        job.last_error = safe_error[:2000]
        job.locked_at = None
        job.locked_by = None
        job.updated_at = now
        if job.attempts >= job.max_attempts:
            job.status = "failed"
            job.completed_at = now
        else:
            delay_seconds = min(300, 2 ** max(1, job.attempts))
            job.status = "pending"
            job.available_at = now + timedelta(seconds=delay_seconds)
            job.completed_at = None
        await session.flush()

    @staticmethod
    async def recover_stale(
        session: AsyncSession,
        *,
        lock_timeout_seconds: int,
    ) -> int:
        """Return abandoned processing jobs to the queue or fail them."""

        if lock_timeout_seconds <= 0:
            raise ValueError("lock_timeout_seconds must be positive.")
        cutoff = datetime.now(timezone.utc) - timedelta(
            seconds=lock_timeout_seconds
        )
        jobs = list(
            (
                await session.scalars(
                    select(IngestionJob)
                    .where(
                        IngestionJob.status == "processing",
                        IngestionJob.locked_at < cutoff,
                    )
                    .with_for_update(skip_locked=True)
                )
            ).all()
        )
        for job in jobs:
            await IngestionJobService.mark_failed_or_retry(
                session,
                job,
                safe_error="The ingestion worker stopped before completion.",
            )
        return len(jobs)
