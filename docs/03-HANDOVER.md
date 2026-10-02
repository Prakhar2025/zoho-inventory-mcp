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
| P1 | blocked on user | user must create the Zoho account first |
| P2 to P8 | not started | see roadmap |

## Immediate next action

Phase P1, step 1 (user action, about 10 minutes):

1. Sign up at https://www.zoho.com/in/inventory/ (India data center) and create an organization.
   Choose the Free plan when asked. No card needed.
2. Add a few fictional customers, items, and sales orders by hand if the agent has not yet written
   `scripts/seed_demo_data.py`, or wait for the script (preferred: wait, the script seeds
   everything consistently).
3. Go to https://api-console.zoho.in, choose Self Client, create one, and copy the client id and
   client secret into `.env` (copy `.env.example` to `.env` first).

Phase P1, step 2 (agent action, right after step 1): write `scripts/get_refresh_token.py` (grant-code
URL with read scopes, exchange code for tokens, print/save refresh token), then
`scripts/seed_demo_data.py`. Verify raw API calls. Record the working scope strings and base URLs in
the "Verified facts" section below.

## Verified facts (fill in as phases complete; trust nothing not written here)

- OAuth token endpoint (IN DC): `https://accounts.zoho.in/oauth/v2/token` (to be verified in P1)
- Inventory API base (IN DC): `https://www.zohoapis.in/inventory/v1` (to be verified in P1)
- Working OAuth scopes: not yet verified
- Free plan limits: 1,000 API calls per day, 5 concurrent (source: Zoho KB, re-verify against
  live behavior in P1)
- Actual model id used for the Bedrock demo agent: decided in P4, record here

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
