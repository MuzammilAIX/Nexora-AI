"""add email_verified columns

Revision ID: abcd1234efgh
Revises: 999999999999
Create Date: 2026-11-23

"""
from alembic import op
import sqlalchemy as sa


revision = 'abcd1234efgh'
down_revision = '999999999999'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add the three new columns to users table
    op.add_column('users', sa.Column('email_verified', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('users', sa.Column('verification_token', sa.String(), nullable=True))
    op.add_column('users', sa.Column('verification_token_expires', sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'verification_token_expires')
    op.drop_column('users', 'verification_token')
    op.drop_column('users', 'email_verified')
