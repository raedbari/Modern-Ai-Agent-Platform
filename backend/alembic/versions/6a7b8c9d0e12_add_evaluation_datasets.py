"""add durable uploaded evaluation datasets

Revision ID: 6a7b8c9d0e12
Revises: 4e6f7a8b9c01
"""

from alembic import op
import sqlalchemy as sa


revision = "6a7b8c9d0e12"
down_revision = "4e6f7a8b9c01"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "evaluation_datasets",
        sa.Column("name", sa.String(128), nullable=False),
        sa.Column("version", sa.String(64), nullable=False),
        sa.Column("owner", sa.String(128), nullable=False),
        sa.Column("domain", sa.String(128), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("classification", sa.String(128), nullable=False),
        sa.Column("records_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_by_admin_id",
            sa.String(128),
            sa.ForeignKey("admin_users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "status IN ('draft', 'active', 'retired')",
            name="ck_evaluation_datasets_status",
        ),
        sa.PrimaryKeyConstraint(
            "name",
            "version",
            name="pk_evaluation_datasets",
        ),
    )
    op.create_index(
        "ix_evaluation_datasets_created_at",
        "evaluation_datasets",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_evaluation_datasets_created_at",
        table_name="evaluation_datasets",
    )
    op.drop_table("evaluation_datasets")
