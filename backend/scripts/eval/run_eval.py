"""
Runs generated evaluation cases through the real ingest endpoint and pipeline (in-process, against an
isolated database) and scores the outcomes against the archetype labels.

Each case runs in isolation: payments and derived rows are cleared before it, so cases cannot trigger
each other's duplicate detection. Only a case's own prior payment (if any) is ingested first.
Cases whose name score used the LLM ("gray zone") are then re-run --repeat-gray more times to measure
how stable the outcome is.

Safety: refuses to run unless the target database name ends in "_eval".

Usage (from backend/):  python scripts/eval/run_eval.py [--data scripts/eval/data/full.json] [--repeat-gray 4]
"""
import argparse
import asyncio
import json
import os
import re
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))


def _eval_db_url() -> str:
    if os.environ.get("EVAL_DATABASE_URL"):
        return os.environ["EVAL_DATABASE_URL"]
    env = (BACKEND / ".env").read_text() if (BACKEND / ".env").exists() else ""
    match = re.search(r"^DATABASE_URL=(.+)$", env, re.M)
    base = match.group(1).strip() if match else "postgresql+asyncpg://ces_user:ces_password@localhost:5432/ces"
    return base.rsplit("/", 1)[0] + "/ces_eval"


EVAL_URL = _eval_db_url()
if not EVAL_URL.rsplit("/", 1)[-1].endswith("_eval"):
    sys.exit(f"refusing to run: {EVAL_URL} is not an *_eval database")
os.environ["DATABASE_URL"] = EVAL_URL  # must be set before app modules import settings

import httpx  # noqa: E402
from sqlalchemy import text  # noqa: E402

from app.database import AsyncSessionLocal  # noqa: E402
from app.main import app  # noqa: E402

PAYMENT_TABLES = ("audit_log", "case_annotations", "case_documents", "payment_signals", "payment_recommendations", "payments")
WORLD_TABLES = ("payment_history", "policies", "risk_flags", "customers")
POLICY_RE = re.compile(r"POL-\d{5}")


def cents(usd: float) -> int:
    return round(usd * 100)


async def clear(db, tables) -> None:
    for table in tables:
        await db.execute(text(f"DELETE FROM {table}"))
    await db.commit()


async def load_world(db, world: dict, now: datetime) -> None:
    await clear(db, PAYMENT_TABLES + WORLD_TABLES)
    for c in world["customers"]:
        await db.execute(text("""
            INSERT INTO customers (customer_id, name, account_number, status)
            VALUES (:id, :name, :acct, CAST(:status AS customer_status))
        """), {"id": c["customer_id"], "name": c["name"], "acct": c["account_number"], "status": c["status"]})
        for flag in c["risk_flags"]:
            await db.execute(text("""
                INSERT INTO risk_flags (customer_id, flag_type, notes)
                VALUES (:id, CAST(:flag AS risk_flag_type), 'synthetic eval data')
            """), {"id": c["customer_id"], "flag": flag})
        for p in c["policies"]:
            await db.execute(text("""
                INSERT INTO policies (policy_number, customer_id, policy_type, premium_amount, premium_frequency,
                                      status, outstanding_balance, next_due_date)
                VALUES (:pn, :cid, :type, :premium, CAST(:freq AS premium_frequency),
                        CAST(:status AS policy_status), :balance, :due)
            """), {"pn": p["policy_number"], "cid": c["customer_id"], "type": p["policy_type"], "premium": cents(p["premium_usd"]),
                   "freq": p["premium_frequency"], "status": p["status"], "balance": cents(p["outstanding_balance_usd"]),
                   "due": (now + timedelta(days=p["next_due_in_days"])).date()})
            for h in p["history"]:
                await db.execute(text("""
                    INSERT INTO payment_history (policy_id, payment_date, amount, payment_method, sender_account, status)
                    VALUES (:pn, :date, :amount, :method, :acct, CAST(:status AS payment_history_status))
                """), {"pn": p["policy_number"], "date": now - timedelta(days=h["days_ago"]), "amount": cents(h["amount_usd"]),
                       "method": h["payment_method"], "acct": h["sender_account"] or None, "status": h["status"]})
    await db.commit()


