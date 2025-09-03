import pytest
import uuid
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_password_complexity_validation(client: AsyncClient):
    """Test password complexity requirements"""
    test_cases = [
        ("weak", 400, "Password must be at least 8 characters long"),
        ("nocaps123!", 400, "Password must contain at least one uppercase letter"),
        ("NOUPPER123!", 400, "Password must contain at least one lowercase letter"),
        ("NoNumbers!", 400, "Password must contain at least one digit"),
        ("NoSpecial123", 400, "Password must contain at least one special character"),
        ("ValidPass123!", 201, None),  # This should succeed
    ]
    
    for i, (password, expected_status, expected_error) in enumerate(test_cases):
        email = f"test{i}_{uuid.uuid4().hex[:8]}@example.com"
        response = await client.post("/auth/register", json={"email": email, "password": password})
        assert response.status_code == expected_status, f"Failed for password: {password}. Got status: {response.status_code}, Response: {response.text}"
        
        if expected_error:
            assert expected_error in response.json()["detail"]

@pytest.mark.asyncio
async def test_email_verification_required_for_login(client: AsyncClient):
    """Test that unverified users cannot login"""
    email = f"unverified_{uuid.uuid4().hex[:8]}@example.com"
    password = "ValidPass123!"
    
    # Register user but don't verify email
    reg_response = await client.post("/auth/register", json={"email": email, "password": password})
    assert reg_response.status_code == 201
    
    # Try to login without verification  
    login_response = await client.post("/auth/login", json={"email": email, "password": password})
    assert login_response.status_code == 401
    assert "Email not verified" in login_response.json()["detail"]

@pytest.mark.asyncio
async def test_security_headers_present(client: AsyncClient):
    """Test that security headers are present in responses"""
    response = await client.get("/health")
    
    # Check for security headers
    assert "X-Content-Type-Options" in response.headers
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert "X-Frame-Options" in response.headers
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "Content-Security-Policy" in response.headers
    assert "X-Request-ID" in response.headers
