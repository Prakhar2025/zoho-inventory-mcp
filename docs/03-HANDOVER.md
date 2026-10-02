# Handover for Continuation Agents

Audience: any agent (ZCode, Antigravity Gemini 3.8 Flash or 3.1 Pro, or a human) continuing this
project with no prior context. Follow this file exactly. It exists so the project can be finished by
someone who was not here when it started.

## Read in this order

1. `docs/00-PROJECT-BRIEF.md` (what this is and why)
2. `docs/02-ROADMAP.md` (find the first unchecked phase; that is your job)
3. `docs/01-ARCHITECTURE.md` (how the pieces fit)
4. `docs/04-DECISIONS.md` (why things are the way they are, so you do not re-litigate them)

## Environment facts (do not rediscover these the hard way)

- Windows 11, Git Bash shell. The project path contains a space:
  `C:\Users\prakh\projects\FDE Razorpay`. Always quote it.
- Python 3.12.10 is available as `py -3.12`. The bare `python` command is NOT on PATH.
  Create the venv with: `py -3.12 -m venv .venv` then `source .venv/Scripts/activate`.
- **No Docker.** It is broken on this machine. Never suggest docker, docker-compose, or images.
- **The user is on phone mobile data.** No large downloads, no model weights, no heavy installs.
  Acceptable: pip packages up to a few MB (boto3 for the phase 4 agent is fine, one time).
- **Free tier only.** No paid services, no card details anywhere.
- **No em dash or en dash characters anywhere**: chat, docs, code, commit messages.
  Use periods, commas, colons, or parentheses.
- **No secrets in git.** `.env` is gitignored. `.env.example` is the checked-in template.
- AWS account exists with Bedrock access (used before by other projects). GitHub account exists
  (Prakhar2025). **Do not push to GitHub without asking the user first.**
- All demo data must be fictional.

## Working conventions

- Work in phases from `docs/02-ROADMAP.md`. Complete a phase, verify its acceptance criteria, then
  check its boxes and update the status table in both the roadmap and this file.
- Commit per logical step. Message style: `P2: add rate limiter with backoff and jitter`.
- Run tests before committing anything that has tests:
  `py -3.12 -m pytest` and `py -3.12 -m ruff check .`
- When you finish a step, write the next agent's next action in the "Immediate next action"
  section below, as if instructing a stranger.

## Status snapshot

| Phase | Status | Notes |
| --- | --- | --- |
| P0 | done | scaffold and docs committed (first commit) |
| P1 | done | auth verified live, LoomKart org seeded (see Verified facts) |
| P2 | done | see roadmap and Verified facts |
| P3 | done | protocol smoke over stdio passed |
| P4 | done | demo agent live, transcript in agent/transcript.md |
| P5 | done | evals 16/16 pass, report in evals/report.md |
| P6 to P8 | not started | see roadmap |

## Immediate next action

Phase P6 (mostly agent action): final docs and demo video.

1. Rewrite README.md: merchant story up top, 10-minute quickstart, architecture summary,
   eval badge numbers (16/16), and the demo video link placeholder.
2. Write docs/CAPABILITIES.md: what the agent can and cannot do (the assignment's
   required short document).
3. Write the demo video script; the USER records the 2 to 3 minute video and the link
   goes at the top of the README.
4. P7 (optional, needs user go-ahead: deploys into their AWS account) and P8 submission
   (user flips the repo to public and fills the form) follow.

## Verified facts (fill in as phases complete; trust nothing not written here)

- OAuth token endpoint (IN DC), verified live: `https://accounts.zoho.in/oauth/v2/token`
- Inventory API base (IN DC), verified live: `https://www.zohoapis.in/inventory/v1`
- The `/organizations` endpoint returns `organization_id` (not `id`); org id is stored in `.env`
- Org-scoped endpoints take the org id via the `Organization-Id` header (verified) or an
  `organization_id` query parameter
- Working read scopes (connector token): settings.READ, items.READ, salesorders.READ,
  contacts.READ under the `ZohoInventory.` prefix
- Seeding scopes needed READ **and** CREATE per entity; create-only scopes fail list calls with
  HTTP 401 code 57 ("not authorized")
- Sales order status transition endpoint, verified live: `POST /salesorders/{id}/status/confirmed`
- API-created sales orders default to status `draft`; confirming is a separate call
- Grant codes from the Self Client "Generate Code" tab are single use and expire in 10 minutes
- Free plan live behavior: 1 call per second spacing produced zero 429s while seeding ~40 calls
- Seeded demo data: 6 fictional customers, 8 items (LK- prefixes), 12 sales orders spread over
  the last 4 weeks (10 confirmed, 2 draft), reference numbers `LK-SO-*`
- The seeding token lives in `.env` as `ZOHO_SEED_REFRESH_TOKEN` (write scopes, revocable); the
  connector token `ZOHO_REFRESH_TOKEN` stays read-only
- The pip `mcp` package is 2.x: FastMCP was renamed to MCPServer
  (`from mcp.server.mcpserver import MCPServer`); tool annotations use snake_case
  attributes in Python (read_only_hint) and camelCase only on the wire
- Zoho free-plan orgs do not return stock levels for API-created items
  (initial_stock comes back empty), so Item.stock_on_hand stays optional and no
  doc promises stock numbers
- Bedrock model in use: `global.amazon.nova-2-lite-v1:0` (first-party, no marketplace
  subscription; Anthropic models are blocked on this account by INVALID_PAYMENT_INSTRUMENT)
- Get primitives accept friendly identifiers: sales orders by id, SO number, or merchant
  reference; items by id or SKU (search fallback after a 404, unit tested)
- Eval suite: `.venv/Scripts/python evals/run_evals.py`; 16/16 cases passed on 2026-10-02;
  report committed at evals/report.md
- Actual model id used for the Bedrock demo agent: global.amazon.nova-2-lite-v1:0

## Pitfalls learned so far

- Zoho documentation examples often show the US DC (`inventory.zoho.com`). The Indian org uses
  `zohoapis.in` domains. Handle both via `ZOHO_DC` in config.
- Zoho access tokens last about 1 hour; the refresh token is long lived. Exchange the grant code
  exactly once; the grant code itself expires within a few minutes.
- Never fire concurrent requests at Zoho on the free plan: the connector enforces serial requests
  with spacing by design. Do not "optimize" that away.
- pip installs can fail once on mobile data; retry before investigating anything else.

## If context is running low

Stop at a phase boundary, check the boxes for what is done, update the status tables, write the
exact next action in this file, and commit with a clear message. The next agent takes it from there.
