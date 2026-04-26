import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import get_db
from app.main import app

TEST_DATABASE_URL = "postgresql+asyncpg://ces_user:ces_password@localhost:5432/ces"

# NullPool ensures every test gets a brand-new connection — no recycled state
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False, poolclass=NullPool)


@pytest.fixture
async def db():
    """Each test gets a transaction that is rolled back on teardown — no leftover data.
    rollback_only means session.commit() is a no-op; only conn.rollback() at teardown
    actually runs, so every insert is undone after each test."""
    async with test_engine.connect() as conn:
        await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False, join_transaction_mode="rollback_only")
        try:
            yield session
        finally:
            await session.rollback()
            await session.close()
            await conn.rollback()


@pytest.fixture
async def client(db: AsyncSession):
    """HTTP client wired to the FastAPI app, with DB overridden to use the test transaction."""
    app.dependency_overrides[get_db] = lambda: db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()
