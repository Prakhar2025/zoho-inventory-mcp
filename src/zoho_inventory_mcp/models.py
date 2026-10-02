"""Normalized read models for items and sales orders.

Only fields useful to an agent are kept. Unknown upstream fields are ignored
so Zoho can add fields without breaking the connector.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class Item(BaseModel):
    """A product in the Zoho Inventory catalog."""

    model_config = ConfigDict(extra="ignore")

    item_id: str
    name: str
    sku: str | None = None
    rate: float | None = None
    status: str | None = None
    description: str | None = None
    stock_on_hand: float | None = None
    unit: str | None = None


class LineItem(BaseModel):
    """A single line of a sales order."""

    model_config = ConfigDict(extra="ignore")

    item_id: str | None = None
    name: str | None = None
    quantity: float | None = None
    rate: float | None = None
    item_total: float | None = None


class SalesOrder(BaseModel):
    """A customer order in Zoho Inventory."""

    model_config = ConfigDict(extra="ignore")

    salesorder_id: str
    salesorder_number: str | None = None
    reference_number: str | None = None
    date: str | None = None
    status: str | None = None
    customer_name: str | None = None
    total: float | None = None
    currency: str | None = None
    line_items: list[LineItem] = Field(default_factory=list)
