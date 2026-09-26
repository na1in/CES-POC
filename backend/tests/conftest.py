from contextlib import ExitStack

import pytest
from unittest.mock import patch, AsyncMock
from httpx import ASGITransport, AsyncClient
from sqlalchemy.pool import NullPool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

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
    By default, keep every test offline and deterministic. The pipeline has two LLM call sites left (reference parsing
    is now a deterministic regex and needs no mock):

      - get_reasoning: analyst-facing prose. Patched to a fixed fallback; the narrative does not affect routing,
        recommendation, status, or any signal we assert on.
      - the gray-zone name scorer's client: made to fail, so compute_name_similarity falls back to the deterministic
        score (its documented behaviour). Tests that exercise the LLM path patch _get_client themselves.

    Patches are applied where each name is USED. The scenario handlers import get_reasoning by name, so patching only
    app.services.agent.reasoning.get_reasoning never reached them and real LLM calls slipped through.

    Pass --live-llm to skip patching and exercise real OpenRouter calls.
    """
    if request.config.getoption("--live-llm"):
        yield  # no patching — real LLM
        return

    _fake_reasoning = AsyncMock(
        return_value=(["Mocked reasoning — run with --live-llm to use real LLM"], "Mocked suggested action")
    )
    reasoning_targets = ["app.services.agent.reasoning.get_reasoning"] + [
        f"app.services.agent.scenarios.sc{n}.get_reasoning" for n in range(1, 6)
    ]

    with ExitStack() as stack:
        for target in reasoning_targets:
            stack.enter_context(patch(target, _fake_reasoning))
        stack.enter_context(
            patch("app.services.signals.matching._get_client", side_effect=RuntimeError("LLM disabled in tests (use --live-llm)"))
        )
        yield


# Follow the app's own configuration (backend/.env) rather than hardcoding a
# port — a local docker-compose override can move Postgres off 5432, and a
# hardcoded URL silently makes the whole suite unrunnable on that machine.
TEST_DATABASE_URL = settings.DATABASE_URL

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
