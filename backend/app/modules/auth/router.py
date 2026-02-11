from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import get_current_user
from app.modules.auth.schemas import UserOut
from app.modules.auth.service import get_or_create_user, get_user_by_auth_id

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
async def get_me(
    db: AsyncSession = Depends(get_db),
    token_payload: dict[str, Any] = Depends(get_current_user),
) -> UserOut:
    # Auto-provision user on first login
    user = await get_user_by_auth_id(db, token_payload["sub"])
    if not user:
        email = token_payload.get("email") or token_payload.get(
            "https://priceintelligence.io/email", ""
        )
        name = token_payload.get("name") or token_payload.get(
            "https://priceintelligence.io/name"
        )
        if not email:
            raise HTTPException(status_code=400, detail="Email not found in token")
        user = await get_or_create_user(db, token_payload["sub"], email, name)

    return UserOut.model_validate(user)
