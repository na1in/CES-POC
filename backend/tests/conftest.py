import re
import pytest
from unittest.mock import patch, AsyncMock
from httpx import ASGITransport, AsyncClient
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import get_db
from app.main import app


def pytest_addoption(parser):
    parser.addoption(
        "--live-llm",
        action="store_true",
        default=False,
        help="Use real OpenRouter LLM calls instead of mocks (slower, costs money)",
    )


@pytest.fixture(autouse=True)
def maybe_mock_llm(request):
    """
    By default, patch both LLM callsites so tests run fast and offline.
    Pass --live-llm to skip patching and exercise real OpenRouter calls.

    parse_reference_fields mock: regex-extracts POL-XXXXX from the reference
    text — no LLM needed, produces the same result for well-formed references.

    get_reasoning mock: returns a fixed fallback — the narrative it produces
    does not affect routing decisions, recommendation, status, or any signal
    we assert on in E2E tests.
    """
    if request.config.getoption("--live-llm"):
        yield  # no patching — real LLM
        return

    async def _fake_parse(ref1: str | None, ref2: str | None) -> dict:
        text = f"{ref1 or ''} {ref2 or ''}"
        m = re.search(r"POL-\d+", text)
        return {
            "extracted_policy_number": m.group(0) if m else None,
            "payment_intent": "payment",
            "period_count": 1,
        }

    _fake_reasoning = AsyncMock(
        return_value=(["Mocked reasoning — run with --live-llm to use real LLM"], "Mocked suggested action")
    )

    with (
        patch("app.services.ingest.parse_reference_fields", side_effect=_fake_parse),
        patch("app.services.agent.reasoning.get_reasoning", _fake_reasoning),
    ):
        yield

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
