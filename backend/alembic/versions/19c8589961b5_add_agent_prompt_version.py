"""add_agent_prompt_version

Revision ID: 19c8589961b5
Revises: f4a2b7c9d011
Create Date: 2026-08-15 18:37:34.964346

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '19c8589961b5'
down_revision: Union[str, Sequence[str], None] = 'f4a2b7c9d011'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add prompt_version column to agents table for tracking prompt iterations.

    This enables evaluation platform to correlate results with specific prompt
    versions and supports A/B testing of prompt improvements.
    """
    op.add_column(
        'agents',
        sa.Column(
            'prompt_version',
            sa.String(length=64),
            nullable=False,
            server_default='v1',
        )
    )


def downgrade() -> None:
    """Remove prompt_version column from agents table."""
    op.drop_column('agents', 'prompt_version')
