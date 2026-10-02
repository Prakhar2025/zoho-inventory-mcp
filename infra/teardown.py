"""Delete the hosting stack and every bucket it created. Confirmation required.

    .venv/Scripts/python infra/teardown.py --yes
"""

from __future__ import annotations

import argparse

import boto3

REGION = "us-east-1"
STACK = "zohomcp-dev"
ACCOUNT = boto3.client("sts", region_name=REGION).get_caller_identity()["Account"]
OWNED_BUCKETS = [f"zohomcp-dev-console-{ACCOUNT}", f"zohomcp-dev-deploy-{ACCOUNT}"]


def empty_bucket(s3, bucket: str) -> None:
    paginator = s3.get_paginator("list_object_versions")
    for page in paginator.paginate(Bucket=bucket):
        objects = [
            {"Key": o["Key"], "VersionId": o["VersionId"]}
            for section in ("Versions", "DeleteMarkers")
            for o in page.get(section, [])
        ]
        for chunk_start in range(0, len(objects), 1000):
            s3.delete_objects(Bucket=bucket, Delete={"Objects": objects[chunk_start : chunk_start + 1000]})


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--yes", action="store_true", help="skip confirmation")
    args = parser.parse_args()
    if not args.yes:
        raise SystemExit("This deletes the stack and all buckets. Re-run with --yes to confirm.")

    cfn = boto3.client("cloudformation", region_name=REGION)
    s3 = boto3.client("s3", region_name=REGION)

    try:
        cfn.delete_stack(StackName=STACK)
        print(f"deleting stack {STACK} ...")
        cfn.get_waiter("stack_delete_complete").wait(StackName=STACK)
    except cfn.exceptions.ClientError as exc:
        if "does not exist" in str(exc):
            print("stack already gone")
        else:
            raise

    for bucket in OWNED_BUCKETS:
        try:
            s3.head_bucket(Bucket=bucket)
            empty_bucket(s3, bucket)
            s3.delete_bucket(Bucket=bucket)
            print(f"deleted bucket {bucket}")
        except Exception:  # noqa: BLE001
            print(f"bucket {bucket} already gone")

    print("teardown complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
