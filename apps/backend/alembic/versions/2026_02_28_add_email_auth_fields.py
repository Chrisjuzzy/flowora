"""Add email verification and password reset fields to users

Revision ID: add_email_auth_001
Revises: add_monetization_001
Create Date: 2026-02-28 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_email_auth_001'
down_revision: Union[str, Sequence[str], None] = 'add_monetization_001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add email verification and password reset fields."""
    # Add email verification fields
    op.add_column('users', sa.Column('is_email_verified', sa.String(), nullable=False, server_default='False'))
    op.add_column('users', sa.Column('email_verification_code', sa.String(), nullable=True))
    op.add_column('users', sa.Column('email_verification_expires_at', sa.DateTime(), nullable=True))
    
    # Add password reset fields
    op.add_column('users', sa.Column('password_reset_token', sa.String(), nullable=True))
    op.add_column('users', sa.Column('password_reset_expires_at', sa.DateTime(), nullable=True))


def downgrade() -> None:
    """Downgrade schema - remove email verification and password reset fields."""
    op.drop_column('users', 'password_reset_expires_at')
    op.drop_column('users', 'password_reset_token')
    op.drop_column('users', 'email_verification_expires_at')
    op.drop_column('users', 'email_verification_code')
    op.drop_column('users', 'is_email_verified')
