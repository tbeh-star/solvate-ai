from __future__ import annotations

import math
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.modules.auth.service import get_user_by_auth_id
from app.modules.prices import service
from app.modules.prices.schemas import (
    InternalPriceCreate,
    InternalPriceOut,
    InternalPriceUpdate,
    MarketPriceOut,
    MarketPriceQuery,
    PaginatedResponse,
)

router = APIRouter(prefix="/prices", tags=["prices"])


@router.get("", response_model=PaginatedResponse)
async def list_prices(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    token_payload: dict[str, Any] = Depends(get_current_user),
) -> PaginatedResponse:
    user = await get_user_by_auth_id(db, token_payload["sub"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    items, total = await service.list_internal_prices(db, user.org_id, page, page_size)
    return PaginatedResponse(
        items=[InternalPriceOut.model_validate(i) for i in items],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size) if total > 0 else 0,
    )


@router.post("", response_model=InternalPriceOut, status_code=status.HTTP_201_CREATED)
async def create_price(
    data: InternalPriceCreate,
    db: AsyncSession = Depends(get_db),
    token_payload: dict[str, Any] = Depends(get_current_user),
) -> InternalPriceOut:
    user = await get_user_by_auth_id(db, token_payload["sub"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    price = await service.create_internal_price(db, data, user.org_id, user.id)
    return InternalPriceOut.model_validate(price)


@router.post("/bulk", response_model=list[InternalPriceOut], status_code=status.HTTP_201_CREATED)
async def create_prices_bulk(
    items: list[InternalPriceCreate],
    db: AsyncSession = Depends(get_db),
    token_payload: dict[str, Any] = Depends(get_current_user),
) -> list[InternalPriceOut]:
    user = await get_user_by_auth_id(db, token_payload["sub"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    prices = await service.create_internal_prices_bulk(db, items, user.org_id, user.id)
    return [InternalPriceOut.model_validate(p) for p in prices]


@router.put("/{price_id}", response_model=InternalPriceOut)
async def update_price(
    price_id: int,
    data: InternalPriceUpdate,
    db: AsyncSession = Depends(get_db),
    token_payload: dict[str, Any] = Depends(get_current_user),
) -> InternalPriceOut:
    user = await get_user_by_auth_id(db, token_payload["sub"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    price = await service.update_internal_price(db, price_id, user.org_id, data)
    if not price:
        raise HTTPException(status_code=404, detail="Price not found")
    return InternalPriceOut.model_validate(price)


@router.delete("/{price_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_price(
    price_id: int,
    db: AsyncSession = Depends(get_db),
    token_payload: dict[str, Any] = Depends(get_current_user),
) -> None:
    user = await get_user_by_auth_id(db, token_payload["sub"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    deleted = await service.delete_internal_price(db, price_id, user.org_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Price not found")


market_router = APIRouter(prefix="/market-data", tags=["market-data"])


@market_router.get("", response_model=PaginatedResponse)
async def list_market_prices(
    query: MarketPriceQuery = Depends(),
    db: AsyncSession = Depends(get_db),
    _: dict[str, Any] = Depends(get_current_user),
) -> PaginatedResponse:
    items, total = await service.list_market_prices(
        db,
        start_date=query.start_date,
        end_date=query.end_date,
        source=query.source,
        unit=query.unit,
        price_types=query.price_types,
        product=query.product,
        page=query.page,
        page_size=query.page_size,
    )
    return PaginatedResponse(
        items=[MarketPriceOut.model_validate(i) for i in items],
        total=total,
        page=query.page,
        page_size=query.page_size,
        pages=math.ceil(total / query.page_size) if total > 0 else 0,
    )


favorites_router = APIRouter(prefix="/users/me/favorites", tags=["favorites"])


@favorites_router.get("", response_model=list[int])
async def get_favorites(
    db: AsyncSession = Depends(get_db),
    token_payload: dict[str, Any] = Depends(get_current_user),
) -> list[int]:
    user = await get_user_by_auth_id(db, token_payload["sub"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return await service.get_user_favorites(db, user.id)


@favorites_router.post("/{product_id}", status_code=status.HTTP_201_CREATED)
async def add_favorite(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    token_payload: dict[str, Any] = Depends(get_current_user),
) -> dict[str, str]:
    user = await get_user_by_auth_id(db, token_payload["sub"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    added = await service.add_favorite(db, user.id, product_id)
    if not added:
        raise HTTPException(status_code=409, detail="Already a favorite")
    return {"status": "added"}


@favorites_router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite(
    product_id: int,
    db: AsyncSession = Depends(get_db),
    token_payload: dict[str, Any] = Depends(get_current_user),
) -> None:
    user = await get_user_by_auth_id(db, token_payload["sub"])
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    removed = await service.remove_favorite(db, user.id, product_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Favorite not found")
