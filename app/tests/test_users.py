import pytest
from httpx import AsyncClient
from app.db.models import User
from app.tests.conftest import AsyncSessionLocal
from sqlmodel import select
from app.core.security import create_access_token

@pytest.mark.asyncio
async def test_update_profile(client: AsyncClient, verified_user):
    """Test user profile update"""
    # Create access token for the user
    access_token = create_access_token(subject=str(verified_user.id))
    
    # Update profile
    new_email = "newprofile@example.com"
    update_response = await client.put(
        "/users/me",
        json={"email": new_email},
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert update_response.status_code == 200
    assert update_response.json()["email"] == new_email
    assert update_response.json()["email_verified"] == False  # Reset on email change

@pytest.mark.asyncio
async def test_delete_own_account(client: AsyncClient, verified_user):
    """Test user can delete their own account"""
    # Create access token
    access_token = create_access_token(subject=str(verified_user.id))
    
    # Delete account
    delete_response = await client.delete(
        "/users/me",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert delete_response.status_code == 200
    assert "deleted successfully" in delete_response.json()["message"]

@pytest.mark.asyncio
async def test_admin_list_users(client: AsyncClient, admin_user):
    """Test admin can list all users"""
    # Login as admin
    access_token = create_access_token(subject=str(admin_user.id))
    
    # List users
    list_response = await client.get(
        "/users/",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert list_response.status_code == 200
    assert isinstance(list_response.json(), list)

@pytest.mark.asyncio
async def test_admin_create_user(client: AsyncClient, admin_user):
    """Test admin can create users"""
    access_token = create_access_token(subject=str(admin_user.id))
    
    # Create user
    new_user_email = "newuser@example.com"
    create_response = await client.post(
        "/users/",
        json={"email": new_user_email, "password": "NewUserPass123!"},
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert create_response.status_code == 201
    assert create_response.json()["email"] == new_user_email
    assert create_response.json()["email_verified"] == True  # Admin-created users are pre-verified

@pytest.mark.asyncio
async def test_non_admin_cannot_access_admin_endpoints(client: AsyncClient, verified_user):
    """Test regular users cannot access admin endpoints"""
    access_token = create_access_token(subject=str(verified_user.id))
    
    # Try to access admin endpoint
    list_response = await client.get(
        "/users/",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    assert list_response.status_code == 403
    assert "Not enough permissions" in list_response.json()["detail"]

@pytest.mark.asyncio
async def test_admin_activate_deactivate_user(client: AsyncClient, admin_user, verified_user):
    """Test admin can activate/deactivate users"""
    admin_token = create_access_token(subject=str(admin_user.id))
    user_id = str(verified_user.id)
    
    # Deactivate user
    deactivate_response = await client.post(
        f"/users/{user_id}/deactivate",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert deactivate_response.status_code == 200
    assert "deactivated successfully" in deactivate_response.json()["message"]
    
    # Activate user
    activate_response = await client.post(
        f"/users/{user_id}/activate",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert activate_response.status_code == 200
    assert "activated successfully" in activate_response.json()["message"]


