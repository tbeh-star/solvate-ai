from __future__ import annotations

from typing import Optional
from datetime import datetime

from pydantic import BaseModel, ConfigDict


# ── Category Schemas ──


class CategoryBase(BaseModel):
    name: str
    taxonomy_type: str  # "industry" | "product_family" | "subcategory"
    description: Optional[str] = None
    sort_order: int = 0


class CategoryCreate(CategoryBase):
    parent_id: Optional[int] = None
    slug: Optional[str] = None  # auto-generated if not provided
    knowde_url: Optional[str] = None
    metadata: Optional[dict] = None


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None
    metadata: Optional[dict] = None


class CategoryOut(CategoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    org_id: Optional[str] = None
    parent_id: Optional[int] = None
    depth: int
    path: str
    slug: str
    knowde_url: Optional[str] = None
    is_active: bool
    metadata: Optional[dict] = None
    created_at: datetime
    updated_at: datetime


class CategoryTreeNode(CategoryOut):
    children: list[CategoryTreeNode] = []


# ── Product-Category Assignment ──


class ProductCategoryAssign(BaseModel):
    category_ids: list[int]
    set_primary_id: Optional[int] = None  # which one is the primary category


class ProductCategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: int
    category_id: int
    is_primary: bool
    created_at: datetime
    category: Optional[CategoryOut] = None


# ── Product Attribute Schemas ──


class AttributeBase(BaseModel):
    attribute_group: str
    attribute_key: str
    attribute_value: str
    value_json: Optional[dict] = None
    source: str = "manual"
    confidence: Optional[float] = None


class AttributeCreate(AttributeBase):
    pass


class AttributeBulkCreate(BaseModel):
    attributes: list[AttributeCreate]


class AttributeOut(AttributeBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    org_id: Optional[str] = None
    created_at: datetime


class AttributeGroupOut(BaseModel):
    group: str
    attributes: list[AttributeOut]


# ── HS Code Mapping ──


class HSCodeMappingCreate(BaseModel):
    category_id: int
    hs_code: str
    hs_description: Optional[str] = None


class HSCodeMappingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category_id: int
    hs_code: str
    hs_description: Optional[str] = None


# ── Taxonomy Tree Response ──


class TaxonomyTreeOut(BaseModel):
    industries: list[CategoryTreeNode]
    product_families: list[CategoryTreeNode]
