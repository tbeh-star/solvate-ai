"""add versioning + region columns to golden_records

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h8
Create Date: 2026-02-11 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd4e5f6g7h8i9'
down_revision: Union[str, None] = 'c3d4e5f6g7h8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Add new columns ---
    op.add_column(
        'golden_records',
        sa.Column('region', sa.String(length=10), nullable=False,
                  server_default='GLOBAL'),
    )
    op.add_column(
        'golden_records',
        sa.Column('doc_language', sa.String(length=5), nullable=True),
    )
    op.add_column(
        'golden_records',
        sa.Column('revision_date', sa.String(length=20), nullable=True),
    )
    op.add_column(
        'golden_records',
        sa.Column('document_type', sa.String(length=10), nullable=True),
    )
    op.add_column(
        'golden_records',
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
    )
    op.add_column(
        'golden_records',
        sa.Column('is_latest', sa.Boolean(), nullable=False,
                  server_default=sa.text('true')),
    )

    # --- Replace old unique index with composite one ---
    op.drop_index('uq_golden_records_run_product', table_name='golden_records')
    op.create_index(
        'uq_golden_records_run_product_region', 'golden_records',
        ['run_id', 'product_name', 'region'], unique=True,
    )

    # --- Fast "latest version" queries ---
    op.execute(
        "CREATE INDEX idx_golden_records_latest "
        "ON golden_records (product_name, region) "
        "WHERE is_latest = true"
    )

    # --- Version-history lookup ---
    op.create_index(
        'idx_golden_records_version', 'golden_records',
        ['product_name', 'region', 'version'],
    )


def downgrade() -> None:
    op.drop_index('idx_golden_records_version', table_name='golden_records')
    op.execute("DROP INDEX IF EXISTS idx_golden_records_latest")
    op.drop_index('uq_golden_records_run_product_region',
                  table_name='golden_records')

    # Restore original unique index
    op.create_index(
        'uq_golden_records_run_product', 'golden_records',
        ['run_id', 'product_name'], unique=True,
    )

    op.drop_column('golden_records', 'is_latest')
    op.drop_column('golden_records', 'version')
    op.drop_column('golden_records', 'document_type')
    op.drop_column('golden_records', 'revision_date')
    op.drop_column('golden_records', 'doc_language')
    op.drop_column('golden_records', 'region')
