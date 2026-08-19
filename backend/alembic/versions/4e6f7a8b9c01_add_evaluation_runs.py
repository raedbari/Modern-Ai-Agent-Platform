"""add durable evaluation runs

Revision ID: 4e6f7a8b9c01
Revises: cd2d8fc0a3b1
"""

from alembic import op
import sqlalchemy as sa


revision = "4e6f7a8b9c01"
down_revision = "cd2d8fc0a3b1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "evaluation_runs",
        sa.Column("run_id", sa.String(128), primary_key=True),
        sa.Column(
            "created_by_admin_id",
            sa.String(128),
            sa.ForeignKey("admin_users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("tenant_id", sa.String(128), nullable=False),
        sa.Column("agent_id", sa.String(128), nullable=False),
        sa.Column("configuration_json", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("results_json", sa.JSON(), nullable=False),
        sa.Column("summary_json", sa.JSON(), nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "status IN ('running', 'completed', 'failed')",
            name="ck_evaluation_runs_status",
        ),
    )
    op.create_index(
        "ix_evaluation_runs_started_at",
        "evaluation_runs",
        ["started_at"],
    )
    op.create_index(
        "ix_evaluation_runs_tenant_agent",
        "evaluation_runs",
        ["tenant_id", "agent_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_evaluation_runs_tenant_agent",
        table_name="evaluation_runs",
    )
    op.drop_index(
        "ix_evaluation_runs_started_at",
        table_name="evaluation_runs",
    )
    op.drop_table("evaluation_runs")
