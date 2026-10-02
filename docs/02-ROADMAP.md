# Roadmap

Source of truth for progress. Check a box only when its acceptance criteria are met, and keep the
status table at the bottom in sync with docs/03-HANDOVER.md.

## P0: repo, docs, scaffold

- [x] git init, .gitignore, .env.example, pyproject.toml
- [x] docs: brief, architecture, roadmap, handover, decisions
- [x] package skeleton (`src/zoho_inventory_mcp` with working config module)
- [x] initial commit

## P1: Zoho setup, OAuth, seed data

Goal: a free Zoho Inventory org (India data center) with fictional data, and the connector able to
authenticate.

- [x] User creates a Zoho account and a Zoho Inventory org on the IN data center (free plan)
- [x] Create an API Console Self Client, write down client id and secret in `.env`
- [x] `scripts/get_refresh_token.py`: generates the grant-code URL with read scopes, exchanges the
      code for tokens, saves the refresh token into `.env`
- [x] Record the exact OAuth scope strings that worked, and the API base URL for the IN DC, in
      docs/03-HANDOVER.md
- [x] `scripts/seed_demo_data.py`: creates about 8 items and 12 sales orders (mixed statuses:
      fulfilled, unfulfilled, overdue, cancelled) plus customer names, via the API
- [x] Verify the raw API works: one manual GET for items and one for sales orders

Acceptance: seed script runs green, data visible in the Zoho UI, a raw authenticated GET works.

## P2: connector core

Goal: a clean, tested library: the part a senior engineer would actually review.

- [x] `auth.py`: token cache with expiry awareness, auto-refresh, one-flight refresh guard
- [x] `rate_limiter.py`: serial requests with minimum spacing, plus 429 handling honoring
      `Retry-After` with exponential backoff and jitter
- [x] `client.py`: httpx with timeouts, pagination helper, org id header, error mapping to the
      taxonomy in `errors.py`
- [x] `models.py`: normalized Item and SalesOrder models (documented field subsets)
- [x] Primitives: list/get/search for items and sales orders, with filters
- [x] Unit tests (respx mocks) for auth refresh, rate limiting, pagination, error mapping
- [x] `scripts/smoke_live.py`: quick live check against the real org

Acceptance: `py -3.12 -m pytest` green, smoke script prints real (fictional) data.

## P3: MCP server

Goal: the deliverable itself, a runnable MCP server.

- [x] `server.py` with FastMCP: the six read-only tools with LLM-oriented descriptions
- [x] Structured error returns (no stack traces leak to the agent)
- [x] JSONL audit log of every tool call
- [x] Tests: list tools, call each tool (via the MCP client against the server, mocked HTTP)

Acceptance: `py -3.12 -m zoho_inventory_mcp.server` starts; an MCP client can list and call tools.

## P4: demo agent on Bedrock

Goal: end-to-end proof that an Agent-Studio-style agent can use the connector.

- [ ] Add `strands-agents` dependency (accept the boto3 download, one time, a few MB)
- [ ] `agent/demo.py`: Strands agent + MCP client + Bedrock model available in the user's account
- [ ] Three scripted merchant questions, transcript saved to `agent/transcript.md`

Acceptance: one command runs the demo; transcript shows correct tool usage and answers.

## P5: evals

Goal: measurable quality, the differentiator almost nobody else ships.

- [ ] `evals/cases.yaml`: 15 to 20 cases (question, expected tool sequence, answer assertions)
- [ ] `evals/run_evals.py`: runs cases, prints a pass-rate table
- [ ] Document any known-fail cases honestly

Acceptance: one command prints the eval report.

## P6: final docs and demo video

Goal: the package the evaluator actually reads first.

- [ ] Full README rewrite: merchant story up top, 10-minute quickstart, architecture summary
- [ ] `docs/CAPABILITIES.md`: what the agent can and cannot do (the required short document)
- [ ] Limitations and scale notes (what breaks at 10x, and the long-term fix)
- [ ] "How we would measure impact" section (deflection rate, time-to-answer, tickets avoided)
- [ ] Demo video script, user records a 2 to 3 minute video, link goes at the top of the README

Acceptance: a fresh clone walkthrough succeeds following only the README.

## P7: AWS Lambda deploy (optional differentiator)

Goal: show what production looks like, beyond the local stdio server.

- [ ] CloudFormation template: Lambda (zip, no Docker), Function URL, Secrets Manager, CloudWatch
- [ ] Remote (streamable HTTP) MCP endpoint works from an MCP client
- [ ] Teardown script; document costs (should be pennies on free tier)

Acceptance: an MCP client config pointing at the Function URL lists and calls tools.

## P8: submission

Goal: convert work into a winning application.

- [ ] Draft the four form answers (LLM project with guardrails and evals: Antares; language:
      Python; on-site: yes; experience: honest)
- [ ] Final secrets sweep (no tokens anywhere, git history included)
- [ ] Push to GitHub as a public repo (ask the user first), or prepare a Drive folder fallback
- [ ] Fill the form only after the link is live; note the 48-hour rule

Acceptance: form submitted with a working, accessible link.

## Status table (keep in sync with docs/03-HANDOVER.md)

| Phase | Status | Notes |
| --- | --- | --- |
| P0 | done | scaffold and docs committed |
| P1 | done | auth verified live, org seeded with fictional data |
| P2 | done | 34 unit tests green; live smoke passed against the seeded org |
| P3 | done | protocol smoke over stdio: 6 read-only tools exposed and called |
| P4 | not started | |
| P5 | not started | |
| P6 | not started | |
| P7 | not started | optional |
| P8 | not started | |
