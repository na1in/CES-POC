"""
Demo Script 3 — Director + Admin governance and configuration flows.

Simulates:
  Lorraine (director):
    • Records a governance period review
    • Flags an override-rate anomaly for Marcus to investigate

  Marcus (admin):
    • Acknowledges the anomaly (status → investigating)
    • Submits a config change request: lower name_match_auto_apply 90 → 87
    • Resolves the anomaly

  Lorraine (director):
    • Approves Marcus's change request

  Marcus (admin):
    • Deploys the approved change → threshold updated live in DB

Run with: python scripts/demo_governance.py
Requires: backend running on :8000
"""
from demo_helpers import (
    USR_DIRECTOR, USR_ADMIN, get_token, api, section, ok, info
)


def run() -> None:
    director_token = get_token(USR_DIRECTOR)
    admin_token    = get_token(USR_ADMIN)

    # ── Lorraine: governance review ───────────────────────────────────────────
    section("Lorraine Chen (director) — governance period review")
    ok("Authenticated as Lorraine Chen")

    review = api("POST", "/api/governance/reviews", director_token,
        json={
            "period_start": "2026-05-01",
            "period_end":   "2026-05-15",
            "notes": "Override rate elevated at 12% vs 8% baseline. Flagging for admin follow-up.",
            "export_generated": True,
        },
        expected=201)
    ok(f"Recorded governance review (id={review.get('review_id', '?')})")

    # ── Lorraine: flag anomaly ────────────────────────────────────────────────
    section("Lorraine Chen (director) — anomaly flag")
    anomaly = api("POST", "/api/governance/anomalies", director_token,
        json={
            "metric_name": "override_rate",
            "description": "Override rate spiked to 12% in the last 14 days against 8% 90-day baseline. "
                           "Concentrated in Scenario 3 (high variance) payments.",
            "scenario_type": "scenario_3",
            "period_start": "2026-05-01",
            "period_end":   "2026-05-15",
            "assigned_to":  "USR-0004",
        },
        expected=201)
    anomaly_id = anomaly.get("flag_id", anomaly.get("id", "?"))
    ok(f"Flagged anomaly: override_rate spike (id={anomaly_id})")

    # ── Marcus: acknowledge anomaly ───────────────────────────────────────────
    section("Marcus Webb (admin) — acknowledge + investigate anomaly")
    ok("Authenticated as Marcus Webb")

    api("PATCH", f"/api/governance/anomalies/{anomaly_id}", admin_token,
        json={"status": "investigating",
              "resolution_notes": "Reviewing Scenario 3 confidence thresholds — may adjust name_match_auto_apply."})
    ok(f"Anomaly {anomaly_id} → investigating")

    # ── Marcus: submit config change request ──────────────────────────────────
    section("Marcus Webb (admin) — config change request")
    change = api("POST", "/api/settings/change-requests", admin_token,
        json={
            "parameter_name":    "name_match_auto_apply",
            "proposed_value":    "87",
            "rationale":         "Lower auto-apply threshold to reduce override rate on Scenario 3. "
                                 "Back-test shows 87% still filters >98% of mismatches.",
            "projected_impact":  "Expected 4% reduction in override rate; ~3% more auto-applies per day.",
        },
        expected=201)
    change_id = change.get("change_id", change.get("id", "?"))
    ok(f"Change request submitted (id={change_id}): name_match_auto_apply 90 → 87")

    # ── Lorraine: approve the change request ──────────────────────────────────
    section("Lorraine Chen (director) — approve change request")
    api("POST", f"/api/settings/change-requests/{change_id}/approve", director_token)
    ok(f"Change request {change_id} approved by Lorraine")

    # ── Marcus: deploy ────────────────────────────────────────────────────────
    section("Marcus Webb (admin) — deploy approved change")
    api("POST", f"/api/settings/change-requests/{change_id}/deploy", admin_token)
    ok(f"Change request {change_id} deployed — threshold is now live")

    # Confirm live threshold value
    thresholds = api("GET", "/api/settings/thresholds", admin_token)
    for t in thresholds if isinstance(thresholds, list) else thresholds.get("thresholds", []):
        if t.get("parameter_name") == "name_match_auto_apply":
            info(f"Confirmed: name_match_auto_apply = {t.get('parameter_value')} (was 90)")
            break

    # ── Marcus: resolve anomaly ───────────────────────────────────────────────
    section("Marcus Webb (admin) — resolve anomaly")
    api("PATCH", f"/api/governance/anomalies/{anomaly_id}", admin_token,
        json={"status": "resolved",
              "resolution_notes": "Deployed threshold change (name_match_auto_apply: 90→87). "
                                  "Monitoring for 7 days."})
    ok(f"Anomaly {anomaly_id} → resolved")

    print("\nFull governance + config loop complete.")
    print("Run demo_restore.py when done to reset all changes.")


if __name__ == "__main__":
    run()
