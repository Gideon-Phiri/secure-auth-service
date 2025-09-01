import asyncio
import pytest
from httpx import AsyncClient
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.db.models import User

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
engine_test = create_async_engine(TEST_DATABASE_URL, future=True)
AsyncSessionLocal = sessionmaker(engine_test, class_=AsyncSession, expire_on_commit=False)

async def override_get_session():
    async with AsyncSessionLocal() as session:
        yield session

@pytest.fixture(scope="session", autouse=True)
def prepare_db():
    async def create():
        async with engine_test.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
    asyncio.run(create())
    app.dependency_overrides.clear()
    from app.db.session import get_session
    app.dependency_overrides[get_session] = override_get_session

@pytest.fixture(scope="function")
async def client():
    async with AsyncClient(app=app, base_url="http://testserver") as c:
        yield c
