"""add taxonomy tables

Revision ID: a1b2c3d4e5f6
Revises: 8eaa5db9abe4
Create Date: 2026-02-10 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '8eaa5db9abe4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # taxonomy_categories
    op.create_table(
        'taxonomy_categories',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('parent_id', sa.Integer(), nullable=True),
        sa.Column('depth', sa.Integer(), nullable=False),
        sa.Column('path', sa.Text(), nullable=False),
        sa.Column('taxonomy_type', sa.String(length=30), nullable=False),
        sa.Column('name', sa.Text(), nullable=False),
        sa.Column('slug', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('knowde_url', sa.Text(), nullable=True),
        sa.Column('sort_order', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ),
        sa.ForeignKeyConstraint(['parent_id'], ['taxonomy_categories.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('org_id', 'slug', name='uq_taxonomy_org_slug'),
        sa.UniqueConstraint('org_id', 'parent_id', 'name', name='uq_taxonomy_org_parent_name'),
    )
    op.create_index('idx_taxonomy_type', 'taxonomy_categories', ['taxonomy_type'])
    op.create_index('idx_taxonomy_path', 'taxonomy_categories', ['path'])
    op.create_index(op.f('ix_taxonomy_categories_org_id'), 'taxonomy_categories', ['org_id'])
    op.create_index(op.f('ix_taxonomy_categories_parent_id'), 'taxonomy_categories', ['parent_id'])

    # product_categories (junction)
    op.create_table(
        'product_categories',
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.Column('is_primary', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['category_id'], ['taxonomy_categories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('product_id', 'category_id'),
    )
    op.create_index('idx_product_categories_product', 'product_categories', ['product_id'])
    op.create_index('idx_product_categories_category', 'product_categories', ['category_id'])

    # product_attributes
    op.create_table(
        'product_attributes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('org_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('attribute_group', sa.String(length=50), nullable=False),
        sa.Column('attribute_key', sa.String(length=100), nullable=False),
        sa.Column('attribute_value', sa.Text(), nullable=False),
        sa.Column('value_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=False, server_default='manual'),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['org_id'], ['organizations.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('product_id', 'org_id', 'attribute_group', 'attribute_key', name='uq_product_attribute'),
    )
    op.create_index('idx_product_attrs_product', 'product_attributes', ['product_id'])
    op.create_index('idx_product_attrs_group', 'product_attributes', ['attribute_group'])
    op.create_index('idx_product_attrs_key', 'product_attributes', ['attribute_key'])
    op.create_index(op.f('ix_product_attributes_org_id'), 'product_attributes', ['org_id'])

    # hs_code_mappings
    op.create_table(
        'hs_code_mappings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('category_id', sa.Integer(), nullable=False),
        sa.Column('hs_code', sa.String(length=10), nullable=False),
        sa.Column('hs_description', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['category_id'], ['taxonomy_categories.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('category_id', 'hs_code', name='uq_category_hs_code'),
    )
    op.create_index('idx_hs_mapping_category', 'hs_code_mappings', ['category_id'])
    op.create_index('idx_hs_mapping_code', 'hs_code_mappings', ['hs_code'])


def downgrade() -> None:
    op.drop_table('hs_code_mappings')
    op.drop_table('product_attributes')
    op.drop_table('product_categories')
    op.drop_table('taxonomy_categories')
