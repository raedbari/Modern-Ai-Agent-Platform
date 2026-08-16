"""Tenant-scoped customer repositories.

Every lookup includes the authoritative tenant_id.
Cross-tenant resource identifiers therefore resolve as absent.
"""

from __future__ import annotations

from uuid import uuid4

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.auth.origin import normalize_origin
from backend.app.db.models import (
    Agent,
    AgentWidgetSettings,
    Conversation,
    DocumentModel,
    IngestionJob,
    KnowledgeBaseModel,
    WidgetAllowedOrigin,
)


class TenantScopedAgentRepository:

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_tenant(
        self,
        tenant_id: str,
    ) -> list[Agent]:
        return list(
            (
                await self.session.scalars(
                    select(Agent)
                    .where(
                        Agent.tenant_id == tenant_id,
                    )
                    .order_by(
                        Agent.name,
                        Agent.id,
                    )
                )
            ).all()
        )

    async def get_by_id(
        self,
        agent_id: str,
        tenant_id: str,
    ) -> Agent | None:
        return await self.session.scalar(
            select(Agent).where(
                Agent.id == agent_id,
                Agent.tenant_id == tenant_id,
            )
        )

    async def create(
        self,
        *,
        tenant_id: str,
        name: str,
        system_prompt: str | None = None,
        knowledge_mode: str = "preferred",
        contact_message: str | None = None,
        agent_id: str | None = None,
    ) -> Agent:
        agent = Agent(
            id=agent_id or str(uuid4()),
            tenant_id=tenant_id,
            name=name,
            system_prompt=system_prompt,
            knowledge_mode=knowledge_mode,
            contact_message=contact_message,
            is_active=True,
        )

        self.session.add(agent)
        await self.session.flush()
        return agent

    async def update(
        self,
        agent_id: str,
        tenant_id: str,
        updates: dict,
    ) -> Agent | None:
        agent = await self.get_by_id(
            agent_id,
            tenant_id,
        )

        if agent is None:
            return None

        allowed = {
            "name",
            "system_prompt",
            "knowledge_mode",
            "contact_message",
            "is_active",
        }

        for key, value in updates.items():
            if key in allowed:
                setattr(agent, key, value)

        await self.session.flush()
        return agent

    async def delete(
        self,
        agent_id: str,
        tenant_id: str,
    ) -> bool:
        agent = await self.get_by_id(
            agent_id,
            tenant_id,
        )

        if agent is None:
            return False

        await self.session.delete(agent)
        await self.session.flush()
        return True


class TenantScopedWidgetRepository:

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _agent(
        self,
        agent_id: str,
        tenant_id: str,
    ) -> Agent | None:
        return await self.session.scalar(
            select(Agent).where(
                Agent.id == agent_id,
                Agent.tenant_id == tenant_id,
            )
        )

    async def _origins(
        self,
        agent_id: str,
        tenant_id: str,
    ) -> list[str]:
        return list(
            (
                await self.session.scalars(
                    select(
                        WidgetAllowedOrigin.origin
                    )
                    .where(
                        WidgetAllowedOrigin.tenant_id
                        == tenant_id,
                        WidgetAllowedOrigin.agent_id
                        == agent_id,
                    )
                    .order_by(
                        WidgetAllowedOrigin.origin
                    )
                )
            ).all()
        )

    async def get_by_agent(
        self,
        agent_id: str,
        tenant_id: str,
    ):
        settings = await self.session.scalar(
            select(AgentWidgetSettings).where(
                AgentWidgetSettings.agent_id
                == agent_id,
                AgentWidgetSettings.tenant_id
                == tenant_id,
            )
        )

        if settings is None:
            return None

        return (
            settings,
            await self._origins(
                agent_id,
                tenant_id,
            ),
        )

    async def update(
        self,
        agent_id: str,
        tenant_id: str,
        updates: dict,
        *,
        allowed_origins: list[str] | None = None,
    ):
        agent = await self._agent(
            agent_id,
            tenant_id,
        )

        if agent is None:
            return None

        settings = await self.session.scalar(
            select(AgentWidgetSettings).where(
                AgentWidgetSettings.agent_id
                == agent_id,
                AgentWidgetSettings.tenant_id
                == tenant_id,
            )
        )

        if settings is None:
            settings = AgentWidgetSettings(
                tenant_id=tenant_id,
                agent_id=agent_id,
                public_widget_id=(
                    "wgt_" + uuid4().hex
                ),
            )
            self.session.add(settings)
            await self.session.flush()

        allowed_fields = {
            "is_enabled",
            "display_name",
            "greeting",
            "primary_color",
            "text_color",
            "launcher_color",
            "header_color",
            "user_message_color",
            "position",
            "appearance",
        }

        for key, value in updates.items():
            if key in allowed_fields:
                setattr(
                    settings,
                    key,
                    value,
                )

        if allowed_origins is not None:
            normalized: list[str] = []

            for raw in allowed_origins:
                value = normalize_origin(raw)

                if value is None:
                    raise ValueError(
                        "Invalid allowed origin."
                    )

                if value not in normalized:
                    normalized.append(value)

            await self.session.execute(
                delete(WidgetAllowedOrigin).where(
                    WidgetAllowedOrigin.tenant_id
                    == tenant_id,
                    WidgetAllowedOrigin.agent_id
                    == agent_id,
                )
            )

            for origin in normalized:
                self.session.add(
                    WidgetAllowedOrigin(
                        tenant_id=tenant_id,
                        agent_id=agent_id,
                        origin=origin,
                    )
                )

        await self.session.flush()

        return (
            settings,
            await self._origins(
                agent_id,
                tenant_id,
            ),
        )


