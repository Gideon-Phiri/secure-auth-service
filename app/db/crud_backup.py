import uuid
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.security import get_password_hash, verify_password
from app.db.models import User


async def get_user(session: AsyncSession, user_id: str) -> Optional[User]:
    """Get user by ID"""
    try:
        user_uuid = uuid.UUID(user_id)
        statement = select(User).where(User.id == user_uuid)
        result = await session.execute(statement)
        return result.scalars().first()
    except ValueError:
        return None


async def get_user_by_email(session: AsyncSession, email: str) -> Optional[User]:
    """Get user by email"""
    statement = select(User).where(User.email == email)
    result = await session.execute(statement)
    return result.scalars().first()


async def create_user(session: AsyncSession, email: str, password: str) -> User:
    """Create a new user"""
    # Check if user already exists
    existing_user = await get_user_by_email(session, email)
    if existing_user:
        raise ValueError("User with this email already exists")

    # Create new user
    hashed_password = get_password_hash(password)
    user = User(
        id=uuid.uuid4(),
        email=email,
        hashed_password=hashed_password,
        is_active=True,
        is_superuser=False,
    )

    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def authenticate_user(
    session: AsyncSession, email: str, password: str
) -> Optional[User]:
    """Authenticate user with email and password"""
    user = await get_user_by_email(session, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user