def ingest_body(p: dict, now: datetime) -> dict:
    optional = {k: p[k] for k in ("sender_account", "beneficiary_name", "reference_field_1", "reference_field_2") if p[k].strip()}
    return {"amount": cents(p["amount_usd"]), "sender_name": p["sender_name"], "payment_method": p["payment_method"],
            "payment_date": (now - timedelta(hours=p["hours_ago"])).isoformat(), **optional}


async def run_case(client: httpx.AsyncClient, db, case: dict, now: datetime) -> dict:
    await clear(db, PAYMENT_TABLES)
    ingests = [*case["prior_payments"], case["payment"]]  # the prior payment first
    started = time.monotonic()
    for p in ingests:
        response = await client.post("/api/payments/ingest", json=ingest_body(p, now))
        response.raise_for_status()
        payment_id = response.json()["payment_id"]
    wall = time.monotonic() - started

    deadline = time.monotonic() + 90
    while True:  # the pipeline normally finishes inside the ASGI call; poll defensively
        status = (await db.execute(text("SELECT status::text FROM payments WHERE payment_id = :i"), {"i": payment_id})).scalar_one()
        await db.rollback()
        if status not in ("received", "processing") or time.monotonic() > deadline:
            break
        await asyncio.sleep(0.5)

    row = (await db.execute(text("""
        SELECT p.status::text AS status, p.matched_customer_id, p.matched_policy_id,
               r.recommendation::text AS recommendation, r.scenario_route::text AS scenario_route,
               r.decision_path, r.confidence_score, r.processing_time_ms, r.reasoning,
               row_to_json(s) AS signals,
               (SELECT a.details->>'extracted_policy_number' FROM audit_log a
                 WHERE a.payment_id = p.payment_id AND a.action_type = 'received' LIMIT 1) AS extracted_policy
        FROM payments p
        LEFT JOIN payment_recommendations r USING (payment_id)
        LEFT JOIN payment_signals s USING (payment_id)
        WHERE p.payment_id = :i
    """), {"i": payment_id})).mappings().one()
    await db.rollback()

    before = case.get("noise_detail", {}).get("before")  # the un-noised references are the ground truth for parsing
    refs = f"{before['reference_field_1']} {before['reference_field_2']}" if before else \
        f"{case['payment']['reference_field_1']} {case['payment']['reference_field_2']}"
    token = (POLICY_RE.findall(refs) or [None])[0]
    accept = case.get("accept") or [case["expected_recommendation"]]
    scenario = int(row["scenario_route"].split("_")[1]) if row["scenario_route"] else None
    signals = row["signals"] or {}
    return {
        "case_id": case.get("case_id", case["archetype_id"]), "archetype_id": case["archetype_id"],
        "variant": case.get("variant", "clean"), "payment_id": payment_id, "status": row["status"],
        "expected_scenario": case["expected_scenario"], "expected_recommendation": case["expected_recommendation"], "accept": accept,
        "scenario": scenario, "recommendation": row["recommendation"], "decision_path": row["decision_path"],
        "confidence": row["confidence_score"], "scenario_ok": scenario == case["expected_scenario"],
        "recommendation_ok": row["recommendation"] in accept,
        "customer_expected": case["target_customer_id"] or None, "customer_matched": row["matched_customer_id"],
        "policy_expected": case["target_policy_number"] or None, "policy_matched": row["matched_policy_id"],
        "ref_policy_expected": token, "ref_policy_extracted": row["extracted_policy"],
        "name_similarity": signals.get("name_similarity_score"), "used_llm": signals.get("used_llm"),
        "jaro_winkler": signals.get("jaro_winkler_score"), "levenshtein": signals.get("levenshtein_score"),
        "deterministic_score": signals.get("deterministic_score"), "llm_score": signals.get("llm_score"),
        "amount_variance_pct": signals.get("amount_variance_pct"), "is_duplicate": signals.get("is_duplicate_match"),
        "is_third_party": signals.get("is_third_party_payment"), "has_risk_flags": signals.get("has_risk_flags"),
        "seconds": round(wall / len(ingests), 2), "processing_time_ms": row["processing_time_ms"],
        "sender_name": case["payment"]["sender_name"], "noise_detail": case.get("noise_detail"),
        "reasoning": row["reasoning"], "rationale": case["rationale"],
    }


