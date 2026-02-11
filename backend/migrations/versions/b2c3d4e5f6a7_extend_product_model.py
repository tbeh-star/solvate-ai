"""extend product model with taxonomy fields

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-02-10 12:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('products', sa.Column('inci_name', sa.Text(), nullable=True))
    op.add_column('products', sa.Column('chemical_family', sa.String(length=100), nullable=True))
    op.add_column('products', sa.Column('physical_form', sa.String(length=50), nullable=True))
    op.add_column('products', sa.Column('brand_name', sa.String(length=200), nullable=True))
    op.add_column('products', sa.Column('producer', sa.String(length=200), nullable=True))
    op.add_column('products', sa.Column(
        'updated_at', sa.DateTime(timezone=True),
        server_default=sa.text('now()'), nullable=True
    ))


def downgrade() -> None:
    op.drop_column('products', 'updated_at')
    op.drop_column('products', 'producer')
    op.drop_column('products', 'brand_name')
    op.drop_column('products', 'physical_form')
    op.drop_column('products', 'chemical_family')
    op.drop_column('products', 'inci_name')
