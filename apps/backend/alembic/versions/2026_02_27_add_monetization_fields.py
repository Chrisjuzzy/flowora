"""Add monetization fields to users table

Revision ID: add_monetization_001
Revises: 670ef2d63cfb
Create Date: 2026-02-27 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_monetization_001'
down_revision: Union[str, Sequence[str], None] = '670ef2d63cfb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add monetization columns with defaults for existing rows."""
    # Add executions_this_month column
    op.add_column('users', sa.Column('executions_this_month', sa.Integer(), nullable=False, server_default='0'))
    
    # Add tokens_used_this_month column
    op.add_column('users', sa.Column('tokens_used_this_month', sa.Integer(), nullable=False, server_default='0'))
    
    # Add subscription_tier column
    op.add_column('users', sa.Column('subscription_tier', sa.String(), nullable=False, server_default='free'))
    
    # Add subscription_status column
    op.add_column('users', sa.Column('subscription_status', sa.String(), nullable=False, server_default='active'))
    
    # Note: server_default is used to populate existing rows during migration.
    # SQLite does not support removing defaults with ALTER COLUMN, so we keep them.
    # The SQLAlchemy model handles default values for new inserts at the application level.


def downgrade() -> None:
    """Downgrade schema - remove monetization columns."""
    op.drop_column('users', 'subscription_status')
    op.drop_column('users', 'subscription_tier')
    op.drop_column('users', 'tokens_used_this_month')
    op.drop_column('users', 'executions_this_month')
