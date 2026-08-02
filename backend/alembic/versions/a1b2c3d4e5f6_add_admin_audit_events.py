"""add admin audit events

Revision ID: a1b2c3d4e5f6
Revises: f4a2b7c9d011
Create Date: 2026-08-02 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "f4a2b7c9d011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create append-only audit log for administrative actions."""

    op.create_table(
        "admin_audit_events",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("actor_admin_id", sa.String(length=128), nullable=True),
        sa.Column(
            "actor_username",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column("actor_role", sa.String(length=50), nullable=False),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=True),
        sa.Column("resource_type", sa.String(length=100), nullable=False),
        sa.Column("resource_id", sa.String(length=128), nullable=True),
        sa.Column("changed_fields", sa.JSON(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "actor_role IN ('super_admin', 'auditor', 'operator')",
            name="ck_admin_audit_events_actor_role",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # Create indexes for efficient querying
    op.create_index(
        "ix_admin_audit_events_actor_admin_id",
        "admin_audit_events",
        ["actor_admin_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_audit_events_action",
        "admin_audit_events",
        ["action"],
        unique=False,
    )
    op.create_index(
        "ix_admin_audit_events_tenant_id",
        "admin_audit_events",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_audit_events_resource_type_id",
        "admin_audit_events",
        ["resource_type", "resource_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_audit_events_created_at",
        "admin_audit_events",
        ["created_at"],
        unique=False,
    )
    op.create_index(
        "ix_admin_audit_events_actor_action_created",
        "admin_audit_events",
        ["actor_admin_id", "action", "created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Remove admin audit events table."""

    op.drop_index(
        "ix_admin_audit_events_actor_action_created",
        table_name="admin_audit_events",
    )
    op.drop_index(
        "ix_admin_audit_events_created_at",
        table_name="admin_audit_events",
    )
    op.drop_index(
        "ix_admin_audit_events_resource_type_id",
        table_name="admin_audit_events",
    )
    op.drop_index(
        "ix_admin_audit_events_tenant_id",
        table_name="admin_audit_events",
    )
    op.drop_index(
        "ix_admin_audit_events_action",
        table_name="admin_audit_events",
    )
    op.drop_index(
        "ix_admin_audit_events_actor_admin_id",
        table_name="admin_audit_events",
    )
    op.drop_table("admin_audit_events")
