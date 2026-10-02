"""TokenManager: caching, expiry-aware refresh, single-flight refresh."""

import asyncio

import httpx
import pytest

from zoho_inventory_mcp.auth import TokenManager
from zoho_inventory_mcp.errors import AuthError

ACCOUNTS_BASE = "https://accounts.zoho.in"
TOKEN_URL = f"{ACCOUNTS_BASE}/oauth/v2/token"


def make_manager(http: httpx.AsyncClient, **kwargs: object) -> TokenManager:
    return TokenManager(http, ACCOUNTS_BASE, "client-id", "client-secret", "refresh-token", **kwargs)


async def test_token_is_cached_until_near_expiry(respx_mock, http):
    route = respx_mock.post(TOKEN_URL).mock(
        return_value=httpx.Response(200, json={"access_token": "t1", "expires_in": 3600})
    )
    manager = make_manager(http)

    assert await manager.get_access_token() == "t1"
    assert await manager.get_access_token() == "t1"
    assert route.call_count == 1


async def test_refreshes_when_within_skew_window(respx_mock, http):
    route = respx_mock.post(TOKEN_URL).mock(
        return_value=httpx.Response(200, json={"access_token": "t1", "expires_in": 30})
    )
    manager = make_manager(http)

    await manager.get_access_token()
    await manager.get_access_token()
    # 30 seconds of validity minus the 60 second skew means every call refreshes.
    assert route.call_count == 2


async def test_single_flight_when_cache_expires(respx_mock, http):
    route = respx_mock.post(TOKEN_URL).mock(
        return_value=httpx.Response(200, json={"access_token": "t1", "expires_in": 3600})
    )
    manager = make_manager(http)
    await manager.get_access_token()
    manager._expires_at = 0.0  # simulate the cached token aging out

    results = await asyncio.gather(*(manager.get_access_token() for _ in range(3)))

    assert results == ["t1", "t1", "t1"]
    assert route.call_count == 2  # the warm-up call plus exactly one refresh flight


async def test_force_refresh_bypasses_cache(respx_mock, http):
    route = respx_mock.post(TOKEN_URL).mock(
        side_effect=[
            httpx.Response(200, json={"access_token": "t1", "expires_in": 3600}),
            httpx.Response(200, json={"access_token": "t2", "expires_in": 3600}),
        ]
    )
    manager = make_manager(http)

    first = await manager.get_access_token()
    second = await manager.get_access_token(force_refresh=True)

    assert (first, second) == ("t1", "t2")
    assert route.call_count == 2


async def test_error_payload_raises_auth_error(respx_mock, http):
    respx_mock.post(TOKEN_URL).mock(return_value=httpx.Response(200, json={"error": "invalid_code"}))
    manager = make_manager(http)

    with pytest.raises(AuthError, match="invalid_code"):
        await manager.get_access_token()


async def test_http_failure_raises_auth_error(respx_mock, http):
    respx_mock.post(TOKEN_URL).mock(return_value=httpx.Response(403, json={}))
    manager = make_manager(http)

    with pytest.raises(AuthError, match="403"):
        await manager.get_access_token()
