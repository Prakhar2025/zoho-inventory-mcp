# Decision Records

Short records of the choices that shape this project, so future agents do not re-litigate them.

## ADR-001: Assignment option 3 (merchant connector)

Chosen over option 1 (reverse-engineer an API) and option 2 (voice agent for autopay recovery).

- Option 3 is the closest to the actual FDE job: building connectors between merchant tools and
  agents is what an Agent Studio FDE does.
- It has the most objective rubric (auth, primitives, rate limits, MCP spec, capabilities doc), so
  every bullet can be deliberately exceeded.
- Option 1 draws the classic portfolio move; option 2 draws the "voice AI" crowd. Option 3 is the
  most work, so it is the least crowded and the most production-flavored.
- Option 2 was considered seriously (it is the most Razorpay-flavored problem). It is achievable
  nearly free via provider trial credits (Retell or Vapi signup credits, or the Twilio trial, calling
  only our own verified number). AWS alone does not make it free: Amazon Connect is per-minute paid
  and India outbound has verification friction, while Lex and Polly free tiers only cover the speech
  pieces. The deciding factors: the demo's quality would depend on a third-party voice provider and
  on trial credits not expiring, and the option is the most crowded. Payments-domain depth can be
  shown in option 3 docs instead.

## ADR-002: Zoho Inventory as the merchant tool

Chosen over Freshdesk, WooCommerce, Unicommerce.

- Zoho Inventory has a **permanent free plan** with API access (about 1,000 calls per day, 5
  concurrent). The evaluator can reproduce the demo any time without a card and without a 21-day
  trial expiring mid-review (the Freshdesk risk).
- It is OAuth 2.0 with refresh tokens, which demonstrates a real auth flow rather than a static API
  key.
- Orders and inventory fit a payments company's commerce-agent story; Zoho's merchant base is
  heavily Indian SMB, matching Razorpay's segment.
- WooCommerce would have required a local WordPress install (Docker is banned on this machine and
  downloads cost mobile data). Unicommerce needs a paid/demo account that is hard to obtain.

## ADR-003: Python 3.12 and FastMCP

- The strongest existing production language for this user is Python, and the MCP Python SDK
  (`mcp`, with FastMCP) is the official, maintained path.
- Tool descriptions inside the server are treated as the tool specification: they live in code and
  cannot drift from a separate document.

## ADR-004: Local stdio MCP server first, AWS Lambda later

- The rubric asks for an MCP tool specification "or equivalent": a runnable local server already
  exceeds that. Build and verify that first.
- The optional phase 7 Lambda deployment (zip package, Function URL, Secrets Manager, CloudWatch,
  CloudFormation) shows production thinking. It is pure Python, so no Docker is needed.

## ADR-005: Demo agent via Strands Agents SDK on Bedrock

- The user has an open pull request on the Strands Agents SDK (AWS's open-source agent SDK), so the
  demo agent doubles as evidence of genuine agent-infrastructure experience.
- Bedrock is already available in the user's AWS account.

## ADR-006: Read-only connector

- The assignment only asks the agent to read. Staying read-only is the safest correct scope and
  lets the capabilities doc make a strong safety statement: least-privilege scopes, no write path,
  audit log, explicit "will never do" list.

## ADR-007: No Docker anywhere

- Docker is broken on this machine and downloads consume phone mobile data. All infrastructure
  choices avoid it (cloud SaaS tool, zip-based Lambda deploy, local venv).
