"""OAuth 2.0 token management for Zoho.

Zoho access tokens last roughly one hour. The manager caches the token,
refreshes it shortly before expiry, and guarantees a single refresh flight
when several callers hit an expired token concurrently.
"""

from __future__ import annotations

import asyncio
import logging
import time

import httpx

from .errors import AuthError

logger = logging.getLogger(__name__)

# Refresh this many seconds before the reported expiry so that in-flight
# requests never carry a token that expires mid-flight.
_EXPIRY_SKEW_SECONDS = 60.0


class TokenManager:
    """Caches one access token and refreshes it with single-flight semantics."""

    def __init__(
        self,
        http: httpx.AsyncClient,
        accounts_base: str,
        client_id: str,
        client_secret: str,
        refresh_token: str,
        *,
        skew_seconds: float = _EXPIRY_SKEW_SECONDS,
    ) -> None:
        self._http = http
        self._accounts_base = accounts_base.rstrip("/")
        self._client_id = client_id
        self._client_secret = client_secret
        self._refresh_token = refresh_token
        self._skew = skew_seconds
        self._lock = asyncio.Lock()
        self._access_token: str | None = None
        self._expires_at = 0.0

    async def get_access_token(self, *, force_refresh: bool = False) -> str:
        """Return a valid access token, refreshing at most once concurrently."""
        if not force_refresh and self._cache_valid():
            return self._access_token  # type: ignore[return-value]
        async with self._lock:
            # Another caller may have refreshed while we waited on the lock.
            if not force_refresh and self._cache_valid():
                return self._access_token  # type: ignore[return-value]
            await self._refresh()
            return self._access_token  # type: ignore[return-value]

    def _cache_valid(self) -> bool:
        return self._access_token is not None and time.monotonic() < self._expires_at - self._skew

    async def _refresh(self) -> None:
        resp = await self._http.post(
            f"{self._accounts_base}/oauth/v2/token",
            data={
                "grant_type": "refresh_token",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "refresh_token": self._refresh_token,
            },
        )
        if resp.status_code != 200:
            raise AuthError(f"token refresh failed with HTTP {resp.status_code}", code=resp.status_code)
        payload = resp.json()
        if "access_token" not in payload:
            # Zoho signals bad grants with HTTP 200 and an error payload.
            raise AuthError(f"token refresh rejected: {payload.get('error', 'unknown error')}")
        self._access_token = payload["access_token"]
        self._expires_at = time.monotonic() + float(payload.get("expires_in", 3600))
        logger.debug("access token refreshed, expires in %s seconds", payload.get("expires_in"))
