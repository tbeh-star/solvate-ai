from __future__ import annotations

import re
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import Organization, User


def _slugify(name: str) -> str:
    slug = name.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    return slug


async def get_user_by_auth_id(db: AsyncSession, auth_provider_id: str) -> User | None:
    result = await db.execute(
        select(User).where(User.auth_provider_id == auth_provider_id)
    )
    return result.scalar_one_or_none()


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(
        select(User).where(User.email == email)
    )
    return result.scalar_one_or_none()


async def get_or_create_user(
    db: AsyncSession,
    auth_provider_id: str,
    email: str,
    name: str | None = None,
) -> User:
    user = await get_user_by_auth_id(db, auth_provider_id)
    if user:
        return user

    # Create a personal organization for the user
    org = Organization(
        name=f"{name or email}'s Organization",
        slug=_slugify(email.split("@")[0]) + "-" + uuid.uuid4().hex[:6],
    )
    db.add(org)
    await db.flush()

    user = User(
        org_id=org.id,
        auth_provider_id=auth_provider_id,
        email=email,
        name=name,
        role="admin",
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user
