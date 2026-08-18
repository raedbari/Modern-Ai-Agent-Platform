"""Database models for the multi-tenant AI Agent Platform."""

from __future__ import annotations

import sqlalchemy as athka_sa

from datetime import datetime
from typing import Any

from sqlalchemy import (
    text,
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    PrimaryKeyConstraint,
    String,
    Text,
    UniqueConstraint,
    event,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import VECTOR

from backend.app.db.base import Base

EMBEDDING_DIMENSION = 1024


# ---------------------------------------------------------------------------
# Admin identity models
# ---------------------------------------------------------------------------


class AdminUser(Base):
    """A human operator account with access to the administrative API."""

    __tablename__ = "admin_users"
    __table_args__ = (
        UniqueConstraint("username", name="uq_admin_users_username"),
        CheckConstraint(
            "role IN ('super_admin', 'operator', 'auditor')",
            name="ck_admin_users_role",
        ),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    username: Mapped[str] = mapped_column(String(64), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(512), nullable=False)
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="operator",
        server_default="operator",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    # NULL when created by the CLI bootstrap tool.
    created_by: Mapped[str | None] = mapped_column(
        String(128),
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
    )

    refresh_sessions: Mapped[list[AdminRefreshSession]] = relationship(
        back_populates="admin",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class AdminRefreshSession(Base):
    """One active refresh-token session for an admin user."""

    __tablename__ = "admin_refresh_sessions"
    __table_args__ = (
        Index(
            "ix_admin_refresh_sessions_admin_id",
            "admin_id",
        ),
        Index(
            "ix_admin_refresh_sessions_family_id",
            "family_id",
        ),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    admin_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("admin_users.id", ondelete="CASCADE"),
        nullable=False,
    )
    # SHA-256 hex digest of the raw opaque token value.
    token_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
    )
    # UUID shared by every token produced from the same login event.
    # Used to revoke an entire token lineage on replay detection.
    family_id: Mapped[str] = mapped_column(String(128), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    # IPv4 (max 15 chars) or IPv6 (max 45 chars).
    client_ip: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(512))

    admin: Mapped[AdminUser] = relationship(back_populates="refresh_sessions")


class AdminAuditLog(Base):
    """Immutable audit record for every state-changing administrative action."""

    __tablename__ = "admin_audit_log"
    __table_args__ = (
        CheckConstraint(
            "outcome IN ('success', 'failure')",
            name="ck_admin_audit_log_outcome",
        ),
        Index(
            "ix_admin_audit_log_admin_id",
            "admin_id",
        ),
        Index(
            "ix_admin_audit_log_event_type",
            "event_type",
        ),
        Index(
            "ix_admin_audit_log_created_at",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    # NULL for unauthenticated events such as login_failure before identity
    # is known.
    admin_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    outcome: Mapped[str] = mapped_column(String(20), nullable=False)
    client_ip: Mapped[str | None] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    detail: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)


class EvaluationRunRecord(Base):
    """Durable administrative record of one evaluation execution."""

    __tablename__ = "evaluation_runs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('running', 'completed', 'failed')",
            name="ck_evaluation_runs_status",
        ),
        Index("ix_evaluation_runs_started_at", "started_at"),
        Index("ix_evaluation_runs_tenant_agent", "tenant_id", "agent_id"),
    )

    run_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    created_by_admin_id: Mapped[str | None] = mapped_column(
        String(128),
        ForeignKey("admin_users.id", ondelete="SET NULL"),
        nullable=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    agent_id: Mapped[str] = mapped_column(String(128), nullable=False)
    configuration_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    results_json: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    summary_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
    )
    failure_reason: Mapped[str | None] = mapped_column(Text)


class User(Base):
    """A customer human identity account."""

    __tablename__ = "users"
    __table_args__ = (
        UniqueConstraint(
            "normalized_email",
            name="uq_users_normalized_email",
        ),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    normalized_email: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
    )
    hashed_password: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    display_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    email_verified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    refresh_sessions: Mapped[list["UserRefreshSession"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    email_verification_tokens: Mapped[
        list["EmailVerificationToken"]
    ] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class UserRefreshSession(Base):
    """Database-backed refresh-token session for a customer user."""

    __tablename__ = "user_refresh_sessions"
    __table_args__ = (
        UniqueConstraint(
            "token_hash",
            name="uq_user_refresh_sessions_token_hash",
        ),
        Index(
            "ix_user_refresh_sessions_user_id",
            "user_id",
        ),
        Index(
            "ix_user_refresh_sessions_family_id",
            "family_id",
        ),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    family_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
    client_ip: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(512))

    user: Mapped["User"] = relationship(
        back_populates="refresh_sessions",
    )


class EmailVerificationToken(Base):
    """One-time token used to verify a customer email address."""

    __tablename__ = "email_verification_tokens"
    __table_args__ = (
        UniqueConstraint(
            "token_hash",
            name="uq_email_verification_tokens_token_hash",
        ),
        Index(
            "ix_email_verification_tokens_user_id",
            "user_id",
        ),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    token_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped["User"] = relationship(
        back_populates="email_verification_tokens",
    )



class TenantApplication(Base):
    """Customer application awaiting Athka approval."""

    __tablename__ = "tenant_applications"
    __table_args__ = (
        athka_sa.CheckConstraint(
            "status IN ('email_pending','under_review','changes_requested','approved','rejected')",
            name="ck_tenant_applications_status",
        ),
        athka_sa.UniqueConstraint(
            "approved_tenant_id",
            name="uq_tenant_applications_approved_tenant_id",
        ),
        athka_sa.Index(
            "ix_tenant_applications_user_id",
            "user_id",
        ),
        athka_sa.Index(
            "ix_tenant_applications_status",
            "status",
        ),
        athka_sa.Index(
            "uq_tenant_applications_active_user",
            "user_id",
            unique=True,
            postgresql_where=athka_sa.text(
                "status IN ('email_pending','under_review','changes_requested')"
            ),
        ),
    )

    id: Mapped[str] = mapped_column(
        athka_sa.String(128),
        primary_key=True,
    )
    user_id: Mapped[str] = mapped_column(
        athka_sa.String(128),
        athka_sa.ForeignKey("users.id"),
        nullable=False,
    )
    company_name: Mapped[str] = mapped_column(
        athka_sa.String(255),
        nullable=False,
    )
    requested_plan: Mapped[str] = mapped_column(
        athka_sa.String(64),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        athka_sa.String(32),
        nullable=False,
        default="email_pending",
        server_default=athka_sa.text("'email_pending'"),
    )
    submitted_at: Mapped[datetime | None] = mapped_column(
        athka_sa.DateTime(timezone=True),
    )
    reviewed_at: Mapped[datetime | None] = mapped_column(
        athka_sa.DateTime(timezone=True),
    )
    reviewed_by: Mapped[str | None] = mapped_column(
        athka_sa.String(128),
        athka_sa.ForeignKey(
            "admin_users.id",
            ondelete="SET NULL",
        ),
    )
    review_note: Mapped[str | None] = mapped_column(
        athka_sa.String(2000),
    )
    approved_tenant_id: Mapped[str | None] = mapped_column(
        athka_sa.String(128),
        athka_sa.ForeignKey(
            "tenants.id",
            ondelete="SET NULL",
        ),
    )
    created_at: Mapped[datetime] = mapped_column(
        athka_sa.DateTime(timezone=True),
        nullable=False,
        server_default=athka_sa.func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        athka_sa.DateTime(timezone=True),
        nullable=False,
        server_default=athka_sa.func.now(),
        onupdate=athka_sa.func.now(),
    )


class LegalAcceptance(Base):
    """Versioned legal acceptance attached to a tenant application."""

    __tablename__ = "legal_acceptances"
    __table_args__ = (
        athka_sa.UniqueConstraint(
            "application_id",
            "document_type",
            "document_version",
            name="uq_legal_acceptance_document_version",
        ),
    )

    id: Mapped[str] = mapped_column(
        athka_sa.String(128),
        primary_key=True,
    )
    application_id: Mapped[str] = mapped_column(
        athka_sa.String(128),
        athka_sa.ForeignKey("tenant_applications.id"),
        nullable=False,
    )
    document_type: Mapped[str] = mapped_column(
        athka_sa.String(64),
        nullable=False,
    )
    document_version: Mapped[str] = mapped_column(
        athka_sa.String(64),
        nullable=False,
    )
    accepted_at: Mapped[datetime] = mapped_column(
        athka_sa.DateTime(timezone=True),
        nullable=False,
        server_default=athka_sa.func.now(),
    )
    client_ip: Mapped[str | None] = mapped_column(
        athka_sa.String(45),
    )
    user_agent: Mapped[str | None] = mapped_column(
        athka_sa.String(512),
    )


class TenantMembership(Base):
    """Links a customer user to a tenant with a current role."""

    __tablename__ = "tenant_memberships"
    __table_args__ = (
        athka_sa.CheckConstraint(
            "role IN ('tenant_owner','tenant_admin','knowledge_editor','conversation_viewer','billing_manager')",
            name="ck_tenant_memberships_role",
        ),
        athka_sa.CheckConstraint(
            "status IN ('active','suspended','revoked')",
            name="ck_tenant_memberships_status",
        ),
        athka_sa.UniqueConstraint(
            "user_id",
            "tenant_id",
            name="uq_tenant_memberships_user_tenant",
        ),
        athka_sa.Index(
            "ix_tenant_memberships_tenant_status",
            "tenant_id",
            "status",
        ),
    )

    id: Mapped[str] = mapped_column(
        athka_sa.String(128),
        primary_key=True,
    )
    user_id: Mapped[str] = mapped_column(
        athka_sa.String(128),
        athka_sa.ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    tenant_id: Mapped[str] = mapped_column(
        athka_sa.String(128),
        athka_sa.ForeignKey(
            "tenants.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        athka_sa.String(32),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        athka_sa.String(32),
        nullable=False,
        default="active",
        server_default=athka_sa.text("'active'"),
    )
    created_at: Mapped[datetime] = mapped_column(
        athka_sa.DateTime(timezone=True),
        nullable=False,
        server_default=athka_sa.func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        athka_sa.DateTime(timezone=True),
        nullable=False,
        server_default=athka_sa.func.now(),
        onupdate=athka_sa.func.now(),
    )


class Tenant(Base):
    """A tenant using the platform."""

    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    api_keys: Mapped[list[ApiKey]] = relationship(
        back_populates="tenant",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    agents: Mapped[list[Agent]] = relationship(
        back_populates="tenant",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class ApiKey(Base):
    """API key metadata without storing the raw secret."""

    __tablename__ = "api_keys"
    __table_args__ = (
        Index(
            "ix_api_keys_tenant_active",
            "tenant_id",
            "is_active",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    tenant_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    key_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
    )
    key_digest: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    name: Mapped[str | None] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    revoked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )

    tenant: Mapped[Tenant] = relationship(back_populates="api_keys")


class Agent(Base):
    """An AI agent belonging to one tenant."""

    __tablename__ = "agents"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "id",
            name="uq_agents_tenant_id_id",
        ),
        CheckConstraint(
            "knowledge_mode IN ('required', 'preferred', 'disabled')",
            name="ck_agents_knowledge_mode",
        ),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    system_prompt: Mapped[str | None] = mapped_column(Text)
    prompt_version: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default="v1",
        server_default="v1",
    )
    knowledge_mode: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="preferred",
        server_default="preferred",
    )
    contact_message: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="true",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    tenant: Mapped[Tenant] = relationship(back_populates="agents")
    conversations: Mapped[list[Conversation]] = relationship(
        back_populates="agent",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class AgentWidgetSettings(Base):
    """Public, browser-safe Widget configuration for one tenant agent."""

    __tablename__ = "agent_widget_settings"
    __table_args__ = (
        PrimaryKeyConstraint(
            "tenant_id",
            "agent_id",
            name="pk_agent_widget_settings",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "agent_id"],
            ["agents.tenant_id", "agents.id"],
            ondelete="CASCADE",
            name="fk_agent_widget_settings_tenant_agent",
        ),
        UniqueConstraint(
            "public_widget_id",
            name="uq_agent_widget_settings_public_widget_id",
        ),
        CheckConstraint(
            "position IN ('left', 'right')",
            name="ck_agent_widget_settings_position",
        ),
        CheckConstraint(
            "appearance IN ('light', 'dark')",
            name="ck_agent_widget_settings_appearance",
        ),
    )

    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    agent_id: Mapped[str] = mapped_column(String(128), nullable=False)
    public_widget_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    display_name: Mapped[str | None] = mapped_column(String(255))
    greeting: Mapped[str | None] = mapped_column(String(500))
    primary_color: Mapped[str] = mapped_column(
        String(7),
        nullable=False,
        default="#2563EB",
        server_default="#2563EB",
    )
    text_color: Mapped[str] = mapped_column(
        String(7),
        nullable=False,
        default="#FFFFFF",
        server_default="#FFFFFF",
    )
    launcher_color: Mapped[str] = mapped_column(
        String(7),
        nullable=False,
        default="#2563EB",
        server_default="#2563EB",
    )
    header_color: Mapped[str] = mapped_column(
        String(7),
        nullable=False,
        default="#2563EB",
        server_default="#2563EB",
    )
    user_message_color: Mapped[str] = mapped_column(
        String(7),
        nullable=False,
        default="#2563EB",
        server_default="#2563EB",
    )
    position: Mapped[str] = mapped_column(
        String(5),
        nullable=False,
        default="right",
        server_default="right",
    )
    appearance: Mapped[str] = mapped_column(
        String(5),
        nullable=False,
        default="light",
        server_default="light",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class WidgetAllowedOrigin(Base):
    """One exact normalized browser origin allowed for a Widget."""

    __tablename__ = "widget_allowed_origins"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "agent_id"],
            [
                "agent_widget_settings.tenant_id",
                "agent_widget_settings.agent_id",
            ],
            ondelete="CASCADE",
            name="fk_widget_allowed_origins_widget",
        ),
        UniqueConstraint(
            "tenant_id",
            "agent_id",
            "origin",
            name="uq_widget_allowed_origins_tenant_agent_origin",
        ),
        Index(
            "ix_widget_allowed_origins_tenant_agent",
            "tenant_id",
            "agent_id",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False)
    agent_id: Mapped[str] = mapped_column(String(128), nullable=False)
    origin: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class WidgetConnectorPairing(Base):
    """One short-lived, single-use website Connector pairing."""

    __tablename__ = "widget_connector_pairings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "agent_id"],
            [
                "agent_widget_settings.tenant_id",
                "agent_widget_settings.agent_id",
            ],
            ondelete="CASCADE",
            name="fk_widget_connector_pairings_widget",
        ),
        CheckConstraint(
            "connector_type IN ('wordpress', 'react_next', 'managed', 'custom')",
            name="ck_widget_connector_pairings_connector_type",
        ),
        CheckConstraint(
            "connected_at IS NULL OR used_at IS NOT NULL",
            name="ck_widget_connector_pairings_connected_requires_used",
        ),
        UniqueConstraint(
            "code_digest",
            name="uq_widget_connector_pairings_code_digest",
        ),
        Index(
            "ix_widget_connector_pairings_tenant_agent",
            "tenant_id",
            "agent_id",
        ),
        Index(
            "ix_widget_connector_pairings_expires_at",
            "expires_at",
        ),
    )

    id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
    )
    tenant_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    agent_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    origin: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    connector_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    code_digest: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
    connected_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
    )
    created_by_admin_id: Mapped[str | None] = mapped_column(
        String(128),
        ForeignKey(
            "admin_users.id",
            ondelete="SET NULL",
        ),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class Conversation(Base):
    """A conversation belonging to one tenant and agent."""

    __tablename__ = "conversations"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "agent_id"],
            ["agents.tenant_id", "agents.id"],
            ondelete="CASCADE",
            name="fk_conversations_tenant_agent",
        ),
        UniqueConstraint(
            "tenant_id",
            "id",
            name="uq_conversations_tenant_id_id",
        ),
        Index(
            "ix_conversations_tenant_agent",
            "tenant_id",
            "agent_id",
        ),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    user_identifier: Mapped[str | None] = mapped_column(String(255))
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSON,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    agent: Mapped[Agent] = relationship(back_populates="conversations")
    messages: Mapped[list[Message]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Message.created_at",
    )


