"""add tenant-safe widget configuration

Revision ID: b7c8d9e0f1a2
Revises: a1b2c3d4e5f6
Create Date: 2026-08-02 08:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7c8d9e0f1a2"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "agent_widget_settings",
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("agent_id", sa.String(length=128), nullable=False),
        sa.Column("public_widget_id", sa.String(length=64), nullable=False),
        sa.Column(
            "is_enabled",
            sa.Boolean(),
            server_default="false",
            nullable=False,
        ),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("greeting", sa.String(length=500), nullable=True),
        sa.Column(
            "primary_color",
            sa.String(length=7),
            server_default="#2563EB",
            nullable=False,
        ),
        sa.Column(
            "text_color",
            sa.String(length=7),
            server_default="#FFFFFF",
            nullable=False,
        ),
        sa.Column(
            "launcher_color",
            sa.String(length=7),
            server_default="#2563EB",
            nullable=False,
        ),
        sa.Column(
            "header_color",
            sa.String(length=7),
            server_default="#2563EB",
            nullable=False,
        ),
        sa.Column(
            "user_message_color",
            sa.String(length=7),
            server_default="#2563EB",
            nullable=False,
        ),
        sa.Column(
            "position",
            sa.String(length=5),
            server_default="right",
            nullable=False,
        ),
        sa.Column(
            "appearance",
            sa.String(length=5),
            server_default="light",
            nullable=False,
        ),
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
            "position IN ('left', 'right')",
            name="ck_agent_widget_settings_position",
        ),
        sa.CheckConstraint(
            "appearance IN ('light', 'dark')",
            name="ck_agent_widget_settings_appearance",
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "agent_id"],
            ["agents.tenant_id", "agents.id"],
            ondelete="CASCADE",
            name="fk_agent_widget_settings_tenant_agent",
        ),
        sa.PrimaryKeyConstraint(
            "tenant_id",
            "agent_id",
            name="pk_agent_widget_settings",
        ),
        sa.UniqueConstraint(
            "public_widget_id",
            name="uq_agent_widget_settings_public_widget_id",
        ),
    )

    op.create_table(
        "widget_allowed_origins",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("tenant_id", sa.String(length=128), nullable=False),
        sa.Column("agent_id", sa.String(length=128), nullable=False),
        sa.Column("origin", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["tenant_id", "agent_id"],
            [
                "agent_widget_settings.tenant_id",
                "agent_widget_settings.agent_id",
            ],
            ondelete="CASCADE",
            name="fk_widget_allowed_origins_widget",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "agent_id",
            "origin",
            name="uq_widget_allowed_origins_tenant_agent_origin",
        ),
    )
    op.create_index(
        "ix_widget_allowed_origins_tenant_agent",
        "widget_allowed_origins",
        ["tenant_id", "agent_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_widget_allowed_origins_tenant_agent",
        table_name="widget_allowed_origins",
    )
    op.drop_table("widget_allowed_origins")
    op.drop_table("agent_widget_settings")
