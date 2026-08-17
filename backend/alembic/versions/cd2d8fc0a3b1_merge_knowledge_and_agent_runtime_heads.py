"""merge knowledge and agent runtime heads

Revision ID: cd2d8fc0a3b1
Revises: c5d6e7f8a9b0, f2a3b4c5d6e7
Create Date: 2026-08-17
"""

from collections.abc import Sequence

revision: str = "cd2d8fc0a3b1"
down_revision: tuple[str, str] = (
    "c5d6e7f8a9b0",
    "f2a3b4c5d6e7",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
