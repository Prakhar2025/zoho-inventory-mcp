"""Async client for the Zoho Inventory REST API.

Read-only primitives with pagination, search, rate limiting, retries, and a
mapping from HTTP and envelope errors onto the connector's error taxonomy.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

import httpx

from .auth import TokenManager
from .errors import (
    AuthError,
    NotFoundError,
    RateLimitError,
    UpstreamError,
    ValidationError,
)
from .models import Item, SalesOrder
from .rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

DEFAULT_PER_PAGE = 25
MAX_PER_PAGE = 200


@dataclass(frozen=True)
class Page[T]:
    """One page of results plus the flag needed to know whether to continue."""

    records: list[T]
    page: int
    per_page: int
    has_more: bool


def _clamp_per_page(per_page: int) -> int:
    return min(max(per_page, 1), MAX_PER_PAGE)


def _error_message(resp: httpx.Response) -> str:
    try:
        payload = resp.json()
    except ValueError:
        return (resp.text or resp.reason_phrase)[:200]
    if isinstance(payload, dict) and payload.get("message"):
        return f"{payload.get('message')} (code {payload.get('code')})"
    return (resp.text or resp.reason_phrase)[:200]


class ZohoInventoryClient:
    """Read-only Zoho Inventory client, safe to share across tasks."""

    def __init__(
        self,
        http: httpx.AsyncClient,
        tokens: TokenManager,
        *,
        api_base: str,
        org_id: str,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        self._http = http
        self._tokens = tokens
        self._api_base = api_base.rstrip("/")
        self._org_id = org_id
        self._limiter = rate_limiter or RateLimiter()

    # ------------------------------------------------------------- items

    async def list_items(self, *, page: int = 1, per_page: int = DEFAULT_PER_PAGE) -> Page[Item]:
        """List catalog items, one page at a time."""
        payload = await self._request("GET", "/items", params={"page": page, "per_page": _clamp_per_page(per_page)})
        records = [Item.model_validate(raw) for raw in payload.get("items", [])]
        return _build_page(records, page, per_page, payload)

    async def get_item(self, item_id: str) -> Item:
        """Fetch one item by internal id, falling back to an exact SKU match.

        Merchants and agents naturally say "LK-RUG-005", not Zoho's internal
        item id, so a failed id lookup resolves the value as a SKU via search.
        """
        try:
            payload = await self._request("GET", f"/items/{item_id}")
            return Item.model_validate(payload["item"])
        except NotFoundError:
            matches = await self.search_items(item_id, limit=5)
            for item in matches:
                if item.sku and item.sku.casefold() == item_id.strip().casefold():
                    return item
            raise

    async def search_items(self, query: str, *, limit: int = 10) -> list[Item]:
        """Search items by keyword in name or SKU.

        The query goes to Zoho as `search_text` first. Local matching is
        token-based with plural and prefix tolerance ("jaipur bedsheets" finds
        "Jaipur Block Print Bedsheet"). When the server-side search returns
        nothing (it matches whole phrases strictly), the catalog is scanned
        locally instead, which keeps natural-language queries working at the
        cost of one extra list call.
        """
        if not query.strip():
            return []
        payload = await self._request(
            "GET", "/items", params={"search_text": query.strip(), "per_page": _clamp_per_page(limit)}
        )
        matches = self._filter_items(payload.get("items", []), query)
        if not matches:
            payload = await self._request("GET", "/items", params={"per_page": MAX_PER_PAGE})
            matches = self._filter_items(payload.get("items", []), query)
        return matches[: max(limit, 1)]

    def _filter_items(self, raw_items: list[Any], query: str) -> list[Item]:
        return [
            Item.model_validate(raw)
            for raw in raw_items
            if _query_matches(query, raw.get("name"), raw.get("sku"), raw.get("description"))
        ]

    # ------------------------------------------------------ sales orders

    async def list_sales_orders(
        self,
        *,
        page: int = 1,
        per_page: int = DEFAULT_PER_PAGE,
        status: str | None = None,
    ) -> Page[SalesOrder]:
        """List sales orders, optionally filtered by status (for example confirmed)."""
        params: dict[str, Any] = {"page": page, "per_page": _clamp_per_page(per_page)}
        if status:
            params["status"] = status
        payload = await self._request("GET", "/salesorders", params=params)
        records = [SalesOrder.model_validate(raw) for raw in payload.get("salesorders", [])]
        return _build_page(records, page, per_page, payload)

    async def get_sales_order(self, salesorder_id: str) -> SalesOrder:
        """Fetch one sales order by internal id, order number, or reference number.

        The direct id lookup is tried first; if it misses, the value is resolved
        as a sales order number (SO-00005) or a merchant reference
        (LK-SO-018-20260914) through search, so callers never need to know
        Zoho's internal id scheme.
        """
        try:
            payload = await self._request("GET", f"/salesorders/{salesorder_id}")
            return SalesOrder.model_validate(payload["salesorder"])
        except NotFoundError:
            matches = await self.search_sales_orders(salesorder_id, limit=5)
            wanted = salesorder_id.strip().casefold()
            for order in matches:
                identifiers = {order.salesorder_number or "", order.reference_number or ""}
                if wanted in {value.casefold() for value in identifiers}:
                    return order
            raise

    async def search_sales_orders(self, query: str, *, limit: int = 10) -> list[SalesOrder]:
        """Search sales orders by keyword (customer name or order number).

        Uses the same strategy as item search: server `search_text` first,
        token-based local filtering, and a local scan fallback when the server
        finds nothing (order history is scanned one page deep, which covers
        free-plan orgs comfortably).
        """
        if not query.strip():
            return []
        payload = await self._request(
            "GET", "/salesorders", params={"search_text": query.strip(), "per_page": _clamp_per_page(limit)}
        )
        matches = self._filter_orders(payload.get("salesorders", []), query)
        if not matches:
            payload = await self._request("GET", "/salesorders", params={"per_page": MAX_PER_PAGE})
            matches = self._filter_orders(payload.get("salesorders", []), query)
        return matches[: max(limit, 1)]

    def _filter_orders(self, raw_orders: list[Any], query: str) -> list[SalesOrder]:
        return [
            SalesOrder.model_validate(raw)
            for raw in raw_orders
            if _query_matches(
                query,
                raw.get("customer_name"),
                raw.get("salesorder_number"),
                raw.get("reference_number"),
            )
        ]

    # ------------------------------------------------------------ internals

    async def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Issue one API call with pacing, retries, and error mapping.

        429 and 5xx are retried with backoff. A 401 triggers exactly one forced
        token refresh before failing with AuthError, so an hourly token
        rollover never surfaces to the agent.
        """
        attempt = 0
        force_refresh = False
        refreshed_once = False
        while True:
            await self._limiter.acquire()
            token = await self._tokens.get_access_token(force_refresh=force_refresh)
            force_refresh = False
            try:
                resp = await self._http.request(
                    method,
                    f"{self._api_base}{path}",
                    params=params,
                    headers={"Authorization": f"Zoho-oauthtoken {token}", "Organization-Id": self._org_id},
                )
            except httpx.HTTPError as exc:
                if attempt >= self._limiter.max_retries:
                    raise UpstreamError(f"network error calling {path}: {exc}") from exc
                logger.warning("network error on %s (attempt %d): %s", path, attempt + 1, exc)
                attempt += 1
                await self._limiter.backoff(attempt)
                continue

            if resp.status_code == 401:
                if not refreshed_once:
                    logger.info("got 401 on %s, forcing a token refresh and retrying once", path)
                    refreshed_once = True
                    force_refresh = True
                    continue
                raise AuthError(_error_message(resp), code=401)

            if resp.status_code == 429:
                retry_after = _parse_retry_after(resp.headers.get("Retry-After"))
                if attempt >= self._limiter.max_retries:
                    raise RateLimitError(f"rate limited on {path}", retry_after=retry_after)
                logger.warning("rate limited on %s, backing off (attempt %d)", path, attempt + 1)
                await self._limiter.backoff(attempt, retry_after)
                attempt += 1
                continue

            if resp.status_code >= 500:
                if attempt >= self._limiter.max_retries:
                    raise UpstreamError(f"Zoho server error {resp.status_code} on {path}: {_error_message(resp)}")
                await self._limiter.backoff(attempt)
                attempt += 1
                continue

            if resp.status_code == 404:
                raise NotFoundError(f"not found: {path}", code=404)

            if resp.status_code >= 400:
                raise ValidationError(f"bad request on {path}: {_error_message(resp)}", code=resp.status_code)

            try:
                payload = resp.json()
            except ValueError as exc:
                raise ValidationError(f"malformed JSON from {path}") from exc
            code = payload.get("code")
            if isinstance(code, int) and code != 0:
                # Zoho reports application-level errors inside HTTP 200.
                raise ValidationError(f"Zoho error {code} on {path}: {payload.get('message')}", code=code)
            return payload


