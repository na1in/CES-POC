"""
Demo Script 2 — Analyst + Investigator actions on processed payments.

Simulates:
  Priya (analyst):
    • Approves the first HELD payment
    • Rejects the second HELD payment (→ escalated)
    • Overrides a third payment with a custom reason
    • Escalates PMT-900 (the seeded case — seeded HELD, not escalated, so Damien has something to work)

  Damien (investigator):
    • Adds an investigation note to PMT-900
    • Logs a contact record → transitions PMT-900 to pending_sender_response

Run with: python scripts/demo_actions.py
Requires: backend running on :8000 + demo_payments.py already run (needs HELD payments)
"""
from demo_helpers import (
    USR_ANALYST, USR_INVESTIGATOR, get_token, api, section, ok, info
)


def _find_payments_by_status(status_val: str, token: str, limit: int = 5) -> list[dict]:
    result = api("GET", f"/api/payments?status={status_val}&limit={limit}", token)
    return result.get("payments", [])


def run() -> None:
    # ── Priya: approve, reject, override ──────────────────────────────────────
    section("Priya Sharma (analyst) — approve / reject / override")
    analyst_token = get_token(USR_ANALYST)
    ok("Authenticated as Priya Sharma")

    held = _find_payments_by_status("held", analyst_token)
    if len(held) < 2:
        info(f"Only {len(held)} HELD payment(s) found — run demo_payments.py first")
        if not held:
            return
    else:
        info(f"Found {len(held)} HELD payment(s)")

    def pid(p: dict) -> str:
        return p.get("payment_id") or p.get("payment", {}).get("payment_id", "")

    # Approve the first HELD payment
    approve_id = pid(held[0])
    api("POST", f"/api/payments/{approve_id}/approve",
        analyst_token, json={"notes": "Reviewed and verified — applying to policy."})
    ok(f"Approved {approve_id} → APPLIED")

    # Reject the second HELD payment (if available)
    if len(held) >= 2:
        reject_id = pid(held[1])
        api("POST", f"/api/payments/{reject_id}/reject",
            analyst_token, json={"notes": "Risk flags present — escalating for investigation."})
        ok(f"Rejected {reject_id} → ESCALATED")

    # Override a third HELD payment (if available)
    if len(held) >= 3:
        override_id = pid(held[2])
        api("POST", f"/api/payments/{override_id}/override",
            analyst_token,
            json={
                "override_action": "APPLY",
                "reason": "Verified with policy holder directly. Amount variance explained by quarterly adjustment.",
            })
        ok(f"Overrode {override_id} → APPLY (manual override)")
    else:
        info("Not enough HELD payments for override demo — skipping")

    # ── Priya: escalate the seeded PMT-900 case ───────────────────────────────
    # PMT-900 is seeded HELD (AI recommends escalate, per seed.py) — Priya has to actually escalate it
    # before Damien can work it, otherwise the contact_record below has nothing to transition out of
    # (its pending_sender_response side effect only fires from 'escalated', not 'held').
    section("Priya Sharma (analyst) — escalate the seeded PMT-900 case")
    TARGET = "PMT-900"
    api("POST", f"/api/payments/{TARGET}/reject",
        analyst_token, json={"notes": "No customer match — routing to investigations for manual outreach."})
    ok(f"Escalated {TARGET} → ESCALATED")

    # ── Damien: investigation note + contact record ───────────────────────────
    section("Damien Torres (investigator) — investigation note + contact log")
    inv_token = get_token(USR_INVESTIGATOR)
    ok("Authenticated as Damien Torres")

    # Add investigation note to seeded escalated payment
    api("POST", f"/api/payments/{TARGET}/annotations",
        inv_token,
        json={
            "annotation_type": "investigation_note",
            "content": "Contacted sender Unknown Corp LLC via phone. Left voicemail — awaiting callback.",
        },
        expected=201)
    ok(f"Added investigation note to {TARGET}")

    # Log contact record → transitions payment to pending_sender_response
    api("POST", f"/api/payments/{TARGET}/annotations",
        inv_token,
        json={
            "annotation_type": "contact_record",
            "content": "Outreach attempt #1: phone call to listed number. SLA clock started.",
            "contact_method": "phone",
            "contact_outcome": "voicemail",
            "contacted_party": "Unknown Corp LLC",
        },
        expected=201)
    ok(f"Logged contact record on {TARGET} → pending_sender_response (SLA timer started)")

    # Confirm status
    detail = api("GET", f"/api/payments/{TARGET}", inv_token)
    new_status = detail.get("payment", {}).get("status", "unknown")
    info(f"{TARGET} is now: {new_status}")

    print("\nRun demo_governance.py next for director + admin flows.")


if __name__ == "__main__":
    run()
