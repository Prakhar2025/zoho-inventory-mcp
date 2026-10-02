"""Shared test fixtures. The suite is hermetic: no real network access."""

import httpx
import pytest

from zoho_inventory_mcp.client import ZohoInventoryClient
from zoho_inventory_mcp.rate_limiter import RateLimiter

API_BASE = "https://www.zohoapis.in/inventory/v1"
ACCOUNTS_BASE = "https://accounts.zoho.in"
ORG_ID = "org123"


class FakeTokens:
    """Stands in for TokenManager; records force-refresh calls."""

    def __init__(self) -> None:
        self.calls: list[bool] = []

    async def get_access_token(self, *, force_refresh: bool = False) -> str:
        self.calls.append(force_refresh)
        return "new-token" if force_refresh else "stale-token"


@pytest.fixture
def fake_tokens() -> FakeTokens:
    return FakeTokens()


@pytest.fixture
async def http() -> httpx.AsyncClient:
    async with httpx.AsyncClient() as inner:
        yield inner


@pytest.fixture
def fast_limiter() -> RateLimiter:
    """A limiter with no waiting, so tests stay fast and deterministic."""
    return RateLimiter(min_interval=0.0, max_retries=3, base_delay=0.0, max_delay=0.0)


@pytest.fixture
def client(http: httpx.AsyncClient, fake_tokens: FakeTokens, fast_limiter: RateLimiter) -> ZohoInventoryClient:
    return ZohoInventoryClient(
        http, fake_tokens, api_base=API_BASE, org_id=ORG_ID, rate_limiter=fast_limiter
    )
