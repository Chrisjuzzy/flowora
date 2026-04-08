"""add_marketplace_agent_model

Revision ID: 2026_03_02_marketplace_agents
Revises: 2026_03_01_revenue_platform
Create Date: 2026-03-02 10:00:00.000000

This migration adds the marketplace_agents table for storing
production-ready AI agents that users can execute.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2026_03_02_marketplace_agents'
down_revision = '2026_03_01_revenue_platform'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create marketplace_agents table
    op.create_table(
        'marketplace_agents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('slug', sa.String(), nullable=False, unique=True),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('short_tagline', sa.String(), nullable=True),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('credit_cost', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('is_system_agent', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('creator_user_id', sa.Integer(), nullable=True),
        sa.Column('estimated_output_time', sa.Integer(), nullable=True),
        sa.Column('popularity_score', sa.Integer(), nullable=False, server_default='50'),
        sa.Column('execution_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['creator_user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Add indexes
    op.create_index(op.f('ix_marketplace_agents_name'), 'marketplace_agents', ['name'], unique=False)
    op.create_index(op.f('ix_marketplace_agents_slug'), 'marketplace_agents', ['slug'], unique=True)
    op.create_index(op.f('ix_marketplace_agents_category'), 'marketplace_agents', ['category'], unique=False)
    op.create_index(op.f('ix_marketplace_agents_is_active'), 'marketplace_agents', ['is_active'], unique=False)
    op.create_index(op.f('ix_marketplace_agents_created_at'), 'marketplace_agents', ['created_at'], unique=False)


def downgrade() -> None:
    # Drop marketplace_agents table
    op.drop_index(op.f('ix_marketplace_agents_created_at'), table_name='marketplace_agents')
    op.drop_index(op.f('ix_marketplace_agents_is_active'), table_name='marketplace_agents')
    op.drop_index(op.f('ix_marketplace_agents_category'), table_name='marketplace_agents')
    op.drop_index(op.f('ix_marketplace_agents_slug'), table_name='marketplace_agents')
    op.drop_index(op.f('ix_marketplace_agents_name'), table_name='marketplace_agents')
    op.drop_table('marketplace_agents')
