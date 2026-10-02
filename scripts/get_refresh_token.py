"""One-time OAuth 2.0 setup for the Zoho Inventory connector.

Standard library only, so it runs with: py -3.12 scripts/get_refresh_token.py

What it does:
  1. With no arguments: prints the setup checklist, including the exact scope
     string to paste into the Zoho API Console "Generate Code" dialog.
  2. With a grant code argument: exchanges the code for tokens, saves the
     refresh token and organization id into .env, and verifies the token by
     listing Zoho organizations.

Prerequisites (about 3 minutes):
  a. Create a Self Client at https://api-console.zoho.in (the IN data center
     console, matching our org) and note the Client ID and Client Secret.
  b. Put them in the .env file at the repo root as ZOHO_CLIENT_ID and
     ZOHO_CLIENT_SECRET.
  c. In the Self Client page, open the "Generate Code" tab, paste the scope
     string this script prints, set expiry to 10 minutes, generate, and copy
     the grant code. Grant codes are single use and expire in minutes, so run
     step 2 immediately.

Usage:
    py -3.12 scripts/get_refresh_token.py            # prints instructions
    py -3.12 scripts/get_refresh_token.py <grant_code>
"""

from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = REPO_ROOT / ".env"

# India data center: our org was created on the IN DC (see docs/03-HANDOVER.md).
ACCOUNTS_BASE = "https://accounts.zoho.in"
API_BASE = "https://www.zohoapis.in/inventory/v1"

# Read-only scopes: everything the connector needs and nothing more.
SCOPES = (
    "ZohoInventory.settings.READ,"
    "ZohoInventory.items.READ,"
    "ZohoInventory.salesorders.READ,"
    "ZohoInventory.contacts.READ"
)


def load_env() -> dict[str, str]:
    if not ENV_PATH.exists():
        sys.exit("No .env file found. Copy .env.example to .env first.")
    values: dict[str, str] = {}
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            values[key.strip()] = val.strip()
    return values


def save_env_values(new: dict[str, str]) -> None:
    lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
    for key, val in new.items():
        for i, line in enumerate(lines):
            if line.strip().startswith(f"{key}="):
                lines[i] = f"{key}={val}"
                break
        else:
            lines.append(f"{key}={val}")
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def http_post(url: str, data: dict[str, str]) -> dict:
    req = urllib.request.Request(
        url,
        data=urllib.parse.urlencode(data).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def http_get_json(url: str, token: str) -> dict:
    req = urllib.request.Request(url, headers={"Authorization": f"Zoho-oauthtoken {token}"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode())


def exchange(grant_code: str) -> None:
    env = load_env()
    client_id, client_secret = env.get("ZOHO_CLIENT_ID", ""), env.get("ZOHO_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        sys.exit("ZOHO_CLIENT_ID or ZOHO_CLIENT_SECRET missing in .env")

    print("Exchanging grant code for tokens...")
    token_resp = http_post(
        f"{ACCOUNTS_BASE}/oauth/v2/token",
        {
            "grant_type": "authorization_code",
            "code": grant_code,
            "client_id": client_id,
            "client_secret": client_secret,
        },
    )
    if "refresh_token" not in token_resp:
        sys.exit(
            f"Token exchange failed: {json.dumps(token_resp)}\n"
            "Common causes: grant code already used or expired, or client id and secret\n"
            "belong to a different data center console (must be api-console.zoho.in)."
        )

    refresh_token = token_resp["refresh_token"]
    access_token = token_resp["access_token"]
    save_env_values({"ZOHO_REFRESH_TOKEN": refresh_token})
    print("Refresh token saved to .env (long lived). Access token used for verification only.")

    print("Verifying by listing organizations...")
    orgs = http_get_json(f"{API_BASE}/organizations", access_token).get("organizations", [])
    if not orgs:
        sys.exit("Token works but no organizations were returned. Check the org on inventory.zoho.in")

    org = next(
        (o for o in orgs if str(o.get("name", "")).lower() == "loomkart"),
        orgs[0],
    )
    # The organizations endpoint returns "organization_id" (not "id").
    org_id = org.get("organization_id") or org.get("id")
    if not org_id:
        sys.exit(f"Unexpected organization payload: {json.dumps(org)}")
    save_env_values({"ZOHO_ORG_ID": str(org_id)})
    print(f"Organization: {org['name']} (org id saved to .env)")
    print("\nDone. .env is fully configured. Next: scripts/seed_demo_data.py (phase 1).")


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        print(f"\nScope string to paste into the Generate Code dialog:\n\n{SCOPES}\n")
        print("Then run:  py -3.12 scripts/get_refresh_token.py <grant_code>")
        return
    exchange(sys.argv[1].strip())


if __name__ == "__main__":
    main()
