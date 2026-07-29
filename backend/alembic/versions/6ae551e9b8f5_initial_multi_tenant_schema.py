"""initial_multi_tenant_schema

Revision ID: 6ae551e9b8f5
Revises: 
Create Date: 2026-07-29 18:49:15.864623

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6ae551e9b8f5'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create multi-tenant database schema."""
    # Create tenants table
    op.create_table(
        'tenants',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create api_keys table
    op.create_table(
        'api_keys',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('key_hash', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key_hash')
    )
    op.create_index('ix_api_keys_tenant_id', 'api_keys', ['tenant_id'])
    op.create_index('ix_api_keys_key_hash', 'api_keys', ['key_hash'])

    # Create agents table
    op.create_table(
        'agents',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('system_prompt', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'name', name='uq_agents_tenant_name')
    )
    op.create_index('ix_agents_tenant_id', 'agents', ['tenant_id'])

    # Create conversations table
    op.create_table(
        'conversations',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('tenant_id', sa.String(length=64), nullable=False),
        sa.Column('agent_id', sa.String(length=64), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=True),
        sa.Column('user_id', sa.String(length=64), nullable=True),
        sa.Column('metadata_json', sa.Text(), nullable=True),
        sa.Column('is_archived', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_conversations_tenant_id', 'conversations', ['tenant_id'])
    op.create_index('ix_conversations_agent_id', 'conversations', ['agent_id'])
    op.create_index('ix_conversations_user_id', 'conversations', ['user_id'])
    op.create_index('ix_conversations_created_at', 'conversations', ['created_at'])

    # Create messages table
    op.create_table(
        'messages',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('conversation_id', sa.String(length=64), nullable=False),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('prompt_tokens', sa.Integer(), nullable=False),
        sa.Column('completion_tokens', sa.Integer(), nullable=False),
        sa.Column('model', sa.String(length=100), nullable=True),
        sa.Column('finish_reason', sa.String(length=50), nullable=True),
        sa.Column('latency_ms', sa.Integer(), nullable=True),
        sa.Column('request_id', sa.String(length=64), nullable=True),
        sa.Column('idempotency_key', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['conversation_id'], ['conversations.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_messages_conversation_id', 'messages', ['conversation_id'])
    op.create_index('ix_messages_created_at', 'messages', ['created_at'])
    op.create_index('ix_messages_idempotency_key', 'messages', ['idempotency_key'])


def downgrade() -> None:
    """Drop all tables."""
    op.drop_index('ix_messages_idempotency_key', table_name='messages')
    op.drop_index('ix_messages_created_at', table_name='messages')
    op.drop_index('ix_messages_conversation_id', table_name='messages')
    op.drop_table('messages')
    
    op.drop_index('ix_conversations_created_at', table_name='conversations')
    op.drop_index('ix_conversations_user_id', table_name='conversations')
    op.drop_index('ix_conversations_agent_id', table_name='conversations')
    op.drop_index('ix_conversations_tenant_id', table_name='conversations')
    op.drop_table('conversations')
    
    op.drop_index('ix_agents_tenant_id', table_name='agents')
    op.drop_table('agents')
    
    op.drop_index('ix_api_keys_key_hash', table_name='api_keys')
    op.drop_index('ix_api_keys_tenant_id', table_name='api_keys')
    op.drop_table('api_keys')
    
    op.drop_table('tenants')
