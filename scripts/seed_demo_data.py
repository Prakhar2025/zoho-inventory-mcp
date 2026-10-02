"""Seed the LoomKart demo organization with fictional data (phase P1, one time).

Creates customers, items, and sales orders on the Zoho Inventory free plan.
Everything is fictional and deterministic. Spacing between calls is enforced
because the free plan allows only 5 concurrent requests and we stay polite.

Why a separate token: the connector's own refresh token is read-only by scope.
Seeding needs write scopes, so this script uses a SEPARATE refresh token that
is stored as ZOHO_SEED_REFRESH_TOKEN and can be revoked after seeding. The
connector never holds write access. That split is part of the security story.

Prerequisites:
  - .env has ZOHO_CLIENT_ID, ZOHO_CLIENT_SECRET, ZOHO_ORG_ID, and the read
    ZOHO_REFRESH_TOKEN (already done via scripts/get_refresh_token.py).
  - A NEW grant code generated with WRITE scopes: run this script without
    arguments to print the exact scope string, generate a 10 minute code at
    https://api-console.zoho.in (Self Client > Generate Code), then run:

        py -3.12 scripts/seed_demo_data.py <grant_code>
"""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = REPO_ROOT / ".env"

ACCOUNTS_BASE = "https://accounts.zoho.in"
API_BASE = "https://www.zohoapis.in/inventory/v1"

# Write scopes ONLY for seeding. The read-only connector token stays untouched.
# Listing before creating needs READ as well as CREATE, otherwise Zoho rejects
# the list calls with HTTP 401 code 57 (learned live in P1).
SCOPES_WRITE = (
    "ZohoInventory.contacts.READ,"
    "ZohoInventory.contacts.CREATE,"
    "ZohoInventory.items.READ,"
    "ZohoInventory.items.CREATE,"
    "ZohoInventory.salesorders.READ,"
    "ZohoInventory.salesorders.CREATE"
)

CALL_SPACING_SECONDS = 1.0
_last_call = 0.0


# ---------------------------------------------------------------- fictional data

CUSTOMERS = [
    {"contact_name": "Aarav Sharma", "contact_type": "customer"},
    {"contact_name": "Priya Nair", "contact_type": "customer"},
    {"contact_name": "Rohan Mehta", "contact_type": "customer"},
    {"contact_name": "Sneha Iyer", "contact_type": "customer"},
    {"contact_name": "Vikram Singh", "contact_type": "customer"},
    {"contact_name": "Ananya Rao", "contact_type": "customer"},
]

ITEMS = [
    {"name": "Jaipur Block Print Bedsheet (Queen)", "sku": "LK-BED-001", "rate": 1899.0, "stock": 40},
    {"name": "Handloom Cotton Curtains (Set of 2)", "sku": "LK-CUR-002", "rate": 1249.0, "stock": 55},
    {"name": "Kalamkari Table Runner", "sku": "LK-TAB-003", "rate": 649.0, "stock": 80},
    {"name": "Warli Art Cushion Covers (Set of 5)", "sku": "LK-CUS-004", "rate": 999.0, "stock": 60},
    {"name": "Dhurrie Jute Rug (5x8 ft)", "sku": "LK-RUG-005", "rate": 2799.0, "stock": 25},
    {"name": "Block Print Napkin Set (6 pcs)", "sku": "LK-NAP-006", "rate": 449.0, "stock": 90},
    {"name": "Chikankari Cushion Cover (Single)", "sku": "LK-CUS-007", "rate": 599.0, "stock": 70},
    {"name": "Ajrah Print Doormat", "sku": "LK-DOOR-008", "rate": 799.0, "stock": 45},
]