class Message(Base):
    """A message belonging to a tenant's conversation."""

    __tablename__ = "messages"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "conversation_id"],
            ["conversations.tenant_id", "conversations.id"],
            ondelete="CASCADE",
            name="fk_messages_tenant_conversation",
        ),
        CheckConstraint(
            "role IN ('system', 'user', 'assistant', 'tool')",
            name="ck_messages_role",
        ),
        Index(
            "ix_messages_tenant_conversation",
            "tenant_id",
            "conversation_id",
        ),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    conversation_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata",
        JSON,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    conversation: Mapped[Conversation] = relationship(
        back_populates="messages"
    )


class KnowledgeBaseModel(Base):
    """A tenant-owned collection of documents used for retrieval."""

    __tablename__ = "knowledge_bases"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "id",
            name="uq_knowledge_bases_tenant_id_id",
        ),
        CheckConstraint(
            "status IN ('active', 'inactive')",
            name="ck_knowledge_bases_status",
        ),
        CheckConstraint(
            "classification IN ('public', 'internal', 'restricted')",
            name="ck_knowledge_bases_classification",
        ),
        Index(
            "ix_knowledge_bases_tenant_status",
            "tenant_id",
            "status",
        ),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default="",
        server_default="",
    )
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="active",
        server_default="active",
    )
    # Governance metadata — added in migration e1f2a3b4c5d6
    classification: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="internal",
        server_default="internal",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class AgentKnowledgeBase(Base):
    """Tenant-safe many-to-many assignment between agents and knowledge bases."""

    __tablename__ = "agent_knowledge_bases"
    __table_args__ = (
        PrimaryKeyConstraint(
            "tenant_id",
            "agent_id",
            "knowledge_base_id",
            name="pk_agent_knowledge_bases",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "agent_id"],
            ["agents.tenant_id", "agents.id"],
            ondelete="CASCADE",
            name="fk_agent_knowledge_bases_tenant_agent",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "knowledge_base_id"],
            ["knowledge_bases.tenant_id", "knowledge_bases.id"],
            ondelete="CASCADE",
            name="fk_agent_knowledge_bases_tenant_kb",
        ),
        Index(
            "ix_agent_knowledge_bases_tenant_kb",
            "tenant_id",
            "knowledge_base_id",
        ),
    )

    tenant_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_id: Mapped[str] = mapped_column(String(128), nullable=False)
    knowledge_base_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )


class DocumentModel(Base):
    """Persistent document lifecycle metadata."""

    __tablename__ = "documents"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "id",
            name="uq_documents_tenant_id_id",
        ),
        UniqueConstraint(
            "tenant_id",
            "knowledge_base_id",
            "id",
            name="uq_documents_tenant_kb_id",
        ),
        UniqueConstraint(
            "tenant_id",
            "knowledge_base_id",
            "content_hash",
            name="uq_documents_tenant_kb_content_hash",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "knowledge_base_id"],
            ["knowledge_bases.tenant_id", "knowledge_bases.id"],
            ondelete="CASCADE",
            name="fk_documents_tenant_kb",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "agent_id"],
            ["agents.tenant_id", "agents.id"],
            name="fk_documents_tenant_agent",
        ),
        CheckConstraint(
            "status IN ('pending', 'processing', 'ready', 'failed', 'active', 'superseded', 'archived')",
            name="ck_documents_status",
        ),
        CheckConstraint(
            "file_size_bytes >= 0",
            name="ck_documents_file_size",
        ),
        Index(
            "ix_documents_tenant_kb_status",
            "tenant_id",
            "knowledge_base_id",
            "status",
        ),
        # Governance: only one ACTIVE/READY document per (tenant, kb, filename).
        # Added in migration e1f2a3b4c5d6.
        Index(
            "uq_documents_active_per_tenant_kb_family",
            "tenant_id",
            "knowledge_base_id",
            "version_family_id",
            unique=True,
            postgresql_where=text("status IN ('ready', 'active')"),
            sqlite_where=text("status IN ('ready', 'active')"),
        ),
        Index(
            "ix_documents_tenant_kb_family_version",
            "tenant_id", "knowledge_base_id", "version_family_id", "version_number",
            unique=True,
        ),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    knowledge_base_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    agent_id: Mapped[str | None] = mapped_column(String(128))
    source_name: Mapped[str] = mapped_column(String(512), nullable=False)
    original_filename: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
    )
    failure_reason: Mapped[str | None] = mapped_column(Text)
    # Governance metadata — added in migration e1f2a3b4c5d6
    version_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
    )
    version_family_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    predecessor_id: Mapped[str | None] = mapped_column(
        String(128), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    superseded_by_id: Mapped[str | None] = mapped_column(
        String(128),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


@event.listens_for(DocumentModel, "before_insert")
def _default_document_version_family(_mapper, _connection, target: DocumentModel) -> None:
    if target.version_family_id is None:
        target.version_family_id = target.id


class IngestionJob(Base):
    """Durable PostgreSQL-backed document ingestion job."""

    __tablename__ = "ingestion_jobs"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "agent_id"],
            ["agents.tenant_id", "agents.id"],
            ondelete="CASCADE",
            name="fk_ingestion_jobs_tenant_agent",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "knowledge_base_id", "document_id"],
            [
                "documents.tenant_id",
                "documents.knowledge_base_id",
                "documents.id",
            ],
            ondelete="CASCADE",
            name="fk_ingestion_jobs_tenant_kb_document",
        ),
        CheckConstraint(
            "status IN ('pending', 'processing', 'succeeded', 'failed')",
            name="ck_ingestion_jobs_status",
        ),
        CheckConstraint(
            "attempts >= 0 AND max_attempts > 0",
            name="ck_ingestion_jobs_attempts",
        ),
        Index(
            "ix_ingestion_jobs_claim",
            "status",
            "available_at",
            "created_at",
        ),
        Index(
            "ix_ingestion_jobs_tenant_agent",
            "tenant_id",
            "agent_id",
            "created_at",
        ),
        Index(
            "uq_ingestion_jobs_active_document",
            "tenant_id",
            "document_id",
            unique=True,
            postgresql_where=text(
                "status IN ('pending', 'processing')"
            ),
            sqlite_where=text(
                "status IN ('pending', 'processing')"
            ),
        ),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_id: Mapped[str] = mapped_column(String(128), nullable=False)
    knowledge_base_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    document_id: Mapped[str] = mapped_column(String(128), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    source_filename: Mapped[str | None] = mapped_column(String(512))
    source_mime_type: Mapped[str | None] = mapped_column(String(255))
    source_name: Mapped[str | None] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="pending",
        server_default="pending",
    )
    attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )
    max_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=3,
        server_default="3",
    )
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    locked_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    locked_by: Mapped[str | None] = mapped_column(String(255))
    last_error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )


