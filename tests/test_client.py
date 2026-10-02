"""Client primitives: mapping, pagination, search, retries, error taxonomy."""

import httpx
import pytest

from zoho_inventory_mcp.errors import (
    AuthError,
    NotFoundError,
    RateLimitError,
    UpstreamError,
    ValidationError,
)

API_BASE = "https://www.zohoapis.in/inventory/v1"

ITEM_A = {
    "item_id": "i1",
    "name": "Jaipur Block Print Bedsheet (Queen)",
    "sku": "LK-BED-001",
    "rate": 1899.0,
    "stock_on_hand": 40.0,
    "vendor_taxes": [{"tax_id": "ignored"}],
}
ITEM_B = {"item_id": "i2", "name": "Dhurrie Jute Rug", "sku": "LK-RUG-005", "rate": 2799.0}
ITEMS_PAGE = {
    "code": 0,
    "message": "success",
    "items": [ITEM_A, ITEM_B],
    "page_context": {"page": 1, "per_page": 2, "has_more_page": True},
}
ORDER = {
    "salesorder_id": "so1",
    "salesorder_number": "SO-0001",
    "reference_number": "LK-SO-028-20260904",
    "date": "2026-09-04",
    "status": "confirmed",
    "customer_name": "Aarav Sharma",
    "total": 1899.0,
    "currency": "INR",
    "line_items": [
        {"item_id": "i1", "name": "Jaipur Block Print Bedsheet", "quantity": 1.0, "rate": 1899.0, "item_total": 1899.0}
    ],
}
ORDERS_PAGE = {"code": 0, "message": "success", "salesorders": [ORDER], "page_context": {"has_more_page": False}}


async def test_list_items_maps_models_and_page_metadata(client, respx_mock):
    route = respx_mock.get(f"{API_BASE}/items").mock(return_value=httpx.Response(200, json=ITEMS_PAGE))

    result = await client.list_items(page=1, per_page=2)

    assert [item.item_id for item in result.records] == ["i1", "i2"]
    assert result.records[0].name == "Jaipur Block Print Bedsheet (Queen)"
    assert result.records[0].stock_on_hand == 40.0
    assert result.has_more is True
    assert route.call_count == 1


async def test_list_items_ignores_unknown_fields(client, respx_mock):
    respx_mock.get(f"{API_BASE}/items").mock(return_value=httpx.Response(200, json=ITEMS_PAGE))

    result = await client.list_items()

    assert result.records[0].model_dump().get("vendor_taxes") is None


async def test_get_item_returns_normalized_model(client, respx_mock):
    respx_mock.get(f"{API_BASE}/items/i1").mock(
        return_value=httpx.Response(200, json={"code": 0, "item": ITEM_A})
    )

    item = await client.get_item("i1")

    assert item.sku == "LK-BED-001"


async def test_get_missing_item_raises_not_found(client, respx_mock):
    respx_mock.get(f"{API_BASE}/items/missing").mock(
        return_value=httpx.Response(404, json={"message": "not found"})
    )

    with pytest.raises(NotFoundError):
        await client.get_item("missing")


async def test_rate_limit_is_retried_until_success(client, respx_mock):
    route = respx_mock.get(f"{API_BASE}/items").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "0"}, json={}),
            httpx.Response(429, headers={"Retry-After": "0"}, json={}),
            httpx.Response(200, json=ITEMS_PAGE),
        ]
    )

    result = await client.list_items()

    assert len(result.records) == 2
    assert route.call_count == 3


async def test_persistent_rate_limit_raises_with_retry_after(client, respx_mock):
    route = respx_mock.get(f"{API_BASE}/items").mock(
        return_value=httpx.Response(429, headers={"Retry-After": "7"}, json={})
    )

    with pytest.raises(RateLimitError) as excinfo:
        await client.list_items()

    assert excinfo.value.retry_after == 7.0
    assert excinfo.value.retryable is True
    assert route.call_count == 4  # initial attempt plus max_retries


