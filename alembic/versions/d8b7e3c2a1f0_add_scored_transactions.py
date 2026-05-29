"""add scored_transactions table

Revision ID: d8b7e3c2a1f0
Revises: 8d3b19b5616a
Create Date: 2026-05-29 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd8b7e3c2a1f0'
down_revision: Union[str, Sequence[str], None] = '8d3b19b5616a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('scored_transactions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tx_id', sa.String(), nullable=False),
        sa.Column('iban', sa.String(), nullable=False),
        sa.Column('importo', sa.Float(), nullable=False),
        sa.Column('rischio', sa.String(), nullable=False),
        sa.Column('motivazione', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_scored_transactions')),
        sa.UniqueConstraint('tx_id', name=op.f('uq_scored_transactions_tx_id'))
    )
    op.create_index(op.f('ix_scored_transactions_tx_id'), 'scored_transactions', ['tx_id'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_scored_transactions_tx_id'), table_name='scored_transactions')
    op.drop_table('scored_transactions')
