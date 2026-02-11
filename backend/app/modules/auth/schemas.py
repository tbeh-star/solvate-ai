from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class OrganizationCreate(BaseModel):
    name: str
    slug: str


class OrganizationOut(BaseModel):
    id: UUID
    name: str
    slug: str
    created_at: datetime

    model_config = {"from_attributes": True}


class UserOut(BaseModel):
    id: UUID
    org_id: UUID
    email: str
    name: str | None = None
    role: str
    created_at: datetime

    model_config = {"from_attributes": True}
