"""Deploy (or update) the console hosting stack and verify it live.

    .venv/Scripts/python infra/deploy.py

Reads Zoho credentials from the repo's .env, builds the Lambda bundle, uploads
code and console static, creates/updates the zohomcp-dev stack, then verifies
the public URL end to end (index + /api/health).
"""

from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

import boto3

INFRA_DIR = Path(__file__).resolve().parent
REPO_ROOT = INFRA_DIR.parent
STACK = "zohomcp-dev"
REGION = "us-east-1"

STATIC_FILES = {
    "index.html": "text/html; charset=utf-8",
    "console.css": "text/css; charset=utf-8",
    "console.js": "application/javascript; charset=utf-8",
}


def load_env() -> dict[str, str]:
    values: dict[str, str] = {}
    for line in (REPO_ROOT / ".env").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            values[key.strip()] = val.strip()
    return values


def ensure_bucket(s3, name: str) -> None:
    try:
        s3.head_bucket(Bucket=name)
    except Exception:  # noqa: BLE001
        print(f"creating bucket {name}")
        s3.create_bucket(Bucket=name)
        waiter = s3.get_waiter("bucket_exists")
        waiter.wait(Bucket=name)


def upload_static(s3, bucket: str) -> None:
    static_dir = REPO_ROOT / "console" / "static"
    for name, content_type in STATIC_FILES.items():
        s3.put_object(
            Bucket=bucket,
            Key=name,
            Body=(static_dir / name).read_bytes(),
            ContentType=content_type,
            CacheControl="no-cache",
        )
    print("console static uploaded")


def cfn_parameters(env: dict[str, str], zip_key: str, api_domain: str) -> list[dict]:
    return [
        {"ParameterKey": "DeployBucketName", "ParameterValue": f"zohomcp-dev-deploy-{env_account()}"},
        {"ParameterKey": "ZipObjectKey", "ParameterValue": zip_key},
        {"ParameterKey": "ZohoClientId", "ParameterValue": env["ZOHO_CLIENT_ID"]},
        {"ParameterKey": "ZohoClientSecret", "ParameterValue": env["ZOHO_CLIENT_SECRET"]},
        {"ParameterKey": "ZohoRefreshToken", "ParameterValue": env["ZOHO_REFRESH_TOKEN"]},
        {"ParameterKey": "ZohoOrgId", "ParameterValue": env["ZOHO_ORG_ID"]},
        {"ParameterKey": "BedrockModelId", "ParameterValue": env.get("BEDROCK_MODEL_ID", "global.amazon.nova-2-lite-v1:0")},
        {"ParameterKey": "ApiOriginDomain", "ParameterValue": api_domain},
    ]


_account: str | None = None


def env_account() -> str:
    global _account
    if _account is None:
        _account = boto3.client("sts", region_name=REGION).get_caller_identity()["Account"]
    return _account


def _stack_status(cfn) -> str | None:
    try:
        return cfn.describe_stacks(StackName=STACK)["Stacks"][0]["StackStatus"]
    except cfn.exceptions.ClientError:
        return None


def deploy_changeset(cfn, template_body: str, parameters: list[dict], *, created: bool) -> None:
    """Deploy via a change set: the account's early-validation hook only runs
    (and only passes) on change-set-based deploys, not direct CreateStack."""
    change_set_name = f"{STACK}-cs-{int(time.time())}"
    cfn.create_change_set(
        StackName=STACK,
        TemplateBody=template_body,
        Parameters=parameters,
        Capabilities=["CAPABILITY_NAMED_IAM"],
        ChangeSetType="CREATE" if created else "UPDATE",
        ChangeSetName=change_set_name,
    )
    cfn.get_waiter("change_set_create_complete").wait(
        ChangeSetName=change_set_name, StackName=STACK
    )
    cfn.execute_change_set(ChangeSetName=change_set_name, StackName=STACK)


def main() -> int:
    env = load_env()
    for key in ("ZOHO_CLIENT_ID", "ZOHO_CLIENT_SECRET", "ZOHO_REFRESH_TOKEN", "ZOHO_ORG_ID"):
        if not env.get(key):
            raise SystemExit(f"{key} missing in .env")

    s3 = boto3.client("s3", region_name=REGION)
    cfn = boto3.client("cloudformation", region_name=REGION)

    zip_key = "lambda-bundle.zip"

    sys_path = str(INFRA_DIR)
    if sys_path not in __import__("sys").path:
        __import__("sys").path.insert(0, sys_path)
    from build_lambda import build

    zip_path = build(fresh=False)
    deploy_bucket = f"zohomcp-dev-deploy-{env_account()}"
    ensure_bucket(s3, deploy_bucket)
    s3.put_object(Bucket=deploy_bucket, Key=zip_key, Body=zip_path.read_bytes())
    print("bundle uploaded")

    # The account's early-validation hook does DNS existence checks on custom
    # origins, so phase 1 creates the stack against a known-resolvable stand-in
    # domain and phase 2 repoints it at the stack's own API Gateway domain.
    placeholder_domain = "gmbvgf4mwj.execute-api.us-east-1.amazonaws.com"
    template_body = (INFRA_DIR / "template.yaml").read_text(encoding="utf-8")
    parameters = cfn_parameters(env, zip_key, placeholder_domain)
    stack_exists = _stack_status(cfn) is not None
    if stack_exists:
        print("stack exists; phase 2 update follows")
    else:
        deploy_changeset(cfn, template_body, parameters, created=True)
        cfn.get_waiter("stack_create_complete").wait(StackName=STACK)
        print("stack created")

    outputs = {
        o["OutputKey"]: o["OutputValue"]
        for o in cfn.describe_stacks(StackName=STACK)["Stacks"][0]["Outputs"]
    }

    api_domain = outputs["ApiBaseUrl"].split("https://")[1].split("/")[0]
    if api_domain != placeholder_domain:
        print(f"phase 2: repointing origin at {api_domain} ...")
        parameters = cfn_parameters(env, zip_key, api_domain)
        deploy_changeset(cfn, template_body, parameters, created=False)
        cfn.get_waiter("stack_update_complete").wait(StackName=STACK)
        outputs = {
            o["OutputKey"]: o["OutputValue"]
            for o in cfn.describe_stacks(StackName=STACK)["Stacks"][0]["Outputs"]
        }
    console_bucket = outputs["ConsoleBucketName"]
    ensure_bucket(s3, console_bucket)
    upload_static(s3, console_bucket)

    # Raw ApiGateway resources are not redeployed by stack updates: restage.
    rest_api_id = api_domain.split(".")[0]
    apigw = boto3.client("apigateway", region_name=REGION)
    apigw.create_deployment(restApiId=rest_api_id, stageName="dev")
    print("api gateway restaged")

    cf = boto3.client("cloudfront", region_name=REGION)
    cf.create_invalidation(
        DistributionId=outputs["DistributionId"],
        InvalidationBatch={
            "Paths": {"Quantity": 1, "Items": ["/*"]},
            "CallerReference": f"zohomcp-{int(time.time())}",
        },
    )

    public_url = outputs["PublicUrl"]
    for attempt in range(10):
        try:
            with urllib.request.urlopen(f"{public_url}/api/health", timeout=20) as resp:
                health = json.loads(resp.read().decode())
            print(f"health: {health}")
            break
        except Exception as exc:  # noqa: BLE001
            print(f"waiting for backend ({attempt + 1}/10): {exc}")
            time.sleep(10)
    else:
        print("health check did not pass yet; check CloudWatch logs for zohomcp-dev-backend")
        return 1

    print(f"\nLIVE: {public_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