# (days_ago, customer name, [(sku, qty)], note)
ORDER_PLAN = [
    (28, "Aarav Sharma", [("LK-BED-001", 1)], "Festival order, delivered feedback pending"),
    (25, "Priya Nair", [("LK-CUR-002", 2), ("LK-TAB-003", 1)], "Repeat customer"),
    (22, "Rohan Mehta", [("LK-RUG-005", 1)], "Bulk corporate enquiry earlier"),
    (20, "Sneha Iyer", [("LK-CUS-004", 2)], "Gift order, invoice to company"),
    (18, "Vikram Singh", [("LK-NAP-006", 3)], "Kitchen bundle"),
    (15, "Ananya Rao", [("LK-BED-001", 2), ("LK-NAP-006", 1)], "Wedding gift"),
    (12, "Aarav Sharma", [("LK-DOOR-008", 1), ("LK-TAB-003", 2)], "Second purchase this month"),
    (10, "Priya Nair", [("LK-CUS-007", 4)], "Interior designer, studio order"),
    (7, "Rohan Mehta", [("LK-CUR-002", 1)], "Office refurbishment"),
    (5, "Sneha Iyer", [("LK-RUG-005", 1), ("LK-CUS-004", 1)], "Living room makeover"),
    (3, "Vikram Singh", [("LK-BED-001", 1)], "Diwali pre-order"),
    (1, "Ananya Rao", [("LK-TAB-003", 1), ("LK-DOOR-008", 1)], "Housewarming"),
]


# ---------------------------------------------------------------- helpers

def polite_sleep() -> None:
    global _last_call
    elapsed = time.time() - _last_call
    if elapsed < CALL_SPACING_SECONDS:
        time.sleep(CALL_SPACING_SECONDS - elapsed)
    _last_call = time.time()


def zoho_request(method: str, path: str, token: str, org_id: str, body: dict | None = None) -> dict:
    polite_sleep()
    url = f"{API_BASE}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Zoho-oauthtoken {token}",
            "Organization-Id": org_id,
            "Content-Type": "application/json",
        },
    )
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            payload = e.read().decode(errors="replace")
            if e.code == 429:
                wait = int(e.headers.get("Retry-After", "5") or "5")
                print(f"    429 rate limited, waiting {wait}s (attempt {attempt + 1}/4)")
                time.sleep(wait)
                continue
            raise RuntimeError(f"{method} {path} failed: HTTP {e.code}: {payload[:300]}") from e
    raise RuntimeError(f"{method} {path} still rate limited after retries")


def load_env() -> dict[str, str]:
    if not ENV_PATH.exists():
        sys.exit("No .env file found.")
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


def refresh_access_token(env: dict[str, str], refresh_key: str) -> str:
    data = urllib.parse.urlencode(
        {
            "grant_type": "refresh_token",
            "client_id": env["ZOHO_CLIENT_ID"],
            "client_secret": env["ZOHO_CLIENT_SECRET"],
            "refresh_token": env[refresh_key],
        }
    ).encode()
    req = urllib.request.Request(f"{ACCOUNTS_BASE}/oauth/v2/token", data=data)
    with urllib.request.urlopen(req, timeout=30) as resp:
        out = json.loads(resp.read().decode())
    if "access_token" not in out:
        sys.exit(f"Token refresh failed: {json.dumps(out)}")
    return out["access_token"]


# ---------------------------------------------------------------- seeding steps

def seed_contacts(token: str, org_id: str) -> dict[str, str]:
    existing = zoho_request("GET", "/contacts?per_page=200", token, org_id).get("contacts", [])
    by_name = {c["contact_name"]: c["contact_id"] for c in existing}
    for c in CUSTOMERS:
        if c["contact_name"] in by_name:
            print(f"  contact exists: {c['contact_name']}")
            continue
        created = zoho_request("POST", "/contacts", token, org_id, c).get("contact", {})
        by_name[c["contact_name"]] = created["contact_id"]
        print(f"  contact created: {c['contact_name']}")
    return by_name


def seed_items(token: str, org_id: str) -> dict[str, str]:
    existing = zoho_request("GET", "/items?per_page=200", token, org_id).get("items", [])
    by_sku = {i.get("sku"): i["item_id"] for i in existing if i.get("sku")}
    for it in ITEMS:
        if it["sku"] in by_sku:
            print(f"  item exists: {it['sku']}")
            continue
        payload = {
            "name": it["name"],
            "sku": it["sku"],
            "rate": it["rate"],
            "product_type": "goods",
            "initial_stock": it["stock"],
            "initial_stock_rate": it["rate"],
        }
        created = zoho_request("POST", "/items", token, org_id, payload).get("item", {})
        by_sku[it["sku"]] = created["item_id"]
        print(f"  item created: {it['sku']}")
    return by_sku


