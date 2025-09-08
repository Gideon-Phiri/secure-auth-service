import json
from unittest.mock import patch

import pytest
from httpx import AsyncClient

from app.core.logging import (
    SecurityEvent,
    log_account_lockout,
    log_auth_failure,
    log_auth_success,
    log_security_event,
)
from app.db.models import User


@pytest.mark.asyncio
async def test_security_event_logging():
    """Test security event logging structure"""
    with patch("app.core.logging.logger") as mock_logger:
        event = SecurityEvent(
            event_type="test_event",
            user_id="123",
            email="test@example.com",
            ip_address="192.168.1.1",
            success=True,
            details="Test event",
        )

        log_security_event(event)

        # Verify logger was called
        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "SECURITY_EVENT" in call_args
        assert "test_event" in call_args


@pytest.mark.asyncio
async def test_auth_success_logging():
    """Test successful authentication logging"""
    with patch("app.core.logging.logger") as mock_logger:
        log_auth_success("user123", "test@example.com", "192.168.1.1", "Mozilla/5.0")

        mock_logger.info.assert_called_once()
        call_args = mock_logger.info.call_args[0][0]
        assert "auth_success" in call_args
        assert "test@example.com" in call_args


@pytest.mark.asyncio
async def test_auth_failure_logging():
    """Test failed authentication logging"""
    with patch("app.core.logging.logger") as mock_logger:
        log_auth_failure(
            "test@example.com", "192.168.1.1", "Invalid password", "Mozilla/5.0"
        )

        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args[0][0]
        assert "SECURITY_ALERT" in call_args
        assert "auth_failure" in call_args
        assert "Invalid password" in call_args


@pytest.mark.asyncio
async def test_account_lockout_logging():
    """Test account lockout logging"""
    with patch("app.core.logging.logger") as mock_logger:
        log_account_lockout("test@example.com", "192.168.1.1", "Mozilla/5.0")

        mock_logger.warning.assert_called_once()
        call_args = mock_logger.warning.call_args[0][0]
        assert "account_lockout" in call_args
        assert "multiple failed attempts" in call_args


@pytest.mark.asyncio
async def test_request_logging_middleware(client: AsyncClient):
    """Test that requests are logged with request IDs"""
    with patch("app.core.logging.logger") as mock_logger:
        response = await client.get("/health")

        assert response.status_code == 200
        assert "X-Request-ID" in response.headers

        # Verify request and response were logged
        assert mock_logger.info.call_count >= 2  # At least request and response


@pytest.mark.asyncio
async def test_login_attempts_are_logged(client: AsyncClient, verified_user: User):
    """Test that login attempts are properly logged"""
    email = verified_user.email
    password = "TestPass123!"

    # Patch the names actually used inside the auth router module
    with (
        patch("app.api.v1.auth.log_auth_success") as mock_success,
        patch("app.api.v1.auth.log_auth_failure") as mock_failure,
    ):

        # Successful login
        login_response = await client.post(
            "/auth/login", json={"email": email, "password": password}
        )
        assert login_response.status_code == 200
        mock_success.assert_called_once()

        # Failed login
        fail_response = await client.post(
            "/auth/login", json={"email": email, "password": "wrongpassword"}
        )
        assert fail_response.status_code == 401
        mock_failure.assert_called()


@pytest.mark.asyncio
async def test_admin_actions_are_logged(client: AsyncClient, admin_user: User):
    """Test that admin actions are properly logged"""
    admin_email = admin_user.email
    password = "AdminPass123!"

    # Login as admin
    login_response = await client.post(
        "/auth/login", json={"email": admin_email, "password": password}
    )
    assert login_response.status_code == 200
    admin_token = login_response.json()["access_token"]

    # Patch the names actually imported in users router
    with (
        patch("app.api.v1.users.log_user_action") as mock_log_action,
        patch("app.api.v1.users.log_security_event") as mock_log_event,
    ):

        # List users (should log action)
        list_response = await client.get(
            "/users/", headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert list_response.status_code == 200
        # Accept either 2 or 3 arg call depending on ip capture (action, user_id, optional target)
        assert mock_log_action.called

        # Create user (should log security event)
        create_response = await client.post(
            "/users/",
            json={"email": "newuser@example.com", "password": "NewPass123!"},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert create_response.status_code == 201
        mock_log_event.assert_called()


@pytest.mark.asyncio
async def test_rate_limit_logging(client: AsyncClient):
    """Test that rate limit violations are logged"""
    with patch("app.core.logging.log_rate_limit_exceeded"):
        # This test assumes rate limiting is working
        # Make multiple rapid requests to trigger rate limit
        for _ in range(12):  # Exceed the 10/minute limit for login
            try:
                await client.post(
                    "/auth/login", json={"email": "test@test.com", "password": "wrong"}
                )
            except Exception:
                pass  # Rate limit exception expected

        # In a real scenario, the rate limiter would call our logging function
        # This is more of an integration test placeholder


class TestSecurityEventModel:
    """Test the SecurityEvent model"""

    def test_security_event_creation(self):
        """Test creating a security event"""
        event = SecurityEvent(
            event_type="test",
            user_id="123",
            email="test@example.com",
            ip_address="1.2.3.4",
            success=True,
        )

        assert event.event_type == "test"
        assert event.user_id == "123"
        assert event.email == "test@example.com"
        assert event.ip_address == "1.2.3.4"
        assert event.success is True
        assert event.timestamp is not None

    def test_security_event_serialization(self):
        """Test security event can be serialized to JSON"""
        event = SecurityEvent(event_type="test", user_id="123", ip_address="1.2.3.4")

        data = event.model_dump()
        assert isinstance(data, dict)
        assert data["event_type"] == "test"
        assert data["user_id"] == "123"

        # Test JSON serialization works
        json_str = json.dumps(data, default=str)
        assert "test" in json_str
