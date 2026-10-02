# Project Brief

## Context

Razorpay is hiring a **Forward Deployed Engineer (FDE) for Agent Studio** in Bangalore (on-site),
sourced from a LinkedIn post by Astha Singh (Talent Scout at Razorpay). The process has no resume
screen: pick one of three assignments, ship it, and submit it through a Google Form. The form says
work must be submitted within 48 hours of receiving the assignment, so the rule here is: build and
verify everything first, then fill the form once the submission link is live.

The role: technical owner of the merchant relationship. Sit with merchants, find the real problem
behind the ask, design the fix, build the first working version, and prove whether it moved the
metric. Equal parts engineer, consultant, and builder.

## The assignment we chose (verbatim from the form)

> Choose Freshdesk, Zoho Inventory, WooCommerce, or Unicommerce. Build a connector that enables an
> Agent Studio agent to read tickets, orders, or inventory from the selected tool. Include a working
> OAuth or API-key authentication flow, suitable list/get/search primitives, rate-limit handling, an
> MCP tool specification or equivalent, and a short document describing what the agent can and
> cannot do.

## Why option 3 (summary, details in docs/04-DECISIONS.md)

1. It is the actual job: an FDE on Agent Studio builds merchant connectors. The evaluator reads the
   submission and sees day-1 work.
2. It has the most objective rubric, so every bullet can be hit and then exceeded one level.
3. It is the least crowded option: option 1 is the classic student move and option 2 attracts the
   "voice AI" crowd. Most applicants skip option 3 because it is the most work.
4. The tool choice, Zoho Inventory, serves Indian SMB merchants, which is Razorpay's core segment.
5. It plays to existing strengths: MCP familiarity (from work on the Strands Agents SDK) and
   read-only, safety-first design taste (from the Antares project).

## Deliverables checklist (from the assignment text)

- [ ] Working OAuth authentication flow (Zoho is OAuth 2.0 with refresh tokens: full flow, not a
      static key)
- [ ] Suitable list/get/search primitives (items and sales orders, with pagination and filters)
- [ ] Rate-limit handling (client-side token bucket, plus 429 handling honoring Retry-After)
- [ ] MCP tool specification (we ship a real, runnable MCP server, which exceeds "or equivalent")
- [ ] Short document describing what the agent can and cannot do (docs/CAPABILITIES.md, phase 6)

## Hard constraints

- **No Docker.** It does not work reliably on this machine. Never suggest it.
- **Phone mobile data only.** No large downloads. Cloud SaaS and lightweight Python deps only.
- **Free tier only, no card.** Zoho Inventory free plan: permanent, API access included.
- **Python 3.12** via `py -3.12` on Windows (Git Bash). `python` is not on PATH.
- **No em dash or en dash characters anywhere**, in any file or message.
- **No secrets in the repo.** `.env` is gitignored; `.env.example` is the template.
- Fictional demo data only. No real customer data anywhere.

## Non-goals

- Write access to Zoho. This connector is deliberately read-only (safety posture, documented).
- Multi-tenant support. One org, by design, stated in the capabilities doc.
- Production hosting in early phases. AWS Lambda deployment is an optional differentiator phase.

## Success criteria

1. An evaluator can clone the repo, follow the README with their own free Zoho account, and reach a
   working demo in under 10 minutes.
2. Every rubric bullet is exceeded one level beyond the ask.
3. The whole package (docs, demo video, evals) makes the FDE mindset visible: problem, fix, metric.
