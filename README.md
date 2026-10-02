# Zoho Inventory MCP Connector

A read-only Model Context Protocol (MCP) connector that lets an AI agent read items and sales
orders from a Zoho Inventory organization: with proper OAuth 2.0, rate-limit handling, and an
explicit statement of what the agent can and cannot do.

Built as the assignment submission for the **Forward Deployed Engineer, Agent Studio** role at
Razorpay. The scenario behind it: a D2C merchant on WhatsApp and email wants their commerce agent
to answer "where is my order?" and "is this item in stock?" without a human logging into Zoho.

## Why Zoho Inventory

Zoho Inventory runs a large share of Indian SMB merchants, it has a permanent free plan (so the
evaluator can reproduce everything without a card or a trial that expires), and its API is OAuth 2.0
with refresh tokens, which exercises a real auth flow rather than a static API key.

## Status

Work in progress. The roadmap and current phase live in [docs/02-ROADMAP.md](docs/02-ROADMAP.md).

## Documentation

| Doc | Purpose |
| --- | --- |
| [Project brief](docs/00-PROJECT-BRIEF.md) | Role context, assignment text, constraints |
| [Architecture](docs/01-ARCHITECTURE.md) | Components, data flow, security posture |
| [Roadmap](docs/02-ROADMAP.md) | Phases with acceptance criteria and status |
| [Handover](docs/03-HANDOVER.md) | How any agent can continue this work |
| [Decisions](docs/04-DECISIONS.md) | Choice records with rationale |

## Quickstart

Coming in phase 6, when the connector is complete. The short version will be: create a free Zoho
Inventory account, run the OAuth helper script, seed fictional demo data, start the MCP server, and
point any MCP client at it.
