"""add custom widget connector type

Revision ID: b13c7a9e42f6
Revises: 7f2a4c8e9d31
"""

from alembic import op


revision = "b13c7a9e42f6"
down_revision = "7f2a4c8e9d31"
branch_labels = None
depends_on = None


CONSTRAINT_NAME = (
    "ck_widget_connector_pairings_connector_type"
)

TABLE_NAME = "widget_connector_pairings"


def upgrade() -> None:
    op.drop_constraint(
        CONSTRAINT_NAME,
        TABLE_NAME,
        type_="check",
    )

    op.create_check_constraint(
        CONSTRAINT_NAME,
        TABLE_NAME,
        (
            "connector_type IN "
            "('wordpress', 'react_next', "
            "'managed', 'custom')"
        ),
    )


def downgrade() -> None:
    op.drop_constraint(
        CONSTRAINT_NAME,
        TABLE_NAME,
        type_="check",
    )

    op.create_check_constraint(
        CONSTRAINT_NAME,
        TABLE_NAME,
        (
            "connector_type IN "
            "('wordpress', 'react_next', "
            "'managed')"
        ),
    )
