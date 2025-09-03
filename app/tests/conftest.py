import asyncio
import pytest
import uuid
from httpx import AsyncClient
from sqlmodel import SQLModel, create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.db.models import User
from app.core.middleware import HTTPSRedirectMiddleware
from slowapi.util import get_remote_address
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
import uuid

# Disable HTTPS redirect for all tests
app.user_middleware = [
    m for m in app.user_middleware if m.cls is not HTTPSRedirectMiddleware
]

# Ensure rate limit exception handler & middleware registered once
if not any(h[0] == RateLimitExceeded for h in getattr(app, 'exception_handlers', {}).items()):
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
if not any(m.cls is SlowAPIMiddleware for m in app.user_middleware):
    app.add_middleware(SlowAPIMiddleware)

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
engine_test = create_async_engine(TEST_DATABASE_URL, future=True)
AsyncSessionLocal = sessionmaker(engine_test, class_=AsyncSession, expire_on_commit=False)

async def override_get_session():
    async with AsyncSessionLocal() as session:
        yield session

# Mock rate limiter for tests - use unique IDs per test
def get_test_remote_address(request):
    return f"test-{uuid.uuid4()}"  # Unique per request to avoid rate limits

def get_test_limiter():
    return Limiter(key_func=get_test_remote_address, default_limits=["10000/minute"])

app.state.limiter = get_test_limiter()

@pytest.fixture(scope="function", autouse=True)
async def prepare_db():
    async with engine_test.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)

@pytest.fixture(scope="function")
async def client():
    # Reset app state and overrides for each test
    app.dependency_overrides.clear()
    from app.db.session import get_session
    app.dependency_overrides[get_session] = override_get_session

    # Use a fresh (permissive) limiter for each test
    app.state.limiter = get_test_limiter()

    async with AsyncClient(app=app, base_url="http://testserver") as c:
        yield c

@pytest.fixture
async def verified_user():
    """Helper fixture to create a verified user"""
    async with AsyncSessionLocal() as session:
        from app.core.security import get_password_hash
        user = User(
            id=uuid.uuid4(),
            email="testuser@example.com",
            hashed_password=get_password_hash("TestPass123!"),
            is_active=True,
            is_superuser=False,
            email_verified=True
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

@pytest.fixture
async def admin_user():
    """Helper fixture to create an admin user"""
    async with AsyncSessionLocal() as session:
        from app.core.security import get_password_hash
        user = User(
            id=uuid.uuid4(),
            email="admin@example.com",
            hashed_password=get_password_hash("AdminPass123!"),
            is_active=True,
            is_superuser=True,
            email_verified=True
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

@pytest.fixture
def rate_limiter():
    """Unique rate limiter for explicit rate limit tests"""
    return get_test_limiter()
