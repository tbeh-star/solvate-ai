from __future__ import annotations

from typing import Optional

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class TaxonomyCategory(Base):
    """
    Hierarchical category tree supporting Industry and ProductFamily axes.
    Uses adjacency list + materialized path for flexible querying.

    org_id = NULL  -> global template (Knowde seed data)
    org_id = UUID  -> org-specific copy (editable by that org)
    """

    __tablename__ = "taxonomy_categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Multi-tenancy: NULL = global template, UUID = org-specific
    org_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True
    )

    # Tree structure
    parent_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("taxonomy_categories.id"), index=True
    )
    depth: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    path: Mapped[str] = mapped_column(Text, nullable=False)
    # Materialized path e.g. "1/5/23" for fast ancestor/descendant queries

    # Classification
    taxonomy_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # "industry" | "product_family" | "subcategory"

    # Identity
    name: Mapped[str] = mapped_column(Text, nullable=False)
    slug: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    # External reference
    knowde_url: Mapped[Optional[str]] = mapped_column(Text)

    # Display
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Flexible metadata
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("idx_taxonomy_type", "taxonomy_type"),
        Index("idx_taxonomy_path", "path"),
        UniqueConstraint("org_id", "slug", name="uq_taxonomy_org_slug"),
        UniqueConstraint("org_id", "parent_id", "name", name="uq_taxonomy_org_parent_name"),
    )


class ProductCategory(Base):
    """
    Many-to-many junction: products belong to multiple categories.
    E.g. ELASTOSIL can be in both 'Elastomers' (product_family)
    AND 'Automotive' (industry).
    """

    __tablename__ = "product_categories"

    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="CASCADE"), primary_key=True
    )
    category_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("taxonomy_categories.id", ondelete="CASCADE"),
        primary_key=True,
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_product_categories_product", "product_id"),
        Index("idx_product_categories_category", "category_id"),
    )


class ProductAttribute(Base):
    """
    Flexible key-value attributes for products (Knowde-style enrichment).

    Attribute groups:
    - chemical_identity: CAS, INCI, chemical family
    - functions: primary/secondary functions (emulsifier, antioxidant, etc.)
    - applications: end uses (shampoos, injection molding, etc.)
    - physical_properties: form, density, viscosity
    - regulatory: FDA, EU, GRAS, Halal, Kosher
    - sustainability: origin, biodegradable, vegan, organic, non-GMO
    - technical: processing methods, mechanical properties

    org_id = NULL  -> global attribute (shared)
    org_id = UUID  -> org-specific attribute
    """

    __tablename__ = "product_attributes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    product_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False
    )

    # Multi-tenancy
    org_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id"), index=True
    )

    attribute_group: Mapped[str] = mapped_column(String(50), nullable=False)
    attribute_key: Mapped[str] = mapped_column(String(100), nullable=False)
    attribute_value: Mapped[str] = mapped_column(Text, nullable=False)

    # For structured values (numeric ranges, lists, nested data)
    value_json: Mapped[Optional[dict]] = mapped_column(JSONB)

    # Provenance
    source: Mapped[str] = mapped_column(
        String(50), nullable=False, default="manual"
    )
    confidence: Mapped[Optional[float]] = mapped_column(Float)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("idx_product_attrs_product", "product_id"),
        Index("idx_product_attrs_group", "attribute_group"),
        Index("idx_product_attrs_key", "attribute_key"),
        UniqueConstraint(
            "product_id",
            "org_id",
            "attribute_group",
            "attribute_key",
            name="uq_product_attribute",
        ),
    )


class HSCodeMapping(Base):
    """
    Maps taxonomy categories to HS codes for Smart Trade Data integration.
    A category can map to multiple HS codes and vice versa.
    """

    __tablename__ = "hs_code_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("taxonomy_categories.id", ondelete="CASCADE"),
        nullable=False,
    )
    hs_code: Mapped[str] = mapped_column(String(10), nullable=False)
    hs_description: Mapped[Optional[str]] = mapped_column(Text)

    __table_args__ = (
        Index("idx_hs_mapping_category", "category_id"),
        Index("idx_hs_mapping_code", "hs_code"),
        UniqueConstraint("category_id", "hs_code", name="uq_category_hs_code"),
    )
