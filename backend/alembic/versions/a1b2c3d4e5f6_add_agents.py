"""add agents

Revision ID: a1b2c3d4e5f6
Revises: 5aa7c3d0b891
Create Date: 2026-01-23

Hand-written migration that ONLY creates the agents table.
Autogenerate would have dropped customers/orders/products/order_items/idempotency_keys
due to ORM/schema drift — do not use autogenerate for this step.

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '8f3e2a1b4c5d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'agents',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('slug', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('model', sa.String(length=64), nullable=False, server_default='gpt-4o-mini'),
        sa.Column('system_prompt', sa.Text(), nullable=True),
        sa.Column('tools', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('success_rate', sa.Float(), nullable=True),
        sa.Column('last_execution_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'slug', name='uq_agent_tenant_slug'),
    )
    op.create_index('ix_agents_tenant_id', 'agents', ['tenant_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_agents_tenant_id', table_name='agents')
    op.drop_table('agents')