# ── Reporting ────────────────────────────────────────────────────────────────

def pct(values: list[float], q: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round(q * (len(ordered) - 1)))] if ordered else float("nan")


def both(r: dict) -> bool:
    return r["scenario_ok"] and r["recommendation_ok"]


def line(label: str, rs: list[dict]) -> str:
    n = len(rs)
    false_apply = sum(r["recommendation"] == "apply" and "apply" not in r["accept"] for r in rs)
    missed = sum(r["recommendation"] in ("apply", "hold") and r["accept"] == ["escalate"] for r in rs)
    over = sum(r["recommendation"] == "escalate" and "escalate" not in r["accept"] for r in rs)
    return (f"  {label:<26} n={n:>3}  both {sum(map(both, rs)):>3}/{n:<3} route {sum(r['scenario_ok'] for r in rs):>3}/{n:<3} "
            f"rec {sum(r['recommendation_ok'] for r in rs):>3}/{n:<3} false-APPLY {false_apply}  missed-ESCALATE {missed}  over-escalate {over}")


def report(results: list[dict], stability: dict[str, list[dict]]) -> None:
    n = len(results)
    print(f"\n{'=' * 100}\nRESULTS  ({n} cases)\n{'=' * 100}")
    print("By variant")
    for variant in ["clean", "ref_noise", "name_case", "name_typo"]:
        rs = [r for r in results if r["variant"] == variant]
        if rs:
            print(line(variant, rs))
    print(line("ALL", results))

    print("\nBy expected scenario (all variants)")
    for s in sorted({r["expected_scenario"] for r in results}):
        print(line(f"scenario {s}", [r for r in results if r["expected_scenario"] == s]))

    print("\nBy archetype (clean cases only)")
    for a in sorted({r["archetype_id"] for r in results}):
        rs = [r for r in results if r["archetype_id"] == a and r["variant"] == "clean"]
        if rs:
            print(line(a, rs))

    clean = [r for r in results if r["variant"] == "clean"]
    matrix = Counter((r["expected_recommendation"], r["recommendation"]) for r in clean)
    labels = ["apply", "hold", "escalate"]
    print("\nRecommendation confusion, clean cases (rows = expected, cols = predicted)")
    print(f"  {'':<10}" + "".join(f"{str(c):>10}" for c in labels + [None]))
    for e in labels:
        print(f"  {e:<10}" + "".join(f"{matrix[(e, p)]:>10}" for p in labels + [None]))

    print("\nIdentity resolution and parsing, by variant")
    for variant in ["clean", "ref_noise", "name_case", "name_typo"]:
        rs = [r for r in results if r["variant"] == variant]
        if not rs:
            continue
        cust = [r for r in rs if r["customer_expected"]]
        pol = [r for r in rs if r["policy_expected"]]
        parse = [r for r in rs if r["ref_policy_expected"] or r["ref_policy_extracted"]]
        print(f"  {variant:<10} customer {sum(r['customer_matched'] == r['customer_expected'] for r in cust)}/{len(cust)}  "
              f"policy {sum(r['policy_matched'] == r['policy_expected'] for r in pol)}/{len(pol)}  "
              f"policy-number parse {sum(r['ref_policy_extracted'] == r['ref_policy_expected'] for r in rs)}/{len(rs)}")

    secs = [r["seconds"] for r in results]
    proc = [r["processing_time_ms"] / 1000 for r in results if r["processing_time_ms"] is not None]
    print(f"\nLatency per payment, ingest→recommendation: p50 {pct(secs, .5):.1f}s  p95 {pct(secs, .95):.1f}s  max {max(secs):.1f}s")
    print(f"Pipeline processing_time_ms:                p50 {pct(proc, .5):.1f}s  p95 {pct(proc, .95):.1f}s  max {max(proc):.1f}s")
    print(f"Processing failures: {sum(r['status'] == 'processing_failed' for r in results)}")

    if stability:
        unstable = {cid: runs for cid, runs in stability.items() if len({(x['scenario'], x['recommendation']) for x in runs}) > 1}
        spreads = {cid: max(x["name_similarity"] for x in runs) - min(x["name_similarity"] for x in runs)
                   for cid, runs in stability.items() if all(x["name_similarity"] is not None for x in runs)}
        moved = {cid: s for cid, s in spreads.items() if s > 0}
        runs_per = Counter(len(v) for v in stability.values())
        print(f"\nGray-zone stability: {len(stability)} cases used the LLM name score; runs per case: {dict(runs_per)}")
        print(f"  outcome changed between runs (scenario or recommendation): {len(unstable)}/{len(stability)}")
        print(f"  name score changed between runs:                           {len(moved)}/{len(stability)}"
              + (f"   (max spread {max(moved.values()):.1f} points)" if moved else ""))
        for cid, runs in sorted(unstable.items()):
            print(f"    {cid:<34} " + " | ".join(f"S{x['scenario']}/{x['recommendation']}@{x['name_similarity']}" for x in runs))

    bad = [r for r in results if not both(r)]
    print(f"\nDisagreements ({len(bad)}):")
    for r in bad:
        print(f"  {r['case_id']:<34} expected S{r['expected_scenario']}/{'|'.join(r['accept'])}  got S{r['scenario']}/{r['recommendation']}  "
              f"name={r['name_similarity']}  var={r['amount_variance_pct']}  dup={r['is_duplicate']}  path={r['decision_path']}")


