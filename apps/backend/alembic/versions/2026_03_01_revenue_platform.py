"""add_revenue_platform_models

Revision ID: 2026_03_01_revenue_platform
Revises: 2026_02_28_add_email_auth_fields
Create Date: 2026-03-01 10:00:00.000000

This migration adds the models needed for revenue-platform expansion:
- agent_type field to agents table
- credit_transactions table for credit tracking
- user_revenue_tracking table for revenue reporting
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '2026_03_01_revenue_platform'
down_revision = '2026_02_28_add_email_auth_fields'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add agent_type column to agents table
    op.add_column(
        'agents',
        sa.Column('agent_type', sa.String(), nullable=True)
    )
    op.create_index(
        op.f('ix_agents_agent_type'),
        'agents',
        ['agent_type'],
        unique=False
    )

    # Create credit_transactions table
    op.create_table(
        'credit_transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('agent_type', sa.String(), nullable=True),
        sa.Column('reference_id', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        op.f('ix_credit_transactions_created_at'),
        'credit_transactions',
        ['created_at'],
        unique=False
    )
    op.create_index(
        op.f('ix_credit_transactions_user_id'),
        'credit_transactions',
        ['user_id'],
        unique=False
    )

    # Create user_revenue_tracking table
    op.create_table(
        'user_revenue_tracking',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('reported_revenue', sa.Float(), nullable=False),
        sa.Column('source_agent', sa.String(), nullable=True),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('verified', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(
        op.f('ix_user_revenue_tracking_created_at'),
        'user_revenue_tracking',
        ['created_at'],
        unique=False
    )
    op.create_index(
        op.f('ix_user_revenue_tracking_user_id'),
        'user_revenue_tracking',
        ['user_id'],
        unique=False
    )


def downgrade() -> None:
    # Drop user_revenue_tracking table
    op.drop_index(
        op.f('ix_user_revenue_tracking_user_id'),
        table_name='user_revenue_tracking'
    )
    op.drop_index(
        op.f('ix_user_revenue_tracking_created_at'),
        table_name='user_revenue_tracking'
    )
    op.drop_table('user_revenue_tracking')

    # Drop credit_transactions table
    op.drop_index(
        op.f('ix_credit_transactions_user_id'),
        table_name='credit_transactions'
    )
    op.drop_index(
        op.f('ix_credit_transactions_created_at'),
        table_name='credit_transactions'
    )
    op.drop_table('credit_transactions')

    # Drop agent_type column from agents table
    op.drop_index(
        op.f('ix_agents_agent_type'),
        table_name='agents'
    )
    op.drop_column('agents', 'agent_type')
