"""add agent RAG policy and message metadata

Revision ID: c4512c18f8a1
Revises: 8d2f4a7c91b6
Create Date: 2026-07-30 19:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4512c18f8a1"
down_revision: Union[str, Sequence[str], None] = "8d2f4a7c91b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add per-agent grounding policy and auditable message metadata."""

    op.add_column(
        "agents",
        sa.Column(
            "knowledge_mode",
            sa.String(length=20),
            server_default="preferred",
            nullable=False,
        ),
    )
    op.add_column(
        "agents",
        sa.Column("fallback_message", sa.Text(), nullable=True),
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
    op.create_check_constraint(
        "ck_agents_knowledge_mode",
        "agents",
        "knowledge_mode IN ('required', 'preferred', 'disabled')",
    )
    op.add_column(
        "messages",
        sa.Column("metadata", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    """Remove RAG policy fields and message metadata."""

    op.drop_column("messages", "metadata")
    op.drop_constraint(
        "ck_agents_knowledge_mode",
        "agents",
        type_="check",
    )
    op.drop_column("agents", "handoff_enabled")
    op.drop_column("agents", "fallback_message")
    op.drop_column("agents", "knowledge_mode")