class ChunkModel(Base):
    """A tenant- and agent-scoped text chunk with a pgvector embedding."""

    __tablename__ = "chunks"
    __table_args__ = (
        ForeignKeyConstraint(
            ["tenant_id", "agent_id"],
            ["agents.tenant_id", "agents.id"],
            ondelete="CASCADE",
            name="fk_chunks_tenant_agent",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "knowledge_base_id"],
            ["knowledge_bases.tenant_id", "knowledge_bases.id"],
            ondelete="CASCADE",
            name="fk_chunks_tenant_kb",
        ),
        ForeignKeyConstraint(
            ["tenant_id", "knowledge_base_id", "document_id"],
            [
                "documents.tenant_id",
                "documents.knowledge_base_id",
                "documents.id",
            ],
            ondelete="CASCADE",
            name="fk_chunks_tenant_kb_document",
        ),
        UniqueConstraint(
            "tenant_id",
            "document_id",
            "chunk_index",
            name="uq_chunks_tenant_document_index",
        ),
        CheckConstraint(
            "page_number >= 0",
            name="ck_chunks_page_number",
        ),
        CheckConstraint(
            "chunk_index >= 0",
            name="ck_chunks_chunk_index",
        ),
        Index(
            "ix_chunks_tenant_agent_kb",
            "tenant_id",
            "agent_id",
            "knowledge_base_id",
        ),
        Index(
            "ix_chunks_tenant_document",
            "tenant_id",
            "document_id",
        ),
        Index(
            "ix_chunks_embedding_hnsw_cosine",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ).ddl_if(dialect="postgresql"),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(128),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    agent_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    knowledge_base_id: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    document_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_name: Mapped[str] = mapped_column(String(512), nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding: Mapped[list[float]] = mapped_column(
        VECTOR(EMBEDDING_DIMENSION).with_variant(JSON, "sqlite"),
        nullable=False,
    )
