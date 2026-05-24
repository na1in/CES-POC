"""
Demo Script 1 — Ingest payments across all 5 scenarios.

Injects 6 payments designed to exercise each routing path:
  SC1-auto  : Robert Johnson  + POL-00001 ref   + exact amount → auto-apply
  SC1-hold  : James Wilson    + POL-00004 ref   + exact amount → hold (risk flag)
  SC2       : Maria Rodriguez + no policy ref   + $1,200       → customer match, no policy
  SC3       : Robert Johnson  + POL-00001 ref   + $1,800 (+20%)→ high variance hold
  SC4       : Unknown Corp LLC + no match        + $750 Wire   → escalate
  SC5       : Duplicate of SC2 (same sender/method/amount within 72hrs)

Run with: python scripts/demo_payments.py
Requires: backend running on :8000 + DB seeded (scripts/seed.py)
"""
import time
from datetime import datetime, timezone

from demo_helpers import (
    BASE_URL, USR_ANALYST, get_token, api, section, ok, info
)

NOW = datetime.now(timezone.utc).isoformat()

PAYMENTS = [
    {
        "_label": "SC1 auto-apply — Robert Johnson exact match",
        "sender_name": "Robert Johnson",
        "sender_account": "ACC-10001",
        "amount": 150000,
        "payment_method": "ACH",
        "payment_date": NOW,
        "reference_field_1": "Policy POL-00001 May premium",
    },
    {
        "_label": "SC1 hold — James Wilson (risk flag on CUST-0003)",
        "sender_name": "James Wilson",
        "sender_account": "ACC-10003",
        "amount": 200000,
        "payment_method": "Check",
        "payment_date": NOW,
        "reference_field_1": "POL-00004 May payment",
    },
    {
        "_label": "SC2 — Maria Rodriguez, no policy ref",
        "sender_name": "Maria Rodriguez",
        "sender_account": "ACC-10002",
        "amount": 120000,
        "payment_method": "Credit Card",
        "payment_date": NOW,
        "reference_field_1": "Monthly insurance premium",
    },
    {
        "_label": "SC3 — Robert Johnson, 20% overpayment",
        "sender_name": "Robert Johnson",
        "sender_account": "ACC-10001",
        "amount": 180000,
        "payment_method": "ACH",
        "payment_date": NOW,
        "reference_field_1": "POL-00001 — paid extra this month",
    },
    {
        "_label": "SC4 — Unknown Corp LLC, no customer match",
        "sender_name": "Unknown Corp LLC",
        "sender_account": None,
        "amount": 75000,
        "payment_method": "Wire",
        "payment_date": NOW,
        "reference_field_1": None,
    },
]

SC5_DUPLICATE_TEMPLATE = {
    "_label": "SC5 — duplicate of SC2 (same sender/method/amount within 72hrs)",
}


def run() -> None:
    section("Demo: Ingest payments across all 5 scenarios")
    token = get_token(USR_ANALYST)
    ok("Authenticated as Priya Sharma (analyst)")

    ingested_ids: list[str] = []

    for pmt in PAYMENTS:
        label = pmt.pop("_label")
        body = {k: v for k, v in pmt.items() if v is not None}
        result = api("POST", "/api/payments/ingest", token, json=body, expected=201)
        payment_id = result["payment_id"]
        ingested_ids.append(payment_id)
        ok(f"{payment_id}  ←  {label}")

    # SC5: duplicate of SC2 — ingest same payment again
    sc2_body = {
        "sender_name": "Maria Rodriguez",
        "sender_account": "ACC-10002",
        "amount": 120000,
        "payment_method": "Credit Card",
        "payment_date": NOW,
        "reference_field_1": "Monthly insurance premium",
    }
    result = api("POST", "/api/payments/ingest", token, json=sc2_body, expected=201)
    dup_id = result["payment_id"]
    ingested_ids.append(dup_id)
    ok(f"{dup_id}  ←  SC5 duplicate of SC2 (Maria Rodriguez, same amount/method/date)")

    section("Waiting for pipeline to process all payments...")
    # Poll until all payments leave RECEIVED/PROCESSING or timeout at 60s
    deadline = time.time() + 60
    while time.time() < deadline:
        time.sleep(3)
        statuses = [
            api("GET", f"/api/payments/{pid}", token).get("payment", {}).get("status", "processing")
            for pid in ingested_ids
        ]
        if all(s not in ("received", "processing") for s in statuses):
            info(f"All {len(ingested_ids)} payments processed")
            break
    else:
        info("Timeout waiting for pipeline — some payments may still be processing")

    # Show final statuses
    section("Final payment statuses")
    for pid in ingested_ids:
        detail = api("GET", f"/api/payments/{pid}", token)
        status_val = detail.get("payment", {}).get("status", "unknown")
        recommendation = detail.get("recommendation") or {}
        scenario = recommendation.get("scenario_route", "—")
        rec = recommendation.get("recommendation", "—")
        confidence = recommendation.get("confidence_score", "—")
        info(f"{pid}  status={status_val}  scenario={scenario}  rec={rec}  confidence={confidence}")

    print(f"\nPayment IDs ingested: {', '.join(ingested_ids)}")
    print("Run demo_actions.py next to simulate analyst + investigator actions.")


if __name__ == "__main__":
    run()
