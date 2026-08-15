"""Add short-lived Widget Connector pairings.

Revision ID: 7f2a4c8e9d31
Revises: 270178081dd1
"""

from alembic import op
import sqlalchemy as sa


revision: str = "7f2a4c8e9d31"
down_revision: str | None = "270178081dd1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "widget_connector_pairings",
        sa.Column(
            "id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column(
            "agent_id",
            sa.String(length=128),
            nullable=False,
        ),
        sa.Column(
            "origin",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "connector_type",
            sa.String(length=32),
            nullable=False,
        ),
        sa.Column(
            "code_digest",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "used_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "connected_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "created_by_admin_id",
            sa.String(length=128),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "connector_type IN "
            "('wordpress', 'react_next', 'managed')",
            name=(
                "ck_widget_connector_pairings_"
                "connector_type"
            ),
        ),
        sa.CheckConstraint(
            "connected_at IS NULL OR used_at IS NOT NULL",
            name=(
                "ck_widget_connector_pairings_"
                "connected_requires_used"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["created_by_admin_id"],
            ["admin_users.id"],
            ondelete="SET NULL",
            name=(
                "fk_widget_connector_pairings_"
                "created_by_admin"
            ),
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "agent_id"],
            [
                "agent_widget_settings.tenant_id",
                "agent_widget_settings.agent_id",
            ],
            ondelete="CASCADE",
            name="fk_widget_connector_pairings_widget",
        ),
        sa.PrimaryKeyConstraint(
            "id",
            name="pk_widget_connector_pairings",
        ),
        sa.UniqueConstraint(
            "code_digest",
            name=(
                "uq_widget_connector_pairings_"
                "code_digest"
            ),
        ),
    )

    op.create_index(
        "ix_widget_connector_pairings_tenant_agent",
        "widget_connector_pairings",
        ["tenant_id", "agent_id"],
        unique=False,
    )

    op.create_index(
        "ix_widget_connector_pairings_expires_at",
        "widget_connector_pairings",
        ["expires_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_widget_connector_pairings_expires_at",
        table_name="widget_connector_pairings",
    )
    op.drop_index(
        "ix_widget_connector_pairings_tenant_agent",
        table_name="widget_connector_pairings",
    )
    op.drop_table(
        "widget_connector_pairings"
    )
