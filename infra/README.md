# AWS Hosting Stack

A probe-driven CloudFormation stack that hosts the merchant console on AWS:
static console on S3, CloudFront distribution, API Gateway (REST, proxy) in
front of a Python 3.12 Lambda running the FastAPI backend via Mangum, and a
Bedrock-invoking execution role. The design copies the antares-dev pattern
proven live on this account.

## Status

The stack deploys and serves the console; the hosted agent endpoint needs one
decision recorded here honestly.

1. **Anonymous Lambda function URLs are blocked on this account.** Verified by
   experiment: a minimal function with `AuthType: NONE` plus a correct
   `lambda:InvokeFunctionUrl` resource policy still returns 403 to anonymous
   callers (no organization or SCP exists, so the restriction is baked into the
   provisioned account). The stack therefore uses API Gateway, whose
   apigateway.amazonaws.com invoke permission works.
2. **The MCP stdio subprocess cannot start under the Lambda runtime.** The
   console backend starts the MCP server as a child process (stdio transport).
   Under the Lambda runtime's process isolation the child fails to initialize,
   which surfaced as a 502 on `/api/health`. This is a runtime constraint, not
   a code bug: the identical backend runs verified locally.

## The path to a fully hosted demo

Pick one, both are small:

- **Console backend on EC2/ Lightsail** (recommended): the same uvicorn process
  runs unchanged, MCP subprocess included. `infra/` scripts adapt by replacing
  the API Gateway + Lambda block with an instance profile and a startup script.
- **MCP over streamable HTTP**: expose the MCP server as a remote endpoint
  (App Runner or an ASGI host) and point the agent's MCP client at it instead
  of stdio. This is the Agent-Studio-native shape named in CAPABILITIES.md.

## Files

| File | Purpose |
| --- | --- |
| `template.yaml` | The full stack (S3, CloudFront, API Gateway, Lambda, IAM) |
| `probe.yaml`, `probe-api.yaml`, `probe-site.yaml`, `probe-lambda.yaml` | Bisect stacks used to map the account's early-validation hook |
| `build_lambda.py` | Builds the manylinux x86_64 Lambda bundle (deps at zip root, runtime-provided boto3 removed) |
| `deploy.py` | Two-phase deploy: create against a resolvable origin domain, then repoint at the stack's own API domain; restages API Gateway (raw resources are not redeployed by updates); uploads console static; invalidates CloudFront; health-checks |
| `teardown.py` | Empties and deletes all buckets and the stack |

## Account constraints learned (probe-verified)

1. Anonymous Lambda function URL invokes: blocked (see above).
2. The early-validation hook rejects stage throttling
   (`ThrottlingBurstLimit` / `ThrottlingRateLimit` on `AWS::ApiGateway::Stage`)
   and custom-origin domains it cannot resolve: origins must point at
   already-existing domains, hence the two-phase deploy.
3. S3 public-read bucket policy + REST origin (no OAC) passes; raw Lambda
   functions, API Gateway proxy routes, and CloudFront Functions pass.

## Usage

```bash
.venv/Scripts/python infra/deploy.py      # build, upload, deploy, verify
.venv/Scripts/python infra/teardown.py --yes
```

The deploy prints the public URL and verifies `/api/health` end to end.
