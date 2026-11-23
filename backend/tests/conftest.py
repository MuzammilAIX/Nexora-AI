"""Pytest fixtures: in-process ASGI client + authenticated headers.

IMPORTANT: ASGITransport (in-process test client) shares the event loop
across tests. After a test closes its DB session, the connection pool can
leave stale entries that cause the NEXT test's request to fail with a 502
(the orchestrator's "status: failed" → 502 path).

The `reset_db_pool` autouse fixture disposes the engine after each test,
forcing SQLAlchemy to open fresh connections on the next request. This
isolates tests from each other's connection state.
"""
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.database import engine

TEST_EMAIL = "test@nexora-test.com"
TEST_PASSWORD = "TestPass123!"


@pytest_asyncio.fixture(autouse=True)
async def reset_db_pool():
    """Dispose the engine pool after each test to prevent stale connections."""
    yield
    await engine.dispose()


@pytest_asyncio.fixture
async def client():
    """In-process client that talks directly to the ASGI app (no network)."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        timeout=120.0,  # reporting workflow needs up to 60s for LLM narrative
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_headers(client):
    """Return Authorization headers for the test user."""
    r = await client.post(
        "/api/v1/auth/login",
        json={"email": TEST_EMAIL, "password": TEST_PASSWORD},
    )
    assert r.status_code == 200, f"Login failed: {r.status_code} {r.text}"
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}