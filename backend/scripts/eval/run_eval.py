"""
Runs generated evaluation cases through the real ingest endpoint and pipeline (in-process, against an
isolated database) and scores the outcomes against the archetype labels.

Each case runs in isolation: payments and derived rows are cleared before it, so cases cannot trigger
each other's duplicate detection. Only a case's own prior payment (if any) is ingested first.
Cases whose name score used the LLM ("gray zone") are then re-run --repeat-gray more times to measure
how stable the outcome is.

Safety: refuses to run unless the target database name ends in "_eval".

Usage (from backend/):  python scripts/eval/run_eval.py [--data scripts/eval/data/full.json] [--repeat-gray 4]

LLM ablation: --llm regex|defaults replaces the pipeline's three LLM call sites with non-LLM equivalents (see
apply_llm_mode); pair it with --out so a live result file is not overwritten.
"""
import argparse
import asyncio
import copy
import importlib
import json
import os
import re
import subprocess
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


# ── LLM ablation ─────────────────────────────────────────────────────────────
# Until 2026-09-26 the pipeline called the LLM in three places: reference parsing (at ingest and again in the pipeline),
# gray-zone name scoring, and analyst-facing reasoning text. Reference parsing is now a deterministic regex in the app
# itself, so two call sites remain (name scoring and reasoning text). In a no-LLM arm both are replaced inside this
# process, so production code is untouched. A tripwire client counts any request that still reaches an LLM client (the
# call sites swallow exceptions and fall back, so a failure alone would be invisible); the count must be 0.
# Result files from before that date were produced with an LLM (or a harness-side regex) parser; see
# docs/Evaluation_Harness.md.
#
# Every call site that IS live in an arm is wrapped by a usage recorder (tokens, reasoning tokens, wall time per call),
# so cost and latency can be reported per call site for every arm.

LLM_CALLS_ATTEMPTED = 0
LLM_MODES = ["live", "regex", "defaults", "name-llm", "name-llm+explain", "parse-llm", "parse-fallback",
             "ai-rules", "ai-open", "ai-tight"]

USAGE: dict[str, dict] = {}          # call site -> totals
EXPLANATIONS: list[dict] = []        # (input, output) of every reasoning call, for the faithfulness check
CURRENT_CASE: dict = {"id": None, "pass": 0}


def _site(name: str) -> dict:
    return USAGE.setdefault(name, {"calls": 0, "failures": 0, "prompt_tokens": 0, "completion_tokens": 0,
                                   "reasoning_tokens": 0, "visible_chars": 0, "seconds": 0.0, "latencies": []})


class _UsageClient:
    """Wraps a real client and records tokens, reasoning tokens and wall time per call site."""

    def __init__(self, site: str, real) -> None:
        self.site, self.real = site, real
        self.chat = self
        self.completions = self

    async def create(self, *args, **kwargs):
        s = _site(self.site)
        started = time.monotonic()
        try:
            response = await self.real.chat.completions.create(*args, **kwargs)
        except Exception:
            s["failures"] += 1
            raise
        elapsed = time.monotonic() - started
        usage = response.usage
        details = getattr(usage, "completion_tokens_details", None) if usage else None
        s["calls"] += 1
        s["seconds"] += elapsed
        s["latencies"].append(round(elapsed, 3))
        s["prompt_tokens"] += (usage.prompt_tokens or 0) if usage else 0
        s["completion_tokens"] += (usage.completion_tokens or 0) if usage else 0
        s["reasoning_tokens"] += (getattr(details, "reasoning_tokens", 0) or 0) if details else 0
        try:
            s["visible_chars"] += len(response.choices[0].message.content or "")
        except Exception:  # noqa: BLE001
            pass
        return response


def install_usage(module, site: str) -> None:
    original = module._get_client
    module._get_client = lambda: _UsageClient(site, original())


class _TripwireClient:
    def __init__(self) -> None:
        self.chat = self
        self.completions = self

    async def create(self, *args, **kwargs):
        global LLM_CALLS_ATTEMPTED
        LLM_CALLS_ATTEMPTED += 1
        raise RuntimeError("LLM call attempted in a no-LLM arm")


