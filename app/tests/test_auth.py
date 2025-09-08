import anyio


def test_register_and_verify_email():
    """Test user registration and email verification"""

    async def async_test():
        # Setup database
        from sqlmodel import SQLModel

        from app.tests.conftest import engine_test

        async with engine_test.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

        try:
            # Reset app state and overrides for each test
            from httpx import AsyncClient

            from app.db.session import get_session
            from app.main import app
            from app.tests.conftest import get_test_limiter, override_get_session

            app.dependency_overrides.clear()
            app.dependency_overrides[get_session] = override_get_session
            app.state.limiter = get_test_limiter()

            async with AsyncClient(app=app, base_url="http://testserver") as client:
                email = "integrationtest@example.com"
                password = "StrongPassw0rd!"
                # Register user
                r = await client.post(
                    "/auth/register", json={"email": email, "password": password}
                )
                assert r.status_code == 201
                # Extract token from console output (simulate)
                # In real test, you would mock send_verification_email and capture the token
                # For now, fetch user from DB and get token
                from app.db.models import User
                from app.tests.conftest import AsyncSessionLocal  # type: ignore

                async with AsyncSessionLocal() as session:  # type: ignore
                    from sqlmodel import select

                    result = await session.execute(
                        select(User).where(User.email == email)
                    )
                    user = result.scalar_one_or_none()
                    assert user is not None
                    token = user.email_verification_token
                # Verify email
                r2 = await client.get(f"/auth/verify-email?token={token}")
                assert r2.status_code == 200
                assert "Email verified successfully" in r2.text
        finally:
            # Cleanup database
            async with engine_test.begin() as conn:
                await conn.run_sync(SQLModel.metadata.drop_all)

    anyio.run(async_test)


def test_login_and_lockout():
    """Test login attempts and account lockout"""

    async def async_test():
        # Reset app state and overrides for each test
        from httpx import AsyncClient

        from app.db.session import get_session
        from app.main import app
        from app.tests.conftest import get_test_limiter, override_get_session

        app.dependency_overrides.clear()
        app.dependency_overrides[get_session] = override_get_session
        app.state.limiter = get_test_limiter()

        async with AsyncClient(app=app, base_url="http://testserver") as client:
            email = "lockouttest@example.com"
            password = "StrongPassw0rd!"
            # Register and verify
            r = await client.post(
                "/auth/register", json={"email": email, "password": password}
            )
            assert r.status_code == 201
            from app.db.models import User
            from app.tests.conftest import AsyncSessionLocal  # type: ignore

            async with AsyncSessionLocal() as session:  # type: ignore
                from sqlmodel import select

                result = await session.execute(select(User).where(User.email == email))
                user = result.scalar_one_or_none()
                token = user.email_verification_token
            await client.get(f"/auth/verify-email?token={token}")
            # Fail login 5 times
            for _ in range(5):
                r_fail = await client.post(
                    "/auth/login", json={"email": email, "password": "WrongPass!"}
                )
                assert r_fail.status_code == 401
            # 6th attempt should be locked out
            r_locked = await client.post(
                "/auth/login", json={"email": email, "password": password}
            )
            assert r_locked.status_code == 403
            assert "Account locked" in r_locked.text

    anyio.run(async_test)


def test_rate_limiting():
    """Test rate limiting for login endpoint"""

    async def async_test():
        # Reset app state and overrides for each test
        from httpx import AsyncClient

        from app.db.session import get_session
        from app.main import app
        from app.tests.conftest import get_test_limiter, override_get_session

        app.dependency_overrides.clear()
        app.dependency_overrides[get_session] = override_get_session
        app.state.limiter = get_test_limiter()

        async with AsyncClient(app=app, base_url="http://testserver") as client:
            email = "ratelimit@example.com"
            password = "StrongPassw0rd!"
            from app.core.rate_limit import (
                disable_test_rate_limits,
                enable_test_rate_limits,
            )

            enable_test_rate_limits()
            # Register and verify
            r = await client.post(
                "/auth/register", json={"email": email, "password": password}
            )
            assert r.status_code == 201
            from app.db.models import User
            from app.tests.conftest import AsyncSessionLocal  # type: ignore

            async with AsyncSessionLocal() as session:  # type: ignore
                from sqlmodel import select

                result = await session.execute(select(User).where(User.email == email))
                user = result.scalar_one_or_none()
                token = user.email_verification_token
            await client.get(f"/auth/verify-email?token={token}")
            # Exceed login rate limit
            try:
                for _ in range(11):
                    await client.post(
                        "/auth/login", json={"email": email, "password": password}
                    )
                r_limited = await client.post(
                    "/auth/login", json={"email": email, "password": password}
                )
                assert r_limited.status_code == 429
            finally:
                disable_test_rate_limits()

    anyio.run(async_test)