def _build_page[T](records: list[T], page: int, per_page: int, payload: dict[str, Any]) -> Page[T]:
    """Derive page metadata from the Zoho envelope's page_context block."""
    context = payload.get("page_context") or {}
    has_more = bool(context.get("has_more_page", len(records) >= _clamp_per_page(per_page)))
    return Page(records=records, page=page, per_page=per_page, has_more=has_more)


def _query_matches(query: str, *fields: str | None) -> bool:
    """Token-based relevance check across the given fields.

    Every query token must match some field. A token matches when it appears
    as a substring (covering SKUs like lk-rug) or when a field word and the
    token share a prefix of at least three characters (covering plurals and
    stems like bedsheets vs bedsheet).
    """
    tokens = [token for token in query.strip().casefold().split() if token]
    if not tokens:
        return False
    for token in tokens:
        if not any(_token_in_field(token, field) for field in fields):
            return False
    return True


def _token_in_field(token: str, field: str | None) -> bool:
    haystack = (field or "").casefold()
    if not haystack:
        return False
    if token in haystack:
        return True
    return any(_shares_prefix(token, word) for word in re.findall(r"[a-z0-9]+", haystack))


def _shares_prefix(token: str, word: str) -> bool:
    """Plural and stem tolerance, guarded against short-word false matches."""
    if token == word:
        return True
    if len(word) >= 3 and token.startswith(word):
        return True
    return len(token) >= 3 and word.startswith(token)


def _parse_retry_after(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except ValueError:
        return None
