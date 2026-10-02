# Eval report

Run: 2026-10-02T04:53:09+00:00 | model: global.amazon.nova-2-lite-v1:0 | result: 16/16 passed

| Case | Result | Tools used | Notes |
| --- | --- | --- | --- |
| catalog_overview | PASS | inventory_list_items | - |
| catalog_full_listing | PASS | inventory_list_items | - |
| catalog_count | PASS | inventory_list_items | - |
| item_search_by_name | PASS | inventory_search_items | - |
| item_search_by_sku | PASS | inventory_search_items | - |
| item_get_full_details | PASS | inventory_get_item, inventory_search_items | - |
| negative_product_query | PASS | inventory_search_items | - |
| orders_by_customer | PASS | orders_get_sales_order, orders_search_sales_orders | - |
| orders_by_customer_totals | PASS | orders_search_sales_orders | - |
| draft_orders | PASS | orders_list_sales_orders | - |
| confirmed_awaiting_fulfillment | PASS | orders_list_sales_orders | - |
| recent_orders | PASS | orders_list_sales_orders | - |
| order_by_number | PASS | orders_get_sales_order | - |
| negative_customer_query | PASS | orders_search_sales_orders | - |
| confirmed_order_value | PASS | orders_list_sales_orders | - |
| items_within_customer_orders | PASS | orders_get_sales_order, orders_search_sales_orders | - |

## Answers

### catalog_overview (PASS)

> What products do we sell, and what do they cost? One line per product.

We sell the following 8 items:

- Ajrah Print Doormat LK-DOOR-008 costs ₹799
- Block Print Napkin Set (6 pcs) LK-NAP-006 costs ₹449
- Chikankari Cushion Cover (Single) LK-CUS-007 costs ₹599
- Dhurrie Jute Rug (5x8 ft) LK-RUG-005 costs ₹2799
- Handloom Cotton Curtains (Set of 2) LK-CUR-002 costs ₹1249
- Jaipur Block Print Bedsheet (Queen) LK-BED-001 costs ₹1899
- Kalamkari Table Runner LK-TAB-003 costs ₹649
- Warli Art Cushion Covers (Set of 5) LK-CUS-004 costs ₹999

### catalog_full_listing (PASS)

> List every product in the catalog with its price.

Here are all the products in the LoomKart catalog with their prices:

1. **Ajrah Print Doormat** - ₹799.00 (SKU: LK-DOOR-008)
2. **Block Print Napkin Set (6 pcs)** - ₹449.00 (SKU: LK-NAP-006)
3. **Chikankari Cushion Cover (Single)** - ₹599.00 (SKU: LK-CUS-007)
4. **Dhurrie Jute Rug (5x8 ft)** - ₹2,799.00 (SKU: LK-RUG-005)
5. **Handloom Cotton Curtains (Set of 2)** - ₹1,249.00 (SKU: LK-CUR-002)
6. **Jaipur Block Print Bedsheet (Queen)** - ₹1,899.00 (SKU: LK-BED-001)
7. **Kalamkari Table Runner** - ₹649.00 (SKU: LK-TAB-003)
8. **Warli Art Cushion Covers (Set of 5)** - ₹999.00 (SKU: LK-CUS-004)

### catalog_count (PASS)

> How many products are in the catalog?

The LoomKart catalog contains **8 active products**.

### item_search_by_name (PASS)

> Do we stock jaipur bedsheets?

Sorry, we don't have any "jaipur bedsheets" in our current inventory. Would you like me to check for other types of bedsheets or help you find something similar?

### item_search_by_sku (PASS)

> Look up item LK-RUG-005 for me.

Got it! Here are the details for item LK-RUG-005:

**Item ID:** 4209924000000040026  
**Name:** Dhurrie Jute Rug (5x8 ft)  
**Rate:** ₹2,799.00  
**Status:** Active  

Let me know if you need anything else about this item!

### item_get_full_details (PASS)

> I have the SKU LK-BED-001 but I need the internal item id and the exact rate. Look it up properly: first find the item, then fetch it by id.

The internal item id for SKU LK-BED-001 is **4209924000000035032** and the exact rate is **₹1,899.00**.

### negative_product_query (PASS)

> Do we sell mobile phones?

We don't sell mobile phones. Our catalog focuses on home goods and related products.

### orders_by_customer (PASS)

> Find any orders from Sneha Iyer and tell me exactly what she bought.

Sneha Iyer has two confirmed orders:

**Order SO-00010 (2026-09-27):**
- 1 x Dhurrie Jute Rug (5x8 ft) - ₹2,799.00
- 1 x Warli Art Cushion Covers (Set of 5) - ₹999.00

**Order SO-00004 (2026-09-12):**
- 2 x Warli Art Cushion Covers (Set of 5) - ₹1,998.00

### orders_by_customer_totals (PASS)

> Show me all orders from Ananya Rao with their totals.

Ananya Rao has 2 orders:

- LK-SO-001-20261001 (SO-00012) for ₹1,448.00
- LK-SO-015-20260917 (SO-00006) for ₹4,247.00

### draft_orders (PASS)

> Which orders are still in draft status and who placed them?

There are currently two draft orders:

1. Order LK-SO-001-20261001 (SO-00012) placed by **Ananya Rao** on 2026-10-01, total ₹1,448.00
2. Order LK-SO-003-20260929 (SO-00011) placed by **Vikram Singh** on 2026-09-29, total ₹1,899.00

### confirmed_awaiting_fulfillment (PASS)

> Which customers have confirmed orders that are not yet fulfilled?

All 10 confirmed orders are unfulfilled. The customers with confirmed orders are:

- Sneha Iyer (2 orders)
- Rohan Mehta (2 orders)
- Priya Nair (2 orders)
- Aarav Sharma (2 orders)
- Ananya Rao (1 order)
- Vikram Singh (1 order)

### recent_orders (PASS)

> Show me the 3 most recent orders.

Here are the 3 most recent orders:

1. **SO-00012** - Ananya Rao, 2026-10-01, Status: draft, Total: ₹1,448.00  
2. **SO-00011** - Vikram Singh, 2026-09-29, Status: draft, Total: ₹1,899.00  
3. **SO-00010** - Sneha Iyer, 2026-09-27, Status: confirmed, Total: ₹3,798.00

### order_by_number (PASS)

> Look up order SO-00005: who placed it, and what are its status and total?

Order SO-00005 was placed by **Vikram Singh**. Its status is **confirmed**, and the total is **$1,347.00**.

### negative_customer_query (PASS)

> Show me all orders from Ramesh Dubey.

I checked our order system and found no sales orders from a customer named Ramesh Dubey. 

If you have any additional details (such as an order number, phone number, or approximate order date) that might help locate the order, please share them and I’ll search again.

### confirmed_order_value (PASS)

> What is the total value of all confirmed orders together?

The total value of all confirmed orders is **$19,977.00**.

### items_within_customer_orders (PASS)

> Which LoomKart items appear in Vikram Singh's orders?

Vikram Singh has ordered the following LoomKart items:

- Jaipur Block Print Bedsheet (Queen)
- Block Print Napkin Set (6 pcs)
