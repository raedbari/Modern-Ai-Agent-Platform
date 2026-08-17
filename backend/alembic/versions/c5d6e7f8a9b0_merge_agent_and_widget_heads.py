"""merge agent prompt version and custom widget connector heads

Revision ID: c5d6e7f8a9b0
Revises: 19c8589961b5, b13c7a9e42f6
Create Date: 2026-08-16
"""

from typing import Sequence, Union


revision: str = "c5d6e7f8a9b0"
down_revision: Union[str, Sequence[str], None] = (
    "19c8589961b5",
    "b13c7a9e42f6",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge independent migration heads without schema changes."""


def downgrade() -> None:
    """Split migration history back to the two preceding heads."""
