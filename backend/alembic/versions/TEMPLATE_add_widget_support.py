"""add widget support for agents

Revision ID: <WILL_BE_GENERATED>
Revises: <DEVELOPER_2_REVISION>
Create Date: <TIMESTAMP>

Description:
    - Adds widget_enabled and widget_public_id columns to agents table
    - Creates agent_allowed_origins table for origin whitelisting
    - Adds session_id column to conversations table for widget session isolation
    - All existing agents remain unchanged (widget_enabled defaults to False)
    - No data is modified or deleted

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '<WILL_BE_GENERATED>'
down_revision: Union[str, None] = '<DEVELOPER_2_REVISION>'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add widget support to the platform.
    
    Changes:
    1. Add widget_enabled (default False) and widget_public_id (nullable) to agents
    2. Create agent_allowed_origins table with unique constraint
    3. Add session_id (nullable) to conversations for widget session isolation
    """
    
    # ========================================================================
    # 1. Add widget columns to agents table
    # ========================================================================
    op.add_column('agents', 
        sa.Column('widget_enabled', sa.Boolean(), 
                  server_default=sa.text('false'), 
                  nullable=False))
    
    op.add_column('agents', 
        sa.Column('widget_public_id', sa.String(length=64), 
                  nullable=True))
    
    # Create unique index on widget_public_id (partial index - only non-NULL values)
    op.create_index(
        'idx_agents_widget_public_id',
        'agents',
        ['widget_public_id'],
        unique=True,
        postgresql_where=sa.text('widget_public_id IS NOT NULL')
    )
    
    # ========================================================================
    # 2. Create agent_allowed_origins table
    # ========================================================================
    op.create_table(
        'agent_allowed_origins',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=128), nullable=False),
        sa.Column('agent_id', sa.String(length=128), nullable=False),
        sa.Column('origin', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), 
                  server_default=sa.text('now()'), 
                  nullable=False),
        
        # Primary key
        sa.PrimaryKeyConstraint('id', name='pk_agent_allowed_origins'),
        
        # Foreign keys
        sa.ForeignKeyConstraint(
            ['tenant_id'], 
            ['tenants.id'], 
            name='fk_agent_allowed_origins_tenant',
            ondelete='CASCADE'
        ),
        sa.ForeignKeyConstraint(
            ['agent_id'], 
            ['agents.id'], 
            name='fk_agent_allowed_origins_agent',
            ondelete='CASCADE'
        ),
        
        # Unique constraint: prevent duplicate origins per agent
        sa.UniqueConstraint(
            'tenant_id', 'agent_id', 'origin',
            name='uq_agent_allowed_origins_tenant_agent_origin'
        ),
        
        # Check constraint: validate origin format
        sa.CheckConstraint(
            "origin ~ '^https?://[a-zA-Z0-9.-]+(:[0-9]+)?$'",
            name='ck_agent_allowed_origins_origin_format'
        )
    )
    
    # Create composite index for faster lookups
    op.create_index(
        'idx_agent_allowed_origins_tenant_agent',
        'agent_allowed_origins',
        ['tenant_id', 'agent_id']
    )
    
    # ========================================================================
    # 3. Add session_id to conversations table
    # ========================================================================
    op.add_column('conversations',
        sa.Column('session_id', sa.String(length=128), nullable=True))
    
    # Create partial index for widget sessions (ignoring NULL API-key conversations)
    op.create_index(
        'idx_conversations_tenant_agent_session',
        'conversations',
        ['tenant_id', 'agent_id', 'session_id'],
        postgresql_where=sa.text('session_id IS NOT NULL')
    )


def downgrade() -> None:
    """
    Remove widget support from the platform.
    
    Reverses all changes made in upgrade().
    """
    
    # Remove in reverse order
    
    # 3. Remove session_id from conversations
    op.drop_index('idx_conversations_tenant_agent_session', table_name='conversations')
    op.drop_column('conversations', 'session_id')
    
    # 2. Drop agent_allowed_origins table
    op.drop_index('idx_agent_allowed_origins_tenant_agent', table_name='agent_allowed_origins')
    op.drop_table('agent_allowed_origins')
    
    # 1. Remove widget columns from agents
    op.drop_index('idx_agents_widget_public_id', table_name='agents')
    op.drop_column('agents', 'widget_public_id')
    op.drop_column('agents', 'widget_enabled')