def apply_llm_mode(mode: str) -> None:
    """
    live (= name-llm+explain, since parsing became regex): the gray-zone name LLM and the LLM explanation are live.
    regex: the app's own deterministic parser, deterministic name score, template explanations: no LLM anywhere.
    name-llm: as regex, except the gray-zone name score is live. ("Optimised" configuration: LLM only where it earns it.)
    name-llm+explain: name-llm plus the live LLM explanation call. Identical to live on today's code (the alias exists
        so the arm can be reported under both names and its explanation cost priced separately).
    parse-llm: experiment-only. The LLM reference parser production used until 2026-09-26 (legacy_parser.llm_parse),
        name LLM live, template explanations.
    parse-fallback: experiment-only. Regex parser first, the LLM only when the regex finds nothing (the "keep an LLM
        fallback" design), name LLM live, template explanations.
    defaults: as regex, but the reference parser returns no policy number (a total parse failure).
    ai-rules / ai-open / ai-tight: as regex, and the scenario handlers are replaced so an LLM makes the final
        recommendation (see ai_decider.py).
    """
    if mode == "name-llm+explain":
        mode = "live"
    from app.routers import payments as payments_router
    from app.services import ingest, pipeline
    from app.services.agent import reasoning
    from app.services.signals import matching

    name_live = mode in ("live", "name-llm", "parse-llm", "parse-fallback")
    explain_live = mode == "live"

    async def parse_defaults(ref1, ref2):
        return {"extracted_policy_number": None, "payment_intent": "unknown", "period_count": 1}

    async def no_llm_name_score(a, b):
        return None

    async def reasoning_fallback(scenario_num, recommendation, context_summary, fallback_reasoning, fallback_action):
        return fallback_reasoning, fallback_action

    if mode == "defaults":
        for module in (ingest, pipeline, payments_router):  # pipeline and the router import the parser by name
            module.parse_reference_fields = parse_defaults
    if mode in ("parse-llm", "parse-fallback"):
        import legacy_parser  # sits next to this script

        parser_fn = legacy_parser.llm_parse if mode == "parse-llm" else legacy_parser.regex_then_llm
        for module in (ingest, pipeline, payments_router):
            module.parse_reference_fields = parser_fn
        install_usage(legacy_parser, "reference_parse")

    if name_live:
        install_usage(matching, "name_gray_zone")
    else:
        matching._llm_score = no_llm_name_score
        matching._get_client = _TripwireClient

    if explain_live:
        install_usage(reasoning, "reasoning_text")
        real_reasoning = reasoning.get_reasoning

        async def logged_reasoning(scenario_num, recommendation, context_summary, fallback_reasoning, fallback_action):
            out = await real_reasoning(scenario_num, recommendation, context_summary, fallback_reasoning, fallback_action)
            EXPLANATIONS.append({"case_id": CURRENT_CASE["id"], "pass": CURRENT_CASE["pass"], "scenario": scenario_num,
                                 "recommendation": recommendation, "context_summary": context_summary,
                                 "reasoning": out[0], "suggested_action": out[1],
                                 "used_fallback": out[0] == fallback_reasoning})
            return out

        reasoning.get_reasoning = logged_reasoning
        for n in range(1, 6):  # each scenario handler imports get_reasoning by name
            importlib.import_module(f"app.services.agent.scenarios.sc{n}").get_reasoning = logged_reasoning
    else:
        reasoning.get_reasoning = reasoning_fallback
        for n in range(1, 6):
            importlib.import_module(f"app.services.agent.scenarios.sc{n}").get_reasoning = reasoning_fallback
        reasoning._get_client = _TripwireClient

    if mode in ("ai-rules", "ai-open", "ai-tight"):
        import ai_decider  # sits next to this script

        ai_decider.install(mode)


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
    CURRENT_CASE["id"] = case.get("case_id", case["archetype_id"])
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


