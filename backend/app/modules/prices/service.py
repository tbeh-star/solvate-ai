from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.prices.models import InternalPrice, MarketPrice, Product, UserFavorite
from app.modules.prices.schemas import InternalPriceCreate, InternalPriceUpdate


async def create_product(db: AsyncSession, data: dict) -> Product:
    product = Product(**data)
    db.add(product)
    await db.flush()
    await db.refresh(product)
    return product


async def get_or_create_product(db: AsyncSession, name: str) -> Product:
    result = await db.execute(
        select(Product).where(func.lower(Product.canonical_name) == name.lower())
    )
    product = result.scalar_one_or_none()
    if product:
        return product
    return await create_product(db, {"canonical_name": name})


async def list_internal_prices(
    db: AsyncSession,
    org_id: uuid.UUID,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[InternalPrice], int]:
    count_query = select(func.count()).select_from(InternalPrice).where(
        InternalPrice.org_id == org_id
    )
    total = (await db.execute(count_query)).scalar_one()

    query = (
        select(InternalPrice)
        .where(InternalPrice.org_id == org_id)
        .order_by(InternalPrice.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(query)
    return list(result.scalars().all()), total


async def get_internal_price(
    db: AsyncSession, price_id: int, org_id: uuid.UUID
) -> InternalPrice | None:
    result = await db.execute(
        select(InternalPrice).where(
            InternalPrice.id == price_id,
            InternalPrice.org_id == org_id,
        )
    )
    return result.scalar_one_or_none()


async def create_internal_price(
    db: AsyncSession,
    data: InternalPriceCreate,
    org_id: uuid.UUID,
    user_id: uuid.UUID,
) -> InternalPrice:
    price = InternalPrice(
        **data.model_dump(),
        org_id=org_id,
        created_by=user_id,
    )
    db.add(price)
    await db.flush()
    await db.refresh(price)
    return price


async def create_internal_prices_bulk(
    db: AsyncSession,
    items: list[InternalPriceCreate],
    org_id: uuid.UUID,
    user_id: uuid.UUID,
) -> list[InternalPrice]:
    prices = []
    for data in items:
        price = InternalPrice(
            **data.model_dump(),
            org_id=org_id,
            created_by=user_id,
        )
        db.add(price)
        prices.append(price)
    await db.flush()
    for p in prices:
        await db.refresh(p)
    return prices


async def update_internal_price(
    db: AsyncSession,
    price_id: int,
    org_id: uuid.UUID,
    data: InternalPriceUpdate,
) -> InternalPrice | None:
    price = await get_internal_price(db, price_id, org_id)
    if not price:
        return None
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(price, key, value)
    await db.flush()
    await db.refresh(price)
    return price


async def delete_internal_price(
    db: AsyncSession, price_id: int, org_id: uuid.UUID
) -> bool:
    price = await get_internal_price(db, price_id, org_id)
    if not price:
        return False
    await db.delete(price)
    await db.flush()
    return True


async def list_market_prices(
    db: AsyncSession,
    start_date: datetime,
    end_date: datetime,
    source: str | None = None,
    unit: str | None = None,
    price_types: list[str] | None = None,
    product: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> tuple[list[MarketPrice], int]:
    base = select(MarketPrice).where(
        MarketPrice.time >= start_date,
        MarketPrice.time <= end_date,
    )
    if source:
        base = base.where(MarketPrice.source == source)
    if unit:
        base = base.where(MarketPrice.price_unit == unit)
    if price_types:
        base = base.where(MarketPrice.price_type.in_(price_types))
    if product:
        base = base.where(func.lower(MarketPrice.product_raw).contains(product.lower()))

    count_query = select(func.count()).select_from(base.subquery())
    total = (await db.execute(count_query)).scalar_one()

    query = base.order_by(MarketPrice.time.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return list(result.scalars().all()), total


async def get_user_favorites(db: AsyncSession, user_id: uuid.UUID) -> list[int]:
    result = await db.execute(
        select(UserFavorite.product_id).where(UserFavorite.user_id == user_id)
    )
    return list(result.scalars().all())


async def add_favorite(db: AsyncSession, user_id: uuid.UUID, product_id: int) -> bool:
    existing = await db.execute(
        select(UserFavorite).where(
            UserFavorite.user_id == user_id,
            UserFavorite.product_id == product_id,
        )
    )
    if existing.scalar_one_or_none():
        return False
    fav = UserFavorite(user_id=user_id, product_id=product_id)
    db.add(fav)
    await db.flush()
    return True


async def remove_favorite(db: AsyncSession, user_id: uuid.UUID, product_id: int) -> bool:
    result = await db.execute(
        select(UserFavorite).where(
            UserFavorite.user_id == user_id,
            UserFavorite.product_id == product_id,
        )
    )
    fav = result.scalar_one_or_none()
    if not fav:
        return False
    await db.delete(fav)
    await db.flush()
    return True