class TenantScopedConversationRepository:

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_agent(
        self,
        agent_id: str,
        tenant_id: str,
    ) -> list[Conversation]:
        return list(
            (
                await self.session.scalars(
                    select(Conversation)
                    .where(
                        Conversation.tenant_id
                        == tenant_id,
                        Conversation.agent_id
                        == agent_id,
                    )
                    .order_by(
                        Conversation.created_at,
                        Conversation.id,
                    )
                )
            ).all()
        )

    async def get_by_id(
        self,
        conversation_id: str,
        tenant_id: str,
    ) -> Conversation | None:
        return await self.session.scalar(
            select(Conversation).where(
                Conversation.id
                == conversation_id,
                Conversation.tenant_id
                == tenant_id,
            )
        )

    async def delete(
        self,
        conversation_id: str,
        tenant_id: str,
    ) -> bool:
        item = await self.get_by_id(
            conversation_id,
            tenant_id,
        )

        if item is None:
            return False

        await self.session.delete(item)
        await self.session.flush()
        return True


class TenantScopedDocumentRepository:

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _owned_kb(
        self,
        kb_id: str,
        tenant_id: str,
    ) -> KnowledgeBaseModel | None:
        return await self.session.scalar(
            select(KnowledgeBaseModel).where(
                KnowledgeBaseModel.id == kb_id,
                KnowledgeBaseModel.tenant_id
                == tenant_id,
            )
        )

    async def list_by_knowledge_base(
        self,
        kb_id: str,
        tenant_id: str,
    ) -> list[DocumentModel]:
        if await self._owned_kb(
            kb_id,
            tenant_id,
        ) is None:
            return []

        return list(
            (
                await self.session.scalars(
                    select(DocumentModel)
                    .where(
                        DocumentModel.tenant_id
                        == tenant_id,
                        DocumentModel.knowledge_base_id
                        == kb_id,
                    )
                    .order_by(
                        DocumentModel.created_at,
                        DocumentModel.id,
                    )
                )
            ).all()
        )

    async def get_by_id(
        self,
        doc_id: str,
        kb_id: str,
        tenant_id: str,
    ) -> DocumentModel | None:
        return await self.session.scalar(
            select(DocumentModel).where(
                DocumentModel.id == doc_id,
                DocumentModel.tenant_id
                == tenant_id,
                DocumentModel.knowledge_base_id
                == kb_id,
            )
        )

    async def create(
        self,
        *,
        doc_id: str,
        kb_id: str,
        tenant_id: str,
        source_name: str,
        original_filename: str,
        mime_type: str,
        file_size_bytes: int,
        content_hash: str,
        agent_id: str | None = None,
    ) -> DocumentModel | None:
        if await self._owned_kb(
            kb_id,
            tenant_id,
        ) is None:
            return None

        document = DocumentModel(
            id=doc_id,
            tenant_id=tenant_id,
            knowledge_base_id=kb_id,
            agent_id=agent_id,
            source_name=source_name,
            original_filename=original_filename,
            mime_type=mime_type,
            file_size_bytes=file_size_bytes,
            content_hash=content_hash,
            status="pending",
        )

        self.session.add(document)
        await self.session.flush()
        return document

    async def delete(
        self,
        doc_id: str,
        kb_id: str,
        tenant_id: str,
    ) -> bool:
        document = await self.get_by_id(
            doc_id,
            kb_id,
            tenant_id,
        )

        if document is None:
            return False

        await self.session.delete(document)
        await self.session.flush()
        return True

    async def create_ingestion_job(
        self,
        *,
        job_id: str,
        doc_id: str,
        kb_id: str,
        tenant_id: str,
        agent_id: str,
        storage_key: str,
        source_filename: str | None = None,
        source_mime_type: str | None = None,
        source_name: str | None = None,
    ) -> IngestionJob | None:
        document = await self.get_by_id(
            doc_id,
            kb_id,
            tenant_id,
        )

        if document is None:
            return None

        agent = await self.session.scalar(
            select(Agent).where(
                Agent.id == agent_id,
                Agent.tenant_id
                == tenant_id,
            )
        )

        if agent is None:
            return None

        job = IngestionJob(
            id=job_id,
            tenant_id=tenant_id,
            agent_id=agent_id,
            knowledge_base_id=kb_id,
            document_id=doc_id,
            storage_key=storage_key,
            source_filename=source_filename,
            source_mime_type=source_mime_type,
            source_name=source_name,
        )

        self.session.add(job)
        await self.session.flush()
        return job

    async def get_ingestion_job(
        self,
        job_id: str,
        kb_id: str,
        tenant_id: str,
    ) -> IngestionJob | None:
        return await self.session.scalar(
            select(IngestionJob).where(
                IngestionJob.id == job_id,
                IngestionJob.tenant_id
                == tenant_id,
                IngestionJob.knowledge_base_id
                == kb_id,
            )
        )
