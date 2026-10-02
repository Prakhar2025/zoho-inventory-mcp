"""MCP server exposing read-only Zoho Inventory tools.

The tool docstrings are written for an LLM consumer: together with the JSON
schemas MCPServer derives from the type hints, they are the MCP tool
specification, and they live in code so they cannot drift from a document.

Run locally over stdio:

    py -3.12 -m zoho_inventory_mcp
"""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

import httpx
from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from .audit import AuditLogger
from .client import DEFAULT_PER_PAGE, MAX_PER_PAGE, Page, ZohoInventoryClient
from .config import Settings, get_settings
from .errors import AuthError, RateLimitError, ZohoError
from .models import Item, SalesOrder

logger = logging.getLogger(__name__)

SERVER_NAME = "zoho-inventory"

# Declared on every tool so MCP clients know these never mutate merchant data.
READ_ONLY = ToolAnnotations(readOnlyHint=True)

SERVER_INSTRUCTIONS = (
    "Read-only access to a Zoho Inventory organization. Use the inventory_* tools for "
    "products and stock levels, and the orders_* tools for customer sales orders. "
    "Errors come back as structured payloads with a retryable flag: retryable errors "
    "(rate limits, server errors) mean wait and try again, non-retryable errors mean "
    "stop or rephrase. This connector can never modify data."
)


def build_runtime(settings: Settings) -> tuple[ZohoInventoryClient, AuditLogger]:
    """Construct the HTTP stack and audit log from settings.

    Raises AuthError if credentials are missing, so misconfiguration surfaces
    at startup instead of on the first tool call.
    """
    if not settings.is_configured:
        raise AuthError(
            "connector is not configured: set ZOHO_CLIENT_ID, ZOHO_CLIENT_SECRET, "
            "ZOHO_REFRESH_TOKEN, and ZOHO_ORG_ID in .env (see .env.example)"
        )
    http = httpx.AsyncClient(timeout=httpx.Timeout(20.0, connect=10.0))
    from .auth import TokenManager

    tokens = TokenManager(
        http,
        settings.accounts_base,
        settings.zoho_client_id,
        settings.zoho_client_secret,
        settings.zoho_refresh_token,
    )
    from .rate_limiter import RateLimiter

    limiter = RateLimiter(min_interval=settings.call_spacing_seconds)
    client = ZohoInventoryClient(http, tokens, api_base=settings.api_base, org_id=settings.zoho_org_id, rate_limiter=limiter)
    return client, AuditLogger(settings.audit_log_path)


def _error_payload(exc: ZohoError) -> dict[str, Any]:
    error: dict[str, Any] = {
        "type": type(exc).__name__,
        "message": exc.message,
        "retryable": exc.retryable,
    }
    if isinstance(exc, RateLimitError) and exc.retry_after is not None:
        error["retry_after_seconds"] = exc.retry_after
    return {"error": error}


def _item_view(item: Item) -> dict[str, Any]:
    return item.model_dump(exclude_none=True)


def _order_view(order: SalesOrder) -> dict[str, Any]:
    return order.model_dump(exclude_none=True)


def _items_page_view(result: Page[Item], *, page: int) -> dict[str, Any]:
    return {
        "summary": f"Page {page}: {len(result.records)} items" + (", more pages available" if result.has_more else ""),
        "count": len(result.records),
        "page": page,
        "has_more": result.has_more,
        "items": [_item_view(item) for item in result.records],
    }


def _orders_page_view(result: Page[SalesOrder], *, page: int) -> dict[str, Any]:
    return {
        "summary": f"Page {page}: {len(result.records)} sales orders"
        + (", more pages available" if result.has_more else ""),
        "count": len(result.records),
        "page": page,
        "has_more": result.has_more,
        "sales_orders": [_order_view(order) for order in result.records],
    }


