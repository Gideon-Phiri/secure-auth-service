import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserRead(BaseModel):
    id: uuid.UUID
    email: EmailStr
    is_active: bool
    is_superuser: bool
    email_verified: bool
    created_at: datetime


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    password: Optional[str] = None
