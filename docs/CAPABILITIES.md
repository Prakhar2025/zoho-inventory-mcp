# What the Agent Can and Cannot Do

This is the capability statement for the connector shipped in this repository: six
read-only MCP tools through which an Agent-Studio-style agent can read a Zoho Inventory
organization. It is written for two audiences at once: the merchant deciding whether to
trust the agent, and the engineer wiring it into a deployment.

## What the agent CAN do

| Tool | What it gives the agent |
| --- | --- |
| `inventory_list_items` | Browse the product catalog page by page (id, name, SKU, rate) |
| `inventory_get_item` | Fetch one product by internal id or by merchant SKU |
| `inventory_search_items` | Find products by keyword in name or SKU |
| `orders_list_sales_orders` | List customer orders, optionally filtered by status (draft, confirmed, and so on) |
| `orders_get_sales_order` | Fetch one order by internal id, order number (SO-00005), or merchant reference, including line items, quantities, and totals |
| `orders_search_sales_orders` | Find orders by customer name or order number |

With these six tools an agent can answer the questions that drive most merchant support
load: what do we sell, what does it cost, did customer X order item Y, what is order Z's
status, how many orders are waiting, what was the total value of a period.

## What the agent CANNOT do (by design)

- **It can never modify anything.** No create, update, delete, cancel, or fulfillment.
  This is enforced three independent ways: the OAuth scopes are read-only, every MCP tool
  is annotated `readOnlyHint`, and the connector library contains no write code paths at
  all.
- **It can never see another organization.** Every request carries one org id from local
  configuration; there is no tool parameter that can redirect it.
- **It can never act outside the six tools.** Contacts, purchase orders, invoices, and
  settings are not exposed even though the data center account can see them.
- **It can never retry blindly.** Error payloads carry a `retryable` flag: rate-limit
  errors include `retry_after_seconds` and mean "wait, then retry"; auth errors mean
  "stop"; not-found errors mean "rephrase the query".
- **It can never call untraced.** Every tool invocation is appended to a JSONL audit log:
  timestamp, tool, arguments, duration, outcome. No tokens or secrets are ever logged.

## Data handling

- The demo organization contains fictional data only; nothing in this repository touches
  real customer data.
- The connector holds a read-only refresh token in local configuration (`.env`, gitignored).
  The separate seeding token (write scopes, used once to create the fictional catalog)
  should be revoked after setup and is deliberately not the connector's token.
- Order and customer records may contain personal data (names, phone numbers) in a real
  deployment. The models pass through only the fields an agent needs; a production rollout
  should add field-level redaction policies per merchant.

## What a production deployment would add

1. **Transport**: the same server behind a streamable HTTP endpoint with authentication,
   instead of local stdio (the tool layer is transport-agnostic).
2. **Multi-tenancy**: one read-only token per merchant org in a secrets manager, with
   per-tenant rate budgets so one merchant's usage cannot exhaust another's.
3. **Field-level PII controls**: per-merchant redaction of contact fields in tool output.
4. **Write tools, only with human approval**: fulfillment or cancellation flows would be
   separate tools gated by explicit confirmation, never part of a read-only connector.
5. **Monitoring**: the audit log is already structured for ingestion; add alerting on
   error rates and token refresh failures.
