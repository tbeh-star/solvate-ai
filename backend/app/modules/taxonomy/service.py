from __future__ import annotations

import re
import uuid
from typing import Optional

from sqlalchemy import select, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.taxonomy.models import (
    HSCodeMapping,
    ProductAttribute,
    ProductCategory,
    TaxonomyCategory,
)


def _slugify(text: str) -> str:
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    return re.sub(r"-+", "-", slug).strip("-")


# ── Category CRUD ──


async def create_category(
    db: AsyncSession,
    *,
    org_id: Optional[uuid.UUID],
    name: str,
    taxonomy_type: str,
    parent_id: Optional[int] = None,
    slug: Optional[str] = None,
    description: Optional[str] = None,
    knowde_url: Optional[str] = None,
    sort_order: int = 0,
    metadata: Optional[dict] = None,
) -> TaxonomyCategory:
    depth = 0
    path = ""

    if parent_id:
        parent = await db.get(TaxonomyCategory, parent_id)
        if parent:
            depth = parent.depth + 1
            path = parent.path  # will be updated after insert

    cat = TaxonomyCategory(
        org_id=org_id,
        parent_id=parent_id,
        depth=depth,
        path="temp",
        taxonomy_type=taxonomy_type,
        name=name,
        slug=slug or _slugify(name),
        description=description,
        knowde_url=knowde_url,
        sort_order=sort_order,
        metadata_=metadata or {},
    )
    db.add(cat)
    await db.flush()

    # Set materialized path after we have the ID
    if parent_id and path:
        cat.path = f"{path}/{cat.id}"
    else:
        cat.path = str(cat.id)

    await db.flush()
    return cat


async def get_category(db: AsyncSession, category_id: int) -> Optional[TaxonomyCategory]:
    return await db.get(TaxonomyCategory, category_id)


async def get_children(
    db: AsyncSession, category_id: int
) -> list[TaxonomyCategory]:
    result = await db.execute(
        select(TaxonomyCategory)
        .where(TaxonomyCategory.parent_id == category_id)
        .order_by(TaxonomyCategory.sort_order, TaxonomyCategory.name)
    )
    return list(result.scalars().all())


async def get_descendants(
    db: AsyncSession, category_id: int
) -> list[TaxonomyCategory]:
    """Get all descendants using materialized path prefix query."""
    cat = await db.get(TaxonomyCategory, category_id)
    if not cat:
        return []
    result = await db.execute(
        select(TaxonomyCategory)
        .where(TaxonomyCategory.path.like(f"{cat.path}/%"))
        .order_by(TaxonomyCategory.depth, TaxonomyCategory.sort_order)
    )
    return list(result.scalars().all())


async def get_root_categories(
    db: AsyncSession,
    org_id: Optional[uuid.UUID],
    taxonomy_type: Optional[str] = None,
) -> list[TaxonomyCategory]:
    conditions = [
        TaxonomyCategory.parent_id.is_(None),
        TaxonomyCategory.is_active.is_(True),
    ]
    if org_id is not None:
        conditions.append(TaxonomyCategory.org_id == org_id)
    else:
        conditions.append(TaxonomyCategory.org_id.is_(None))

    if taxonomy_type:
        conditions.append(TaxonomyCategory.taxonomy_type == taxonomy_type)

    result = await db.execute(
        select(TaxonomyCategory)
        .where(and_(*conditions))
        .order_by(TaxonomyCategory.sort_order, TaxonomyCategory.name)
    )
    return list(result.scalars().all())


async def update_category(
    db: AsyncSession,
    category_id: int,
    **kwargs: object,
) -> Optional[TaxonomyCategory]:
    cat = await db.get(TaxonomyCategory, category_id)
    if not cat:
        return None
    for key, value in kwargs.items():
        if value is not None and hasattr(cat, key):
            setattr(cat, key, value)
    await db.flush()
    return cat


async def deactivate_category(
    db: AsyncSession, category_id: int
) -> Optional[TaxonomyCategory]:
    return await update_category(db, category_id, is_active=False)


# ── Full Tree Builder ──


async def build_tree(
    db: AsyncSession,
    org_id: Optional[uuid.UUID],
    taxonomy_type: Optional[str] = None,
) -> list[dict]:
    """Build a nested tree structure from flat categories."""
    conditions = [TaxonomyCategory.is_active.is_(True)]
    if org_id is not None:
        conditions.append(TaxonomyCategory.org_id == org_id)
    else:
        conditions.append(TaxonomyCategory.org_id.is_(None))

    if taxonomy_type:
        conditions.append(TaxonomyCategory.taxonomy_type == taxonomy_type)

    result = await db.execute(
        select(TaxonomyCategory)
        .where(and_(*conditions))
        .order_by(TaxonomyCategory.depth, TaxonomyCategory.sort_order, TaxonomyCategory.name)
    )
    all_cats = list(result.scalars().all())

    by_id: dict[int, dict] = {}
    roots: list[dict] = []

    for cat in all_cats:
        node = {
            "id": cat.id,
            "org_id": str(cat.org_id) if cat.org_id else None,
            "parent_id": cat.parent_id,
            "depth": cat.depth,
            "path": cat.path,
            "taxonomy_type": cat.taxonomy_type,
            "name": cat.name,
            "slug": cat.slug,
            "description": cat.description,
            "knowde_url": cat.knowde_url,
            "sort_order": cat.sort_order,
            "is_active": cat.is_active,
            "metadata": cat.metadata_,
            "created_at": cat.created_at,
            "updated_at": cat.updated_at,
            "children": [],
        }
        by_id[cat.id] = node

    for cat in all_cats:
        node = by_id[cat.id]
        if cat.parent_id and cat.parent_id in by_id:
            by_id[cat.parent_id]["children"].append(node)
        else:
            roots.append(node)

    return roots


