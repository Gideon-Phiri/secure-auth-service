from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_user
from app.core.logging import SecurityEvent, log_security_event, log_user_action
from app.core.security import get_password_hash
from app.db.crud import create_user, get_user, get_user_by_email
from app.db.models import User
from app.db.session import get_session
from app.schemas.user import UserCreate, UserRead, UserUpdate

router = APIRouter()


async def get_current_admin_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Dependency to get current admin user"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )
    return current_user


@router.get("/me", response_model=UserRead)
async def read_me(current_user=Depends(get_current_user)):
    """Get current user profile"""
    return current_user


@router.put("/me", response_model=UserRead)
async def update_me(
    request: Request,
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Update current user profile"""
    client_ip = request.client.host if request.client else "unknown"

    # Update fields if provided
    if user_update.email is not None:
        # Check if email already exists
        existing_user = await get_user_by_email(session, user_update.email)
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
        current_user.email = user_update.email
        # Reset email verification if email changed
        current_user.email_verified = False

    if user_update.password is not None:
        current_user.hashed_password = get_password_hash(user_update.password)

    await session.commit()
    await session.refresh(current_user)

    # Log user update
    log_user_action("profile_update", str(current_user.id), ip_address=client_ip)

    return current_user


@router.delete("/me")
async def delete_me(
    request: Request,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Delete current user account"""
    client_ip = request.client.host if request.client else "unknown"

    await session.delete(current_user)
    await session.commit()

    # Log account deletion
    log_security_event(
        SecurityEvent(
            event_type="account_deletion",
            user_id=str(current_user.id),
            email=current_user.email,
            ip_address=client_ip,
            success=True,
            details="User deleted their own account",
        )
    )

    return {"message": "Account deleted successfully"}


# Admin endpoints
@router.get("/", response_model=List[UserRead])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    admin_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session),
):
    """List all users (admin only)"""
    statement = select(User).offset(skip).limit(limit)
    result = await session.execute(statement)
    users = result.scalars().all()

    # Log admin action (include IP if available)
    client_ip = None
    try:
        pass  # local import to avoid circular if any
        # admin_user dependency chain might not provide request directly; ignore if unavailable
    except Exception:
        pass
    log_user_action("list_users", str(admin_user.id), ip_address=client_ip)

    return users


@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user_admin(
    request: Request,
    user_in: UserCreate,
    is_superuser: bool = False,
    admin_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session),
):
    """Create a new user (admin only)"""
    client_ip = request.client.host if request.client else "unknown"

    try:
        new_user = await create_user(session, user_in.email, user_in.password)
        new_user.is_superuser = is_superuser
        new_user.email_verified = True  # Admin-created users are pre-verified
        await session.commit()
        await session.refresh(new_user)

        # Log admin action
        log_security_event(
            SecurityEvent(
                event_type="admin_user_creation",
                user_id=str(admin_user.id),
                ip_address=client_ip,
                success=True,
                details=f"Created user {new_user.email} (superuser: {is_superuser})",
            )
        )

        return new_user
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/{user_id}", response_model=UserRead)
async def get_user_by_id(
    user_id: str,
    admin_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session),
):
    """Get user by ID (admin only)"""
    user = await get_user(session, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Log admin action
    log_user_action("view_user", str(admin_user.id), user_id)

    return user


@router.put("/{user_id}", response_model=UserRead)
async def update_user_admin(
    user_id: str,
    user_update: UserUpdate,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session),
):
    """Update user (admin only)"""
    client_ip = request.client.host if request.client else "unknown"

    user = await get_user(session, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Update fields if provided
    if user_update.email is not None:
        # Check if email already exists
        existing_user = await get_user_by_email(session, user_update.email)
        if existing_user and existing_user.id != user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
        user.email = user_update.email

    if user_update.password is not None:
        user.hashed_password = get_password_hash(user_update.password)

    await session.commit()
    await session.refresh(user)

    # Log admin action
    log_security_event(
        SecurityEvent(
            event_type="admin_user_update",
            user_id=str(admin_user.id),
            ip_address=client_ip,
            success=True,
            details=f"Updated user {user.email}",
        )
    )

    return user


@router.post("/{user_id}/activate")
async def activate_user(
    user_id: str,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session),
):
    """Activate user account (admin only)"""
    client_ip = request.client.host if request.client else "unknown"

    user = await get_user(session, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    user.is_active = True
    user.failed_attempts = 0
    user.locked_until = None
    await session.commit()

    # Log admin action
    log_security_event(
        SecurityEvent(
            event_type="admin_user_activation",
            user_id=str(admin_user.id),
            ip_address=client_ip,
            success=True,
            details=f"Activated user {user.email}",
        )
    )

    return {"message": f"User {user.email} activated successfully"}


@router.post("/{user_id}/deactivate")
async def deactivate_user(
    user_id: str,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session),
):
    """Deactivate user account (admin only)"""
    client_ip = request.client.host if request.client else "unknown"

    user = await get_user(session, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Prevent deactivating the last superuser
    if user.is_superuser:
        statement = select(User).where(
            User.is_superuser is True, User.is_active is True
        )
        result = await session.execute(statement)
        active_admins = result.scalars().all()
        if len(active_admins) <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate the last active admin",
            )

    user.is_active = False
    await session.commit()

    # Log admin action
    log_security_event(
        SecurityEvent(
            event_type="admin_user_deactivation",
            user_id=str(admin_user.id),
            ip_address=client_ip,
            success=True,
            details=f"Deactivated user {user.email}",
        )
    )

    return {"message": f"User {user.email} deactivated successfully"}


@router.delete("/{user_id}")
async def delete_user_admin(
    user_id: str,
    request: Request,
    admin_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session),
):
    """Delete user (admin only)"""
    client_ip = request.client.host if request.client else "unknown"

    user = await get_user(session, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Prevent deleting the last superuser
    if user.is_superuser:
        statement = select(User).where(User.is_superuser is True)
        result = await session.execute(statement)
        all_admins = result.scalars().all()
        if len(all_admins) <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the last admin",
            )

    await session.delete(user)
    await session.commit()

    # Log admin action
    log_security_event(
        SecurityEvent(
            event_type="admin_user_deletion",
            user_id=str(admin_user.id),
            ip_address=client_ip,
            success=True,
            details=f"Deleted user {user.email}",
        )
    )

    return {"message": f"User {user.email} deleted successfully"}