def register_tools(
    mcp: MCPServer,
    client: ZohoInventoryClient,
    audit: AuditLogger,
) -> dict[str, Callable[..., Awaitable[dict[str, Any]]]]:
    """Attach the six read-only tools to `mcp` and return them for testing."""

    async def guarded(tool: str, params: dict[str, Any], operation: Callable[[], Awaitable[dict[str, Any]]]) -> dict[str, Any]:
        started = time.perf_counter()
        try:
            result = await operation()
        except ZohoError as exc:
            duration = (time.perf_counter() - started) * 1000
            await audit.record(tool=tool, params=params, status="error", duration_ms=duration, error=exc.message)
            return _error_payload(exc)
        except Exception as exc:
            # Broad by design: the agent must receive a structured payload, never a dropped call.
            logger.exception("unexpected error in tool %s", tool)
            duration = (time.perf_counter() - started) * 1000
            await audit.record(tool=tool, params=params, status="error", duration_ms=duration, error=f"unexpected: {exc}")
            return {"error": {"type": "UnexpectedError", "message": str(exc)[:200], "retryable": False}}
        duration = (time.perf_counter() - started) * 1000
        await audit.record(tool=tool, params=params, status="ok", duration_ms=duration)
        return result

    @mcp.tool(annotations=READ_ONLY)
    async def inventory_list_items(page: int = 1, per_page: int = DEFAULT_PER_PAGE) -> dict[str, Any]:
        """List inventory items, one page at a time.

        Use when the agent needs to browse the catalog or answer "what products
        do we sell". Returns items with id, name, sku, and rate; stock fields
        appear only when the org tracks inventory. Advance by passing page+1
        while has_more is true.
        """
        clamped = min(max(per_page, 1), MAX_PER_PAGE)
        safe_page = max(page, 1)
        return await guarded(
            "inventory_list_items",
            {"page": safe_page, "per_page": clamped},
            lambda: _list_items(client, safe_page, clamped),
        )

    async def _list_items(client_: ZohoInventoryClient, page: int, per_page: int) -> dict[str, Any]:
        result = await client_.list_items(page=page, per_page=per_page)
        return _items_page_view(result, page=page)

    @mcp.tool(annotations=READ_ONLY)
    async def inventory_get_item(item_id: str) -> dict[str, Any]:
        """Get one inventory item by its item_id or by SKU.

        Use when the agent knows either the internal id (from a previous call)
        or the merchant-facing SKU (LK-BED-001) and needs the single product
        record.
        """
        return await guarded(
            "inventory_get_item",
            {"item_id": item_id},
            lambda: _get_item(client, item_id),
        )

    async def _get_item(client_: ZohoInventoryClient, item_id: str) -> dict[str, Any]:
        item = await client_.get_item(item_id)
        return {"summary": f"Item {item.name}", "item": _item_view(item)}

    @mcp.tool(annotations=READ_ONLY)
    async def inventory_search_items(query: str, limit: int = 10) -> dict[str, Any]:
        """Search inventory items by keyword matching name or SKU.

        Use for questions like "do we stock jaipur bedsheets" or "find item
        LK-RUG-005". Returns up to `limit` matching items.
        """
        return await guarded(
            "inventory_search_items",
            {"query": query, "limit": max(limit, 1)},
            lambda: _search_items(client, query, limit),
        )

    async def _search_items(client_: ZohoInventoryClient, query: str, limit: int) -> dict[str, Any]:
        items = await client_.search_items(query, limit=max(limit, 1))
        return {
            "summary": f"{len(items)} items matched \"{query}\"",
            "count": len(items),
            "items": [_item_view(item) for item in items],
        }

    @mcp.tool(annotations=READ_ONLY)
    async def orders_list_sales_orders(
        page: int = 1,
        per_page: int = DEFAULT_PER_PAGE,
        status: str | None = None,
    ) -> dict[str, Any]:
        """List sales orders, newest period included, one page at a time.

        Use for "show recent orders" or "which orders are still confirmed" by
        passing a status filter such as draft, confirmed, or fulfilled. Returns
        order number, customer, date, status, and total for each order.
        """
        clamped = min(max(per_page, 1), MAX_PER_PAGE)
        safe_page = max(page, 1)
        return await guarded(
            "orders_list_sales_orders",
            {"page": safe_page, "per_page": clamped, "status": status},
            lambda: _list_orders(client, safe_page, clamped, status),
        )

    async def _list_orders(
        client_: ZohoInventoryClient, page: int, per_page: int, status: str | None
    ) -> dict[str, Any]:
        result = await client_.list_sales_orders(page=page, per_page=per_page, status=status)
        view = _orders_page_view(result, page=page)
        if status:
            view["filtered_by_status"] = status
        return view

    @mcp.tool(annotations=READ_ONLY)
    async def orders_get_sales_order(salesorder_id: str) -> dict[str, Any]:
        """Get one sales order by internal id, order number, or reference number.

        Accepts Zoho ids (from a previous call), merchant numbers (SO-00005), or
        reference codes (LK-SO-018-20260914). Returns the full order including
        line items, quantities, rates, and totals.
        """
        return await guarded(
            "orders_get_sales_order",
            {"salesorder_id": salesorder_id},
            lambda: _get_order(client, salesorder_id),
        )

    async def _get_order(client_: ZohoInventoryClient, salesorder_id: str) -> dict[str, Any]:
        order = await client_.get_sales_order(salesorder_id)
        return {"summary": f"Order {order.salesorder_number or order.salesorder_id}", "sales_order": _order_view(order)}

    @mcp.tool(annotations=READ_ONLY)
    async def orders_search_sales_orders(query: str, limit: int = 10) -> dict[str, Any]:
        """Search sales orders by keyword matching customer name or order number.

        Use for "orders for Aarav Sharma" or "find order LK-SO-005". Returns up
        to `limit` matching orders.
        """
        return await guarded(
            "orders_search_sales_orders",
            {"query": query, "limit": max(limit, 1)},
            lambda: _search_orders(client, query, limit),
        )

    async def _search_orders(client_: ZohoInventoryClient, query: str, limit: int) -> dict[str, Any]:
        orders = await client_.search_sales_orders(query, limit=max(limit, 1))
        return {
            "summary": f"{len(orders)} sales orders matched \"{query}\"",
            "count": len(orders),
            "sales_orders": [_order_view(order) for order in orders],
        }

    return {
        "inventory_list_items": inventory_list_items,
        "inventory_get_item": inventory_get_item,
        "inventory_search_items": inventory_search_items,
        "orders_list_sales_orders": orders_list_sales_orders,
        "orders_get_sales_order": orders_get_sales_order,
        "orders_search_sales_orders": orders_search_sales_orders,
    }


def create_mcp_server(settings: Settings | None = None) -> MCPServer:
    """Wire the runtime into an MCP server instance."""
    settings = settings or get_settings()
    client, audit = build_runtime(settings)
    mcp = MCPServer(SERVER_NAME, instructions=SERVER_INSTRUCTIONS)
    register_tools(mcp, client, audit)
    return mcp


def main() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    server = create_mcp_server(settings)
    logger.info("starting MCP server over stdio")
    server.run()


if __name__ == "__main__":
    main()
