"""add admin auth tables

Revision ID: a1b2c3d4e5f6
Revises: f4a2b7c9d011
Create Date: 2026-08-01 18:00:00.000000

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
    """Create admin_users, admin_refresh_sessions, and admin_audit_log tables."""

    # ------------------------------------------------------------------ #
    # admin_users                                                          #
    # ------------------------------------------------------------------ #
    op.create_table(
        "admin_users",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("username", sa.String(length=64), nullable=False),
        sa.Column("hashed_password", sa.String(length=512), nullable=False),
        sa.Column(
            "role",
            sa.String(length=20),
            server_default="operator",
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default="true",
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
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.String(length=128), nullable=True),
        sa.CheckConstraint(
            "role IN ('super_admin', 'operator', 'auditor')",
            name="ck_admin_users_role",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["admin_users.id"],
            ondelete="SET NULL",
            name="fk_admin_users_created_by",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username", name="uq_admin_users_username"),
    )

    # ------------------------------------------------------------------ #
    # admin_refresh_sessions                                               #
    # ------------------------------------------------------------------ #
    op.create_table(
        "admin_refresh_sessions",
        sa.Column("id", sa.String(length=128), nullable=False),
        sa.Column("admin_id", sa.String(length=128), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("family_id", sa.String(length=128), nullable=False),
        sa.Column(
            "issued_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("client_ip", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.ForeignKeyConstraint(
            ["admin_id"],
            ["admin_users.id"],
            ondelete="CASCADE",
            name="fk_admin_refresh_sessions_admin_id",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "token_hash",
            name="uq_admin_refresh_sessions_token_hash",
        ),
    )
    op.create_index(
        "ix_admin_refresh_sessions_admin_id",
        "admin_refresh_sessions",
        ["admin_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_refresh_sessions_family_id",
        "admin_refresh_sessions",
        ["family_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_admin_refresh_sessions_token_hash"),
        "admin_refresh_sessions",
        ["token_hash"],
        unique=True,
    )

    # ------------------------------------------------------------------ #
    # admin_audit_log                                                      #
    # ------------------------------------------------------------------ #
    op.create_table(
        "admin_audit_log",
        sa.Column(
            "id",
            sa.Integer(),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("admin_id", sa.String(length=128), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("target_type", sa.String(length=64), nullable=True),
        sa.Column("target_id", sa.String(length=128), nullable=True),
        sa.Column("outcome", sa.String(length=20), nullable=False),
        sa.Column("client_ip", sa.String(length=45), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("detail", sa.JSON(), nullable=True),
        sa.CheckConstraint(
            "outcome IN ('success', 'failure')",
            name="ck_admin_audit_log_outcome",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_admin_audit_log_admin_id",
        "admin_audit_log",
        ["admin_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_audit_log_event_type",
        "admin_audit_log",
        ["event_type"],
        unique=False,
    )
    op.create_index(
        "ix_admin_audit_log_created_at",
        "admin_audit_log",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop admin_audit_log, admin_refresh_sessions, and admin_users tables."""

    # Drop in reverse dependency order.
    op.drop_index("ix_admin_audit_log_created_at", table_name="admin_audit_log")
    op.drop_index("ix_admin_audit_log_event_type", table_name="admin_audit_log")
    op.drop_index("ix_admin_audit_log_admin_id", table_name="admin_audit_log")
    op.drop_table("admin_audit_log")

    op.drop_index(
        op.f("ix_admin_refresh_sessions_token_hash"),
        table_name="admin_refresh_sessions",
    )
    op.drop_index(
        "ix_admin_refresh_sessions_family_id",
        table_name="admin_refresh_sessions",
    )
    op.drop_index(
        "ix_admin_refresh_sessions_admin_id",
        table_name="admin_refresh_sessions",
    )
    op.drop_table("admin_refresh_sessions")

    op.drop_table("admin_users")
