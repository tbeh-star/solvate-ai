"""add extraction_runs and golden_records tables

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6a7
Create Date: 2026-02-11 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6g7h8'
down_revision: Union[str, None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- extraction_runs ---
    op.create_table(
        'extraction_runs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('pdf_count', sa.Integer(), nullable=True),
        sa.Column('golden_records_count', sa.Integer(), nullable=True),
        sa.Column('total_cost', sa.Float(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False,
                  server_default='running'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # --- golden_records ---
    op.create_table(
        'golden_records',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('run_id', sa.Integer(), nullable=False),
        sa.Column('product_name', sa.Text(), nullable=False),
        sa.Column('brand', sa.String(length=200), nullable=True),
        sa.Column('golden_record', postgresql.JSONB(astext_type=sa.Text()),
                  nullable=False),
        sa.Column('source_files', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('source_count', sa.Integer(), nullable=True),
        sa.Column('missing_count', sa.Integer(), nullable=True),
        sa.Column('completeness', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['run_id'], ['extraction_runs.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # Indexes for golden_records
    op.create_index('idx_golden_records_run', 'golden_records', ['run_id'])
    op.create_index('idx_golden_records_product', 'golden_records', ['product_name'])
    op.create_index('idx_golden_records_brand', 'golden_records', ['brand'])
    op.create_index(
        'idx_golden_records_jsonb', 'golden_records', ['golden_record'],
        postgresql_using='gin',
    )
    op.create_index(
        'uq_golden_records_run_product', 'golden_records',
        ['run_id', 'product_name'], unique=True,
    )


def downgrade() -> None:
    op.drop_index('uq_golden_records_run_product', table_name='golden_records')
    op.drop_index('idx_golden_records_jsonb', table_name='golden_records')
    op.drop_index('idx_golden_records_brand', table_name='golden_records')
    op.drop_index('idx_golden_records_product', table_name='golden_records')
    op.drop_index('idx_golden_records_run', table_name='golden_records')
    op.drop_table('golden_records')
    op.drop_table('extraction_runs')
