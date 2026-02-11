from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.modules.auth.service import get_user_by_auth_id
from app.modules.taxonomy import service
from app.modules.taxonomy.schemas import (
    AttributeBulkCreate,
    AttributeCreate,
    AttributeOut,
    CategoryCreate,
    CategoryOut,
    CategoryUpdate,
    HSCodeMappingCreate,
    HSCodeMappingOut,
    ProductCategoryAssign,
    TaxonomyTreeOut,
)

router = APIRouter(prefix="/taxonomy", tags=["taxonomy"])


async def _resolve_org_id(
    db: AsyncSession, token_payload: dict[str, Any]
) -> str:
    user = await get_user_by_auth_id(db, token_payload["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user.org_id


# ── Tree & Category Browsing ──


@router.get("/tree")
async def get_taxonomy_tree(
    global_only: bool = Query(False, description="Show global templates only"),
    db: AsyncSession = Depends(get_db),
    token_payload: dict[str, Any] = Depends(get_current_user),
) -> TaxonomyTreeOut:
    org_id = None if global_only else await _resolve_org_id(db, token_payload)

    industries = await service.build_tree(db, org_id, taxonomy_type="industry")
    product_families = await service.build_tree(db, org_id, taxonomy_type="product_family")

    return TaxonomyTreeOut(industries=industries, product_families=product_families)


@router.get("/industries", response_model=list[CategoryOut])
async def get_industries(
    db: AsyncSession = Depends(get_db),
    token_payload: dict[str, Any] = Depends(get_current_user),
) -> list[CategoryOut]:
    org_id = await _resolve_org_id(db, token_payload)
    cats = await service.get_root_categories(db, org_id, taxonomy_type="industry")
    return [CategoryOut.model_validate(c) for c in cats]


@router.get("/product-families", response_model=list[CategoryOut])
async def get_product_families(
    db: AsyncSession = Depends(get_db),
    token_payload: dict[str, Any] = Depends(get_current_user),
) -> list[CategoryOut]:
    org_id = await _resolve_org_id(db, token_payload)
    cats = await service.get_root_categories(db, org_id, taxonomy_type="product_family")
    return [CategoryOut.model_validate(c) for c in cats]


@router.get("/categories/{category_id}", response_model=CategoryOut)
async def get_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    token_payload: dict[str, Any] = Depends(get_current_user),
) -> CategoryOut:
    cat = await service.get_category(db, category_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    return CategoryOut.model_validate(cat)


@router.get("/categories/{category_id}/children", response_model=list[CategoryOut])
async def get_category_children(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    token_payload: dict[str, Any] = Depends(get_current_user),
) -> list[CategoryOut]:
    children = await service.get_children(db, category_id)
    return [CategoryOut.model_validate(c) for c in children]


@router.get("/categories/{category_id}/products")
async def get_category_products(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    token_payload: dict[str, Any] = Depends(get_current_user),
) -> dict[str, list[int]]:
    product_ids = await service.get_products_in_category(db, category_id)
    return {"product_ids": product_ids}


# ── Category CRUD (org-specific) ──


@router.post("/categories", response_model=CategoryOut, status_code=201)
async def create_category(
    body: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    token_payload: dict[str, Any] = Depends(get_current_user),
) -> CategoryOut:
    org_id = await _resolve_org_id(db, token_payload)
    cat = await service.create_category(
        db,
        org_id=org_id,
        name=body.name,
        taxonomy_type=body.taxonomy_type,
        parent_id=body.parent_id,
        slug=body.slug,
        description=body.description,
        knowde_url=body.knowde_url,
        sort_order=body.sort_order,
        metadata=body.metadata,
    )
    return CategoryOut.model_validate(cat)


@router.put("/categories/{category_id}", response_model=CategoryOut)
async def update_category(
    category_id: int,
    body: CategoryUpdate,
    db: AsyncSession = Depends(get_db),
    token_payload: dict[str, Any] = Depends(get_current_user),
) -> CategoryOut:
    cat = await service.update_category(
        db,
        category_id,
        name=body.name,
        description=body.description,
        sort_order=body.sort_order,
        is_active=body.is_active,
    )
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    return CategoryOut.model_validate(cat)


@router.delete("/categories/{category_id}", status_code=204)
async def delete_category(
    category_id: int,
    db: AsyncSession = Depends(get_db),
    token_payload: dict[str, Any] = Depends(get_current_user),
) -> None:
    cat = await service.deactivate_category(db, category_id)
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")


# ── Clone Global Defaults ──


@router.post("/clone-defaults")
async def clone_defaults(
    db: AsyncSession = Depends(get_db),
    token_payload: dict[str, Any] = Depends(get_current_user),
) -> dict[str, int]:
    org_id = await _resolve_org_id(db, token_payload)
    count = await service.clone_defaults_for_org(db, org_id)
    return {"cloned_categories": count}


# ── Product-Category Assignment ──


@router.get("/products/{product_id}/categories", response_model=list[CategoryOut])
async def get_product_categories(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    token_payload: dict[str, Any] = Depends(get_current_user),
) -> list[CategoryOut]:
    cats = await service.get_product_categories(db, product_id)
    return [CategoryOut.model_validate(c) for c in cats]


@router.post("/products/{product_id}/categories")
async def assign_product_categories(
    product_id: int,
    body: ProductCategoryAssign,
    db: AsyncSession = Depends(get_db),
    token_payload: dict[str, Any] = Depends(get_current_user),
) -> dict[str, str]:
    await service.assign_categories(
        db, product_id, body.category_ids, primary_id=body.set_primary_id
    )
    return {"status": "ok", "assigned": str(len(body.category_ids))}


# ── Product Attributes ──


@router.get("/products/{product_id}/attributes", response_model=list[AttributeOut])
async def get_product_attributes(
    product_id: int,
    group: Optional[str] = Query(None, description="Filter by attribute group"),
    db: AsyncSession = Depends(get_db),
    token_payload: dict[str, Any] = Depends(get_current_user),
) -> list[AttributeOut]:
    org_id = await _resolve_org_id(db, token_payload)
    attrs = await service.get_product_attributes(db, product_id, org_id=org_id, group=group)
    return [AttributeOut.model_validate(a) for a in attrs]


@router.post("/products/{product_id}/attributes", response_model=AttributeOut, status_code=201)
async def set_product_attribute(
    product_id: int,
    body: AttributeCreate,
    db: AsyncSession = Depends(get_db),
    token_payload: dict[str, Any] = Depends(get_current_user),
) -> AttributeOut:
    org_id = await _resolve_org_id(db, token_payload)
    attr = await service.set_attribute(
        db,
        product_id=product_id,
        org_id=org_id,
        attribute_group=body.attribute_group,
        attribute_key=body.attribute_key,
        attribute_value=body.attribute_value,
        value_json=body.value_json,
        source=body.source,
        confidence=body.confidence,
    )
    return AttributeOut.model_validate(attr)


@router.post("/products/{product_id}/attributes/bulk", status_code=201)
async def set_product_attributes_bulk(
    product_id: int,
    body: AttributeBulkCreate,
    db: AsyncSession = Depends(get_db),
    token_payload: dict[str, Any] = Depends(get_current_user),
) -> dict[str, int]:
    org_id = await _resolve_org_id(db, token_payload)
    for attr in body.attributes:
        await service.set_attribute(
            db,
            product_id=product_id,
            org_id=org_id,
            attribute_group=attr.attribute_group,
            attribute_key=attr.attribute_key,
            attribute_value=attr.attribute_value,
            value_json=attr.value_json,
            source=attr.source,
            confidence=attr.confidence,
        )
    return {"created": len(body.attributes)}
