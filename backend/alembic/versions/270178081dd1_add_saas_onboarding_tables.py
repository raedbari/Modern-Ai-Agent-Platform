"""add saas onboarding tables

Revision ID: 270178081dd1
Revises: b81c1084d9ba
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "270178081dd1"
down_revision: Union[str, Sequence[str], None] = "b81c1084d9ba"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


APPLICATION_STATUSES = (
    "email_pending",
    "under_review",
    "changes_requested",
    "approved",
    "rejected",
)

MEMBERSHIP_ROLES = (
    "tenant_owner",
    "tenant_admin",
    "knowledge_editor",
    "conversation_viewer",
    "billing_manager",
)

MEMBERSHIP_STATUSES = (
    "active",
    "suspended",
    "revoked",
)


def upgrade() -> None:
    op.create_table(
        "tenant_applications",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("requested_plan", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'email_pending'"),
        ),
        sa.Column(
            "submitted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "reviewed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "reviewed_by",
            sa.String(length=128),
            nullable=True,
        ),
        sa.Column(
            "review_note",
            sa.String(length=2000),
            nullable=True,
        ),
        sa.Column(
            "approved_tenant_id",
            sa.String(length=128),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "status IN ('email_pending','under_review','changes_requested','approved','rejected')",
            name="ck_tenant_applications_status",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(
            ["reviewed_by"],
            ["admin_users.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["approved_tenant_id"],
            ["tenants.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "approved_tenant_id",
            name="uq_tenant_applications_approved_tenant_id",
        ),
    )

    op.create_index(
        "ix_tenant_applications_user_id",
        "tenant_applications",
        ["user_id"],
    )

    op.create_index(
        "ix_tenant_applications_status",
        "tenant_applications",
        ["status"],
    )

    op.create_index(
        "uq_tenant_applications_active_user",
        "tenant_applications",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text(
            "status IN ('email_pending','under_review','changes_requested')"
        ),
    )

    op.create_table(
        "legal_acceptances",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column(
            "application_id",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column(
            "document_type",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "document_version",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "accepted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "client_ip",
            sa.String(length=45),
            nullable=True,
        ),
        sa.Column(
            "user_agent",
            sa.String(length=512),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["application_id"],
            ["tenant_applications.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "application_id",
            "document_type",
            "document_version",
            name="uq_legal_acceptance_document_version",
        ),
    )

    op.create_table(
        "tenant_memberships",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("user_id", sa.String(length=128), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "role IN ('tenant_owner','tenant_admin','knowledge_editor','conversation_viewer','billing_manager')",
            name="ck_tenant_memberships_role",
        ),
        sa.CheckConstraint(
            "status IN ('active','suspended','revoked')",
            name="ck_tenant_memberships_status",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "tenant_id",
            name="uq_tenant_memberships_user_tenant",
        ),
    )

    op.create_index(
        "ix_tenant_memberships_tenant_status",
        "tenant_memberships",
        ["tenant_id", "status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_tenant_memberships_tenant_status",
        table_name="tenant_memberships",
    )
    op.drop_table("tenant_memberships")

    op.drop_table("legal_acceptances")

    op.drop_index(
        "uq_tenant_applications_active_user",
        table_name="tenant_applications",
    )
    op.drop_index(
        "ix_tenant_applications_status",
        table_name="tenant_applications",
    )
    op.drop_index(
        "ix_tenant_applications_user_id",
        table_name="tenant_applications",
    )
    op.drop_table("tenant_applications")