# ── Clone Global Templates for Org ──


async def clone_defaults_for_org(
    db: AsyncSession, org_id: uuid.UUID
) -> int:
    """
    Copy all global template categories (org_id=NULL) to org-specific copies.
    Returns number of categories cloned.
    """
    result = await db.execute(
        select(TaxonomyCategory)
        .where(TaxonomyCategory.org_id.is_(None))
        .order_by(TaxonomyCategory.depth, TaxonomyCategory.sort_order)
    )
    templates = list(result.scalars().all())

    # Map old ID -> new ID for parent rewiring
    id_map: dict[int, int] = {}
    count = 0

    for tmpl in templates:
        new_parent_id = id_map.get(tmpl.parent_id) if tmpl.parent_id else None

        clone = TaxonomyCategory(
            org_id=org_id,
            parent_id=new_parent_id,
            depth=tmpl.depth,
            path="temp",
            taxonomy_type=tmpl.taxonomy_type,
            name=tmpl.name,
            slug=tmpl.slug,
            description=tmpl.description,
            knowde_url=tmpl.knowde_url,
            sort_order=tmpl.sort_order,
            is_active=True,
            metadata_=tmpl.metadata_ or {},
        )
        db.add(clone)
        await db.flush()

        id_map[tmpl.id] = clone.id

        # Rebuild materialized path
        if new_parent_id and new_parent_id in id_map:
            parent_clone_id = new_parent_id
            parent_clone = await db.get(TaxonomyCategory, parent_clone_id)
            clone.path = f"{parent_clone.path}/{clone.id}" if parent_clone else str(clone.id)
        else:
            clone.path = str(clone.id)

        count += 1

    await db.flush()
    return count


# ── Product-Category Assignment ──


async def assign_categories(
    db: AsyncSession,
    product_id: int,
    category_ids: list[int],
    primary_id: Optional[int] = None,
) -> list[ProductCategory]:
    # Remove existing assignments for this product
    await db.execute(
        delete(ProductCategory).where(ProductCategory.product_id == product_id)
    )
    await db.flush()

    assignments = []
    for cid in category_ids:
        pc = ProductCategory(
            product_id=product_id,
            category_id=cid,
            is_primary=(cid == primary_id) if primary_id else False,
        )
        db.add(pc)
        assignments.append(pc)

    await db.flush()
    return assignments


async def get_product_categories(
    db: AsyncSession, product_id: int
) -> list[TaxonomyCategory]:
    result = await db.execute(
        select(TaxonomyCategory)
        .join(ProductCategory, ProductCategory.category_id == TaxonomyCategory.id)
        .where(ProductCategory.product_id == product_id)
        .order_by(TaxonomyCategory.taxonomy_type, TaxonomyCategory.name)
    )
    return list(result.scalars().all())


async def get_products_in_category(
    db: AsyncSession, category_id: int
) -> list[int]:
    """Returns product IDs in a given category (including descendants)."""
    cat = await db.get(TaxonomyCategory, category_id)
    if not cat:
        return []

    # Get this category + all descendants
    result = await db.execute(
        select(TaxonomyCategory.id).where(
            (TaxonomyCategory.id == category_id)
            | (TaxonomyCategory.path.like(f"{cat.path}/%"))
        )
    )
    cat_ids = [row[0] for row in result.all()]

    result = await db.execute(
        select(ProductCategory.product_id)
        .where(ProductCategory.category_id.in_(cat_ids))
        .distinct()
    )
    return [row[0] for row in result.all()]


# ── Product Attributes ──


async def set_attribute(
    db: AsyncSession,
    product_id: int,
    org_id: Optional[uuid.UUID],
    attribute_group: str,
    attribute_key: str,
    attribute_value: str,
    value_json: Optional[dict] = None,
    source: str = "manual",
    confidence: Optional[float] = None,
) -> ProductAttribute:
    # Upsert: check if exists
    result = await db.execute(
        select(ProductAttribute).where(
            and_(
                ProductAttribute.product_id == product_id,
                ProductAttribute.org_id == org_id if org_id else ProductAttribute.org_id.is_(None),
                ProductAttribute.attribute_group == attribute_group,
                ProductAttribute.attribute_key == attribute_key,
            )
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.attribute_value = attribute_value
        existing.value_json = value_json
        existing.source = source
        existing.confidence = confidence
        await db.flush()
        return existing

    attr = ProductAttribute(
        product_id=product_id,
        org_id=org_id,
        attribute_group=attribute_group,
        attribute_key=attribute_key,
        attribute_value=attribute_value,
        value_json=value_json,
        source=source,
        confidence=confidence,
    )
    db.add(attr)
    await db.flush()
    return attr


async def get_product_attributes(
    db: AsyncSession,
    product_id: int,
    org_id: Optional[uuid.UUID] = None,
    group: Optional[str] = None,
) -> list[ProductAttribute]:
    conditions = [ProductAttribute.product_id == product_id]

    if org_id is not None:
        # Return both global and org-specific attributes
        conditions.append(
            (ProductAttribute.org_id == org_id) | (ProductAttribute.org_id.is_(None))
        )
    else:
        conditions.append(ProductAttribute.org_id.is_(None))

    if group:
        conditions.append(ProductAttribute.attribute_group == group)

    result = await db.execute(
        select(ProductAttribute)
        .where(and_(*conditions))
        .order_by(ProductAttribute.attribute_group, ProductAttribute.attribute_key)
    )
    return list(result.scalars().all())