def seed_orders(token: str, org_id: str, contacts: dict[str, str], items: dict[str, str]) -> None:
    # Anchor order dates to the org's timezone (IST), not the machine's clock.
    today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    created_count, skipped = 0, 0
    for days_ago, customer_name, lines, note in ORDER_PLAN:
        order_date = (today - timedelta(days=days_ago)).isoformat()
        reference = f"LK-SO-{days_ago:03d}-{order_date.replace('-', '')}"
        found = zoho_request(
            "GET", f"/salesorders?reference_number={urllib.parse.quote(reference)}", token, org_id
        ).get("salesorders", [])
        if found:
            print(f"  order exists: {reference}")
            skipped += 1
            continue
        payload = {
            "customer_id": contacts[customer_name],
            "reference_number": reference,
            "date": order_date,
            "line_items": [
                {"item_id": items[sku], "name": next(i["name"] for i in ITEMS if i["sku"] == sku),
                 "rate": next(i["rate"] for i in ITEMS if i["sku"] == sku), "quantity": qty}
                for sku, qty in lines
            ],
            "notes": note,
        }
        created = zoho_request("POST", "/salesorders", token, org_id, payload).get("salesorder", {})
        print(f"  order created: {reference} ({created.get('status', '?')})")
        created_count += 1
    print(f"  orders: {created_count} created, {skipped} already existed")


def main() -> None:
    env = load_env()
    if len(sys.argv) < 2:
        if env.get("ZOHO_SEED_REFRESH_TOKEN"):
            print("Found ZOHO_SEED_REFRESH_TOKEN in .env, skipping exchange and seeding directly.")
        else:
            print(__doc__)
            print(f"Scope string for the Generate Code dialog:\n\n{SCOPES_WRITE}\n")
            print("Then run:  py -3.12 scripts/seed_demo_data.py <grant_code>")
            return
    else:
        grant_code = sys.argv[1].strip()
        for key in ("ZOHO_CLIENT_ID", "ZOHO_CLIENT_SECRET", "ZOHO_ORG_ID"):
            if not env.get(key):
                sys.exit(f"{key} missing in .env (finish scripts/get_refresh_token.py first)")

        print("Exchanging write-scope grant code for a seeding token...")
        data = urllib.parse.urlencode(
            {
                "grant_type": "authorization_code",
                "code": grant_code,
                "client_id": env["ZOHO_CLIENT_ID"],
                "client_secret": env["ZOHO_CLIENT_SECRET"],
            }
        ).encode()
        req = urllib.request.Request(f"{ACCOUNTS_BASE}/oauth/v2/token", data=data)
        with urllib.request.urlopen(req, timeout=30) as resp:
            out = json.loads(resp.read().decode())
        if "refresh_token" not in out:
            sys.exit(f"Exchange failed: {json.dumps(out)}")
        save_env_values({"ZOHO_SEED_REFRESH_TOKEN": out["refresh_token"]})
        print("Seeding token saved as ZOHO_SEED_REFRESH_TOKEN (separate from the read-only token).")

    for key in ("ZOHO_CLIENT_ID", "ZOHO_CLIENT_SECRET", "ZOHO_ORG_ID"):
        if not env.get(key):
            sys.exit(f"{key} missing in .env")

    token = refresh_access_token(env, "ZOHO_SEED_REFRESH_TOKEN")
    org_id = env["ZOHO_ORG_ID"]

    print("Seeding customers...")
    contacts = seed_contacts(token, org_id)
    print("Seeding items...")
    items = seed_items(token, org_id)
    print("Seeding sales orders...")
    seed_orders(token, org_id, contacts, items)

    print("\nDone. The org now has fictional LoomKart demo data.")
    print("Optional hygiene: revoke ZOHO_SEED_REFRESH_TOKEN later in the API console.")


if __name__ == "__main__":
    main()
