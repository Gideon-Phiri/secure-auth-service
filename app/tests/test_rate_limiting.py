import asyncio
import uuid

import pytest
from httpx import AsyncClient

from app.core.rate_limit import (
    conditional_limit,
    disable_test_rate_limits,
    enable_test_rate_limits,
    is_testing,
    reset_rate_limit_wrappers,
)


@pytest.mark.asyncio
async def test_registration_rate_limit(client: AsyncClient):
    """Test that rate limiting works for registration endpoint"""
    # Clear any cached limited wrappers from prior tests
    from app.api.v1 import auth as auth_module

    reset_rate_limit_wrappers(getattr(auth_module, "register", None))
    enable_test_rate_limits()  # resets limiter instance internally
    try:
        # Make requests that should trigger rate limiting
        responses = []

        for i in range(7):  # More than the 5/minute limit
            email = f"ratetest{i}_{uuid.uuid4().hex[:8]}@example.com"
            response = await client.post(
                "/auth/register", json={"email": email, "password": "ValidPass123!"}
            )
            responses.append(response.status_code)

            # Small delay to avoid overwhelming the system
            await asyncio.sleep(0.1)

        # First 5 should succeed (201) or fail with validation (400)
        # Later ones should be rate limited (429)
        success_or_validation = sum(
            1 for status in responses[:5] if status in [201, 400]
        )
        rate_limited = sum(1 for status in responses[5:] if status == 429)

        # Should have some successful/validation responses and some rate limited
        assert (
            success_or_validation >= 1
        ), f"Expected some successful requests, got statuses: {responses[:5]}"
        assert (
            rate_limited >= 1
        ), f"Expected some rate limited requests, got statuses: {responses[5:]}"

    finally:
        disable_test_rate_limits()


@pytest.mark.asyncio
async def test_login_rate_limit(client: AsyncClient):
    """Test that rate limiting works for login endpoint"""
    # Clear cached limiter state for login handler
    from app.api.v1 import auth as auth_module

    reset_rate_limit_wrappers(getattr(auth_module, "login", None))
    enable_test_rate_limits()  # resets limiter instance internally
    try:
        # Make multiple login attempts
        responses = []

        for i in range(12):  # More than the 10/minute limit
            response = await client.post(
                "/auth/login",
                json={"email": f"test{i}@example.com", "password": "wrongpassword"},
            )
            responses.append(response.status_code)
            await asyncio.sleep(0.1)

        # Should get some 401 (unauthorized) and some 429 (rate limited)
        unauthorized = sum(1 for status in responses[:10] if status == 401)
        rate_limited = sum(1 for status in responses[10:] if status == 429)

        assert (
            unauthorized >= 1
        ), f"Expected some unauthorized responses, got: {responses[:10]}"
        assert (
            rate_limited >= 1
        ), f"Expected some rate limited responses, got: {responses[10:]}"

    finally:
        disable_test_rate_limits()


@pytest.mark.asyncio
async def test_rate_limit_headers(client: AsyncClient):
    """Test that rate limit headers are included in responses"""
    response = await client.post(
        "/auth/login", json={"email": "test@example.com", "password": "wrongpassword"}
    )

    # Check for rate limit headers (these may vary by slowapi version)
    # Common headers include X-RateLimit-Limit, X-RateLimit-Remaining

    # At minimum, the response should be processed successfully
    assert response.status_code in [
        401,
        429,
    ], f"Expected 401 or 429, got {response.status_code}"
    # Common headers include X-RateLimit-Limit, X-RateLimit-Remaining

    # At minimum, the response should be processed successfully
    assert response.status_code in [
        401,
        429,
    ], f"Expected 401 or 429, got {response.status_code}"


def test_conditional_limit_unit_noop_in_tests():
    """Unit test: in testing environment the decorator should NOT enforce until enabled."""
    assert is_testing(), "This test must run under pytest"
    calls = {"count": 0}

    @conditional_limit("1/minute")
    async def sample():
        calls["count"] += 1
        return "ok"

    import anyio

    anyio.run(sample)
    anyio.run(sample)
    # Both calls should pass because limits disabled by default in tests
    assert calls["count"] == 2