async def test_server_errors_are_retried_then_raise_upstream(client, respx_mock):
    route = respx_mock.get(f"{API_BASE}/items").mock(
        return_value=httpx.Response(503, json={"message": "down"})
    )

    with pytest.raises(UpstreamError):
        await client.list_items()

    assert route.call_count == 4


async def test_network_errors_are_retried_then_raise_upstream(client, respx_mock):
    route = respx_mock.get(f"{API_BASE}/items").mock(side_effect=httpx.ConnectError("boom"))

    with pytest.raises(UpstreamError, match="boom"):
        await client.list_items()

    assert route.call_count == 4


async def test_401_triggers_exactly_one_forced_refresh_then_succeeds(client, fake_tokens, respx_mock):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.headers["Authorization"].endswith("stale-token"):
            return httpx.Response(401, json={"code": 57, "message": "not authorized"})
        return httpx.Response(200, json=ITEMS_PAGE)

    respx_mock.get(f"{API_BASE}/items").mock(side_effect=handler)

    result = await client.list_items()

    assert fake_tokens.calls == [False, True]
    assert len(result.records) == 2


async def test_401_after_refresh_raises_auth_error(client, fake_tokens, respx_mock):
    respx_mock.get(f"{API_BASE}/items").mock(
        return_value=httpx.Response(401, json={"code": 57, "message": "not authorized"})
    )

    with pytest.raises(AuthError):
        await client.list_items()

    assert fake_tokens.calls == [False, True]


async def test_envelope_error_inside_http_200_maps_to_validation_error(client, respx_mock):
    respx_mock.get(f"{API_BASE}/items").mock(
        return_value=httpx.Response(200, json={"code": 1002, "message": "bad parameter"})
    )

    with pytest.raises(ValidationError, match="1002"):
        await client.list_items()


async def test_list_sales_orders_passes_status_filter(client, respx_mock):
    captured: dict[str, str] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["status"] = str(request.url.params.get("status"))
        return httpx.Response(200, json=ORDERS_PAGE)

    respx_mock.get(f"{API_BASE}/salesorders").mock(side_effect=handler)

    result = await client.list_sales_orders(status="confirmed")

    assert captured["status"] == "confirmed"
    assert result.records[0].customer_name == "Aarav Sharma"
    assert result.has_more is False


async def test_get_sales_order_maps_line_items(client, respx_mock):
    respx_mock.get(f"{API_BASE}/salesorders/so1").mock(
        return_value=httpx.Response(200, json={"code": 0, "salesorder": ORDER})
    )

    order = await client.get_sales_order("so1")

    assert order.line_items[0].item_total == 1899.0
    assert order.reference_number == "LK-SO-028-20260904"


async def test_search_items_filters_results_locally(client, respx_mock):
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params.get("search_text") == "jaipur"
        # The server returns a loosely matched page; the client must tighten it.
        return httpx.Response(200, json={"code": 0, "items": [ITEM_A, ITEM_B]})

    respx_mock.get(f"{API_BASE}/items").mock(side_effect=handler)

    matches = await client.search_items("jaipur")

    assert [item.sku for item in matches] == ["LK-BED-001"]


async def test_search_items_by_sku(client, respx_mock):
    respx_mock.get(f"{API_BASE}/items").mock(
        return_value=httpx.Response(200, json={"code": 0, "items": [ITEM_A, ITEM_B]})
    )

    matches = await client.search_items("lk-rug-005")

    assert [item.item_id for item in matches] == ["i2"]


async def test_search_items_with_blank_query_makes_no_call(client, respx_mock):
    route = respx_mock.get(f"{API_BASE}/items").mock(return_value=httpx.Response(200, json={}))

    assert await client.search_items("   ") == []
    assert route.call_count == 0


async def test_search_sales_orders_matches_customer_and_reference(client, respx_mock):
    other = dict(ORDER, salesorder_id="so2", customer_name="Priya Nair", reference_number="REF-X")
    respx_mock.get(f"{API_BASE}/salesorders").mock(
        return_value=httpx.Response(200, json={"code": 0, "salesorders": [ORDER, other]})
    )

    matches = await client.search_sales_orders("aarav")

    assert [order.salesorder_id for order in matches] == ["so1"]