async def main(data_path: Path, out: Path, repeat_gray: int, limit: int | None) -> None:
    data = json.loads(data_path.read_text())
    cases = [c for c in data["cases"] if not c["checks"]["failures"]][:limit]
    now = datetime.now(timezone.utc)
    print(f"Target DB: {EVAL_URL.rsplit('@', 1)[-1]}   cases: {len(cases)}   gray-zone repeats: {repeat_gray}", flush=True)

    results: list[dict] = []
    stability: dict[str, list[dict]] = {}
    started = time.monotonic()

    def save() -> None:
        out.write_text(json.dumps({"target_db": EVAL_URL.rsplit("/", 1)[-1], "results": results,
                                   "stability": stability}, indent=2, default=str))

    async with AsyncSessionLocal() as db:
        await load_world(db, data["world"], now)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://eval", timeout=180) as client:
            for i, case in enumerate(cases, 1):
                results.append(await run_case(client, db, case, now))
                if i % 10 == 0 or i == len(cases):
                    elapsed = time.monotonic() - started
                    print(f"  [{i:>3}/{len(cases)}] {elapsed:>4.0f}s elapsed, ~{elapsed / i * (len(cases) - i):.0f}s left", flush=True)
                    save()

            gray = [(c, r) for c, r in zip(cases, results) if r["used_llm"]]
            print(f"Gray-zone repeats: {len(gray)} cases × {repeat_gray} extra runs", flush=True)
            for case, first in gray:
                stability[first["case_id"]] = [{k: first[k] for k in ("scenario", "recommendation", "name_similarity", "llm_score")}]
            for rep in range(repeat_gray):
                for case, first in gray:
                    again = await run_case(client, db, case, now)
                    stability[first["case_id"]].append({k: again[k] for k in ("scenario", "recommendation", "name_similarity", "llm_score")})
                print(f"  repeat {rep + 1}/{repeat_gray} done ({time.monotonic() - started:.0f}s elapsed)", flush=True)
                save()

    save()
    report(results, stability)
    print(f"\nWrote {out}   total {time.monotonic() - started:.0f}s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path(__file__).parent / "data" / "full.json")
    parser.add_argument("--repeat-gray", type=int, default=4)
    parser.add_argument("--limit", type=int, default=None, help="only run the first N cases (debugging)")
    args = parser.parse_args()
    asyncio.run(main(args.data, args.data.with_name(args.data.stem + "_results.json"), args.repeat_gray, args.limit))
