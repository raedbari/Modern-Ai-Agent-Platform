"""add tenant handoffs

Revision ID: d2e7c9a45130
Revises: c4512c18f8a1
Create Date: 2026-07-30 20:15:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d2e7c9a45130"
down_revision: Union[str, Sequence[str], None] = "c4512c18f8a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create durable, tenant-safe human handoff requests."""

    op.create_unique_constraint(
        "uq_messages_tenant_id_id",
        "messages",
        ["tenant_id", "id"],
    )
    op.create_table(
        "handoffs",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("agent_id", sa.String(length=128), nullable=False),
        sa.Column(
            "conversation_id",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column(
            "trigger_message_id",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column("reason", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="open",
            nullable=False,
        ),
        sa.Column("assigned_to", sa.String(length=255), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('open', 'assigned', 'closed')",
            name="ck_handoffs_status",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id"],
            ["tenants.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "agent_id"],
            ["agents.tenant_id", "agents.id"],
            name="fk_handoffs_tenant_agent",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "conversation_id"],
            ["conversations.tenant_id", "conversations.id"],
            name="fk_handoffs_tenant_conversation",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "trigger_message_id"],
            ["messages.tenant_id", "messages.id"],
            name="fk_handoffs_tenant_trigger_message",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_handoffs_tenant_agent_status",
        "handoffs",
        ["tenant_id", "agent_id", "status", "updated_at"],
        unique=False,
    )


def downgrade() -> None:
    """Remove tenant handoffs."""

    op.drop_index(
        "ix_handoffs_tenant_agent_status",
        table_name="handoffs",
    )
    op.drop_table("handoffs")
    op.drop_constraint(
        "uq_messages_tenant_id_id",
        "messages",
        type_="unique",
    )
