"""MCP tool layer: payload shapes, error shaping, and audit records."""

import json

import pytest
from mcp.server.mcpserver import MCPServer

from zoho_inventory_mcp.audit import AuditLogger
from zoho_inventory_mcp.client import Page
from zoho_inventory_mcp.errors import NotFoundError, RateLimitError
from zoho_inventory_mcp.models import Item, SalesOrder
from zoho_inventory_mcp.server import register_tools

ITEM = Item(item_id="i1", name="Jaipur Block Print Bedsheet", sku="LK-BED-001", rate=1899.0, stock_on_hand=40.0)
ORDER = SalesOrder(salesorder_id="so1", salesorder_number="SO-0001", status="confirmed", customer_name="Aarav Sharma")

EXPECTED_TOOLS = {
    "inventory_list_items",
    "inventory_get_item",
    "inventory_search_items",
    "orders_list_sales_orders",
    "orders_get_sales_order",
    "orders_search_sales_orders",
}


class StubClient:
    """Canned client: no network, deterministic results."""

    async def list_items(self, *, page: int = 1, per_page: int = 25) -> Page[Item]:
        return Page(records=[ITEM], page=page, per_page=per_page, has_more=False)

    async def get_item(self, item_id: str) -> Item:
        if item_id == "missing":
            raise NotFoundError("no such item")
        return ITEM

    async def search_items(self, query: str, *, limit: int = 10) -> list[Item]:
        return [ITEM][:limit]

    async def list_sales_orders(
        self, *, page: int = 1, per_page: int = 25, status: str | None = None
    ) -> Page[SalesOrder]:
        return Page(records=[ORDER], page=page, per_page=per_page, has_more=True)

    async def get_sales_order(self, salesorder_id: str) -> SalesOrder:
        if salesorder_id == "missing":
            raise RateLimitError("throttled by Zoho", retry_after=12.0)
        return ORDER

    async def search_sales_orders(self, query: str, *, limit: int = 10) -> list[SalesOrder]:
        return [ORDER][:limit]


@pytest.fixture
def tools(tmp_path):
    """(tool mapping, audit file path) backed by the stub client."""
    mcp = MCPServer("test-server")
    mapping = register_tools(mcp, StubClient(), AuditLogger(tmp_path / "audit.jsonl"))
    return mapping, tmp_path / "audit.jsonl"


async def test_all_six_tools_are_registered(tools):
    mapping, _ = tools
    assert set(mapping) == EXPECTED_TOOLS


async def test_list_items_payload_shape(tools):
    mapping, _ = tools

    payload = await mapping["inventory_list_items"](page=1, per_page=25)

    assert payload["count"] == 1
    assert payload["has_more"] is False
    assert payload["items"][0]["sku"] == "LK-BED-001"
    assert "1 items" in payload["summary"]


async def test_get_missing_item_returns_structured_error(tools):
    mapping, _ = tools

    payload = await mapping["inventory_get_item"](item_id="missing")

    assert payload["error"]["type"] == "NotFoundError"
    assert payload["error"]["retryable"] is False
    assert "message" in payload["error"]


async def test_rate_limit_error_carries_retry_after(tools):
    mapping, _ = tools

    payload = await mapping["orders_get_sales_order"](salesorder_id="missing")

    assert payload["error"]["type"] == "RateLimitError"
    assert payload["error"]["retryable"] is True
    assert payload["error"]["retry_after_seconds"] == 12.0


async def test_successful_calls_are_audited(tools):
    mapping, audit_path = tools

    await mapping["inventory_list_items"]()

    lines = audit_path.read_text(encoding="utf-8").strip().splitlines()
    entry = json.loads(lines[-1])
    assert entry["tool"] == "inventory_list_items"
    assert entry["status"] == "ok"
    assert "duration_ms" in entry


async def test_error_calls_are_audited(tools):
    mapping, audit_path = tools

    await mapping["inventory_get_item"](item_id="missing")

    entry = json.loads(audit_path.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert entry["status"] == "error"
    assert entry["error"].startswith("no such item")


async def test_orders_list_includes_filter_metadata(tools):
    mapping, _ = tools

    payload = await mapping["orders_list_sales_orders"](status="confirmed")

    assert payload["filtered_by_status"] == "confirmed"
    assert payload["has_more"] is True
