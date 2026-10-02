# Demo transcript: merchant questions against the LoomKart org

Answers were produced by a Strands agent backed by AWS Bedrock, using only
the six read-only MCP tools exposed by this connector. Every tool call is
recorded with arguments and timings in logs/audit.jsonl.

## Merchant

> What products do we sell, and what do they cost? One line per product.

**Agent:** Here are the products we sell and their prices:

- Ajrah Print Doormat - ₹799
- Block Print Napkin Set (6 pcs) - ₹449
- Chikankari Cushion Cover (Single) - ₹599
- Dhurrie Jute Rug (5x8 ft) - ₹2,799
- Handloom Cotton Curtains (Set of 2) - ₹1,249
- Jaipur Block Print Bedsheet (Queen) - ₹1,899
- Kalamkari Table Runner - ₹649
- Warli Art Cushion Covers (Set of 5) - ₹999

## Merchant

> Find any orders from Sneha Iyer and tell me exactly what she bought.

**Agent:** Sneha Iyer has placed two orders:

**Order SO-00010 (2026-09-27)**:
- 1 × Dhurrie Jute Rug (5x8 ft) @ ₹2,799
- 1 × Warli Art Cushion Covers (Set of 5) @ ₹999

**Order SO-00004 (2026-09-12)**:
- 2 × Warli Art Cushion Covers (Set of 5) @ ₹999 each

## Merchant

> Which orders are still in draft status and who placed them?

**Agent:** There are currently two orders in draft status:

1. Order SO-00012 placed by Ananya Rao on 2026-10-01 (total: ₹1,448.00)
2. Order SO-00011 placed by Vikram Singh on 2026-09-29 (total: ₹1,899.00)
