from typing import Optional
from datetime import datetime, timezone
from sqlmodel import SQLModel, Field
import uuid

def utc_now():
    return datetime.now(timezone.utc)

class User(SQLModel, table=True):
    id: Optional[uuid.UUID] = Field(default=None, primary_key=True)
    email: str = Field(index=True, nullable=False, unique=True)
    hashed_password: str
    is_active: bool = True
    is_superuser: bool = False
    failed_attempts: int = 0
    locked_until: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
