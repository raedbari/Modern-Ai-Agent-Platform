"""replace handoffs with a per-chatbot contact message

Revision ID: f4a2b7c9d011
Revises: e81fba63c202
Create Date: 2026-07-30 22:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f4a2b7c9d011"
down_revision: Union[str, Sequence[str], None] = "e81fba63c202"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove human workflow state and preserve fallback text as contact text."""

    op.drop_table("handoffs")
    op.drop_constraint(
        "uq_messages_tenant_id_id",
        "messages",
        type_="unique",
    )
    op.drop_column("agents", "handoff_enabled")
    op.alter_column(
        "agents",
        "fallback_message",
        new_column_name="contact_message",
        existing_type=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    """Restore the previous durable handoff schema."""

    op.alter_column(
        "agents",
        "contact_message",
        new_column_name="fallback_message",
        existing_type=sa.Text(),
        existing_nullable=True,
    )
    op.add_column(
        "agents",
        sa.Column(
            "handoff_enabled",
            sa.Boolean(),
            server_default="true",
            nullable=False,
        ),
    )
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
