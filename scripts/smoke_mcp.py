"""Protocol-level smoke test: boot the MCP server over stdio and drive it.

This is the end-to-end proof that the deliverable works as an MCP server, not
just as a Python library: a real MCP client initializes a session, lists the
tools, and calls two of them against the live (fictional) LoomKart org.

    .venv/Scripts/python scripts/smoke_mcp.py
"""

import asyncio
import json

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def _payload(result) -> dict:
    """Extract the tool's JSON payload from a call result."""
    if getattr(result, "structuredContent", None):
        return result.structuredContent
    for block in result.content or []:
        if getattr(block, "text", None):
            return json.loads(block.text)
    return {}


async def main() -> int:
    params = StdioServerParameters(command=sys_executable(), args=["-m", "zoho_inventory_mcp"])
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        listing = await session.list_tools()
        print(f"server initialized, {len(listing.tools)} tools exposed:")
        for tool in sorted(listing.tools, key=lambda t: t.name):
            hint = " (read-only)" if tool.annotations and tool.annotations.read_only_hint else ""
            print(f"  {tool.name}{hint}")

        search = _payload(await session.call_tool("inventory_search_items", {"query": "jaipur"}))
        print(f"\nsearch 'jaipur' -> {search.get('summary')}")
        for item in search.get("items", [])[:2]:
            print(f"  {item.get('sku')}  stock={item.get('stock_on_hand')}")

        orders = _payload(await session.call_tool("orders_list_sales_orders", {"per_page": 3}))
        print(f"\norders page -> {orders.get('summary')}")
        for order in orders.get("sales_orders", [])[:3]:
            print(f"  {order.get('reference_number')}  {order.get('customer_name')}  {order.get('status')}")

        missing = _payload(await session.call_tool("inventory_get_item", {"item_id": "does-not-exist"}))
        error = missing.get("error", {})
        print(f"\nerror shaping -> {error.get('type')} (retryable={error.get('retryable')})")
    print("\nprotocol smoke passed")
    return 0


def sys_executable() -> str:
    import sys

    return sys.executable


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