def _provenance(data_path: Path, llm_mode: str) -> dict:
    """What produced this file: enough to reproduce or to discard it later."""
    def git(*args: str) -> str:
        try:
            return subprocess.run(["git", *args], cwd=BACKEND, capture_output=True, text=True, timeout=20).stdout.strip()
        except Exception:  # noqa: BLE001
            return ""
    return {"commit": git("rev-parse", "HEAD"), "app_dirty": bool(git("status", "--porcelain", "--", "app")),
            "model": "google/gemini-2.5-flash", "llm_mode": llm_mode, "data": data_path.name,
            "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}


async def main(data_path: Path, out: Path, repeat_gray: int, limit: int | None, llm_mode: str = "live") -> None:
    data = json.loads(data_path.read_text())
    cases = [c for c in data["cases"] if not c["checks"]["failures"]][:limit]
    now = datetime.now(timezone.utc)
    apply_llm_mode(llm_mode)
    print(f"Target DB: {EVAL_URL.rsplit('@', 1)[-1]}   cases: {len(cases)}   gray-zone repeats: {repeat_gray}   llm: {llm_mode}", flush=True)

    meta = _provenance(data_path, llm_mode)
    results: list[dict] = []
    stability: dict[str, list[dict]] = {}
    main_pass: dict = {}                   # usage snapshot taken when the main pass ends (repeat passes excluded)
    started = time.monotonic()
    payments_main = sum(1 + len(c["prior_payments"]) for c in cases)

    def save() -> None:
        ai = sys.modules["ai_decider"].STATS if "ai_decider" in sys.modules else None
        out.write_text(json.dumps({
            "target_db": EVAL_URL.rsplit("/", 1)[-1], "llm_mode": llm_mode, "meta": meta,
            "llm_calls_attempted": LLM_CALLS_ATTEMPTED,
            "payments_ingested_main_pass": payments_main,
            "usage_main_pass": main_pass.get("usage", copy.deepcopy(USAGE)),
            "usage_all_passes": USAGE,
            "ai_decider_stats": ai, "ai_decider_stats_main_pass": main_pass.get("ai", copy.deepcopy(ai)),
            "explanations": EXPLANATIONS,
            "results": results, "stability": stability}, indent=2, default=str))

    async with AsyncSessionLocal() as db:
        await load_world(db, data["world"], now)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://eval", timeout=180) as client:
            CURRENT_CASE["pass"] = 0
            for i, case in enumerate(cases, 1):
                results.append(await run_case(client, db, case, now))
                if i % 10 == 0 or i == len(cases):
                    elapsed = time.monotonic() - started
                    print(f"  [{i:>3}/{len(cases)}] {elapsed:>4.0f}s elapsed, ~{elapsed / i * (len(cases) - i):.0f}s left", flush=True)
                    save()
            main_pass["usage"] = copy.deepcopy(USAGE)
            if "ai_decider" in sys.modules:
                main_pass["ai"] = copy.deepcopy(sys.modules["ai_decider"].STATS)

            gray = [(c, r) for c, r in zip(cases, results) if r["used_llm"]]
            print(f"Gray-zone repeats: {len(gray)} cases × {repeat_gray} extra runs", flush=True)
            for case, first in gray:
                stability[first["case_id"]] = [{k: first[k] for k in ("scenario", "recommendation", "name_similarity", "llm_score")}]
            for rep in range(repeat_gray):
                CURRENT_CASE["pass"] = rep + 1
                for case, first in gray:
                    again = await run_case(client, db, case, now)
                    stability[first["case_id"]].append({k: again[k] for k in ("scenario", "recommendation", "name_similarity", "llm_score")})
                print(f"  repeat {rep + 1}/{repeat_gray} done ({time.monotonic() - started:.0f}s elapsed)", flush=True)
                save()

    save()
    report(results, stability)
    if llm_mode not in ("live", "name-llm+explain"):
        print(f"\nLLM requests attempted at the call sites meant to be off in this arm: {LLM_CALLS_ATTEMPTED} (must be 0)")
    for site, u in main_pass.get("usage", {}).items():
        print(f"LLM site {site}: {u['calls']} calls ({u['failures']} failed), {u['prompt_tokens']:,} prompt + {u['completion_tokens']:,} completion "
              f"tokens ({u['reasoning_tokens']:,} reasoning), {u['seconds'] / max(u['calls'], 1):.2f}s avg  [main pass, {payments_main} payments]")
    if "ai_decider" in sys.modules:
        s_ = main_pass.get("ai", sys.modules["ai_decider"].STATS)
        print(f"AI decider: {s_['calls']} calls, {s_['retries']} retries, {s_['failures']} failed decisions (counted as ESCALATE), "
              f"{s_['seconds'] / max(s_['calls'], 1):.1f}s avg, {s_['prompt_tokens']:,} prompt + {s_['completion_tokens']:,} completion tokens "
              f"({s_.get('reasoning_tokens', 0):,} reasoning)")
    print(f"\nWrote {out}   total {time.monotonic() - started:.0f}s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, default=Path(__file__).parent / "data" / "full.json")
    parser.add_argument("--repeat-gray", type=int, default=4)
    parser.add_argument("--limit", type=int, default=None, help="only run the first N cases (debugging)")
    parser.add_argument("--llm", choices=LLM_MODES, default="live",
                        help="live (= name-llm+explain) = gray-zone name LLM and LLM explanations live (default); "
                             "regex / defaults = no-LLM arms; name-llm = only the gray-zone name LLM live; "
                             "parse-llm / parse-fallback = experiment-only LLM reference parsers (legacy_parser.py); "
                             "ai-rules / ai-open / ai-tight = an LLM makes the final recommendation (see ai_decider.py)")
    parser.add_argument("--out", type=Path, default=None, help="result file (default: <data>_results.json, which overwrites)")
    args = parser.parse_args()
    out = args.out or args.data.with_name(args.data.stem + "_results.json")
    asyncio.run(main(args.data, out, args.repeat_gray, args.limit, args.llm))
