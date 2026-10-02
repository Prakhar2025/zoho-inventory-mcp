"""Live smoke test against the (fictional) LoomKart Zoho org.

Exercises the real path end to end: OAuth refresh, call pacing, list and
search primitives. Read-only and safe to rerun.

    .venv/Scripts/python scripts/smoke_live.py
"""

import asyncio

import httpx

from zoho_inventory_mcp.auth import TokenManager
from zoho_inventory_mcp.client import ZohoInventoryClient
from zoho_inventory_mcp.config import get_settings
from zoho_inventory_mcp.errors import ZohoError
from zoho_inventory_mcp.rate_limiter import RateLimiter


async def main() -> int:
    settings = get_settings()
    if not settings.is_configured:
        print("connector not configured: fill .env (see .env.example)")
        return 1

    async with httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=10.0)) as http:
        tokens = TokenManager(
            http,
            settings.accounts_base,
            settings.zoho_client_id,
            settings.zoho_client_secret,
            settings.zoho_refresh_token,
        )
        client = ZohoInventoryClient(
            http,
            tokens,
            api_base=settings.api_base,
            org_id=settings.zoho_org_id,
            rate_limiter=RateLimiter(min_interval=settings.call_spacing_seconds),
        )

        items = await client.list_items(per_page=3)
        print(f"items page 1: {len(items.records)} records (has_more={items.has_more})")
        for item in items.records:
            print(f"  {item.sku or '-':12}  {item.name}  stock={item.stock_on_hand}")

        matches = await client.search_items("jaipur")
        print(f"search 'jaipur': {len(matches)} matched")

        orders = await client.list_sales_orders(per_page=5)
        print(f"sales orders page 1: {len(orders.records)} records (has_more={orders.has_more})")
        for order in orders.records:
            print(f"  {order.reference_number or '-'}  {order.customer_name}  {order.status}  {order.total}")

        confirmed = await client.list_sales_orders(status="confirmed", per_page=3)
        print(f"confirmed orders: {len(confirmed.records)} on first page")
        return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except ZohoError as exc:
        print(f"FAILED: {type(exc).__name__}: {exc.message}")
        raise SystemExit(2) from exc
