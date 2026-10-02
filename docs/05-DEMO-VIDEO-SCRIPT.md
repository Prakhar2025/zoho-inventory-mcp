# Demo Video Script (2 to 3 minutes)

Recording notes: 1080p, terminal at 16 to 18pt font, close every notification. Record in
one take per section and cut. Speak the narration lines naturally; they are a base, not a
teleprompter.

## 0:00 to 0:20: The hook (screen: Zoho Inventory org)

Show the seeded LoomKart org (Sales Orders list) while talking.

> "This is LoomKart, a home-goods merchant running on Zoho Inventory. Every time their
> team asks something simple, like what did Sneha Iyer buy, someone has to log in and
> click around. This connector fixes that: it gives a commerce agent safe, read-only
> access to this data through MCP."

## 0:20 to 0:40: What I built (screen: README or architecture diagram)

> "It is a production-grade connector: an async Zoho Inventory client with OAuth 2.0 and
> single-flight token refresh, client-side rate limiting with backoff, a structured error
> taxonomy, six read-only MCP tools, and a JSONL audit log for every call."

## 0:40 to 1:25: The live demo (screen: terminal)

Run `python agent/demo.py` and let it answer the Sneha Iyer question live. Show the
answer citing order numbers.

> "Watch the agent answer three merchant questions using only the tools. It searches
> orders, pulls line items, and cites order numbers, because the system prompt makes it
> cite. Then I ask for draft orders and it uses the status filter."

Show `logs/audit.jsonl` (open in editor): every call with arguments and timings.

> "Every tool call is audited: arguments, duration, outcome. Merchants can trust what
> they can verify."

## 1:25 to 2:00: Engineering quality (screen: terminal)

Run `python -m pytest -q` (39 passed), then `python evals/run_evals.py` (16/16).

> "39 hermetic unit tests cover the token refresh race, retry policy, pagination, and
> error mapping. And because an agent demo without evals is just a vibe, there is a
> 16-case eval suite scoring real merchant questions on tool usage and answer facts.
> Current run: 16 out of 16."

Mention one design point:

> "One example of agent-first design: the agent kept asking for orders by merchant
> number, not Zoho's internal id. So the get tool now accepts id, order number, or
> reference, with a search fallback. The connector speaks merchant, not Zoho."

## 2:00 to 2:30: Safety and close (screen: CAPABILITIES.md)

> "Everything is read-only, enforced by scopes, tool annotations, and the code itself.
> The capabilities doc states exactly what the agent can and cannot do. What I would add
> next for Agent Studio: a hosted HTTP transport, multi-tenant token management, and
> write tools gated by human approval. Repo and eval report are in the description."
