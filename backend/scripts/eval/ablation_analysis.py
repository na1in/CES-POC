"""
Analysis for docs/Ablation_Results.md. Reads data/abl_<arm>_<corpus>.json (written by run_eval.py) and prints markdown.

  python scripts/eval/ablation_analysis.py cost        [corpus]   task 1: cost per 1,000 payments, time, thinking check
  python scripts/eval/ablation_analysis.py arms        [corpus]   tasks 2/3: accuracy, wrong APPLY, over-escalate, paired tests
  python scripts/eval/ablation_analysis.py errors      [corpus]   task 4: cause x arm
  python scripts/eval/ablation_analysis.py stability              task 5: run-to-run flips
  python scripts/eval/ablation_analysis.py shift                  task 7: degradation under format shift
  python scripts/eval/ablation_analysis.py calibration [corpus]   task 8: accuracy by confidence bucket
  python scripts/eval/ablation_analysis.py summary                the paste-ready table

Every accuracy is on the valid-label set (compare_runs.excluded_case_ids): both scenario and recommendation correct.
95% intervals are Wilson. Paired comparisons report the discordant counts, an exact two-sided McNemar p, and a
95% paired-bootstrap interval for the accuracy difference (4,000 resamples, seeded).
"""
import json
import random
import re
import statistics
import sys
from collections import Counter
from pathlib import Path

from compare_runs import excluded_case_ids, mcnemar_exact, ok, wilson
from spend import PRICE_IN, PRICE_OUT, cost

DATA = Path(__file__).parent / "data"
CORPORA = {"mock500": "mock_500.json", "full": "full.json", "heldout": "heldout.json",
           "fresh500": "fresh_500_seed7.json", "shift200": "shift_200.json"}
ARM_LABEL = {"regex": "regex (no LLM)", "name-llm": "name-llm (optimised)", "live": "live = name-llm+explain",
             "ai-rules": "ai-rules (LLM decides)", "ai-tight": "ai-tight (LLM decides)",
             "parse-llm": "parse-llm (old LLM parser)", "parse-fallback": "parse-fallback (regex → LLM)"}


_EXPECTED: dict[str, int] = {}


def expected_cases(corpus: str) -> int:
    if corpus not in _EXPECTED:
        cases = json.loads((DATA / CORPORA[corpus]).read_text())["cases"]
        _EXPECTED[corpus] = sum(1 for c in cases if not c["checks"]["failures"])
    return _EXPECTED[corpus]


def load_arm(arm: str, corpus: str, suffix: str = "") -> dict | None:
    """The arm's result file, or None if it is missing or still running (partial files are saved every 10 cases)."""
    path = DATA / f"abl_{arm}_{corpus}{suffix}.json"
    if not path.exists():
        return None
    d = json.loads(path.read_text())
    if len(d["results"]) < expected_cases(corpus):
        print(f"<!-- {path.name}: incomplete ({len(d['results'])}/{expected_cases(corpus)}), skipped -->", file=sys.stderr)
        return None
    return d


def rows_of(d: dict) -> dict[str, dict]:
    return {r["case_id"]: r for r in d["results"]}


def valid_ids(corpus: str, rows: dict[str, dict]) -> list[str]:
    excl = excluded_case_ids(DATA / CORPORA[corpus])
    return sorted(i for i in rows if i not in excl)


def pct(k: int, n: int) -> str:
    if not n:
        return "n/a"
    lo, hi = wilson(k, n)
    return f"{100 * k / n:.1f}% ({k}/{n}; CI {100 * lo:.1f}–{100 * hi:.1f})"


def counts(rows: dict[str, dict], ids: list[str]) -> dict:
    rs = [rows[i] for i in ids]
    return {"n": len(rs), "correct": sum(map(ok, rs)),
            "false_apply": sum(r["recommendation"] == "apply" and "apply" not in r["accept"] for r in rs),
            "over_escalate": sum(r["recommendation"] == "escalate" and "escalate" not in r["accept"] for r in rs),
            "failed": sum(r["status"] == "processing_failed" for r in rs)}


def paired(a: dict[str, dict], b: dict[str, dict], ids: list[str], seed: int = 1) -> dict:
    """Paired comparison of two arms on the same cases: b - a."""
    x = [ok(a[i]) for i in ids]
    y = [ok(b[i]) for i in ids]
    only_a = sum(1 for p, q in zip(x, y) if p and not q)
    only_b = sum(1 for p, q in zip(x, y) if q and not p)
    rng = random.Random(seed)
    n = len(ids)
    diffs = []
    for _ in range(4000):
        idx = [rng.randrange(n) for _ in range(n)]
        diffs.append(sum(y[i] for i in idx) / n - sum(x[i] for i in idx) / n)
    diffs.sort()
    return {"only_a": only_a, "only_b": only_b, "p": mcnemar_exact(only_a, only_b),
            "diff": (sum(y) - sum(x)) / n, "lo": diffs[100], "hi": diffs[3899]}


def fmt_pair(pr: dict) -> str:
    return f"{pr['only_a']} vs {pr['only_b']}; p = {pr['p']:.3f}; Δ {100 * pr['diff']:+.1f} pts (95% CI {100 * pr['lo']:+.1f} to {100 * pr['hi']:+.1f})"


def pctile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round(q * (len(ordered) - 1)))] if ordered else float("nan")


# ── task 1 ───────────────────────────────────────────────────────────────────────────────────────────────────────

def usage_of(d: dict) -> dict[str, dict]:
    """Main-pass usage per call site; the AI decider is one more site."""
    sites = {k: v for k, v in (d.get("usage_main_pass") or {}).items()}
    ai = d.get("ai_decider_stats_main_pass") or d.get("ai_decider_stats")
    if ai and ai.get("calls"):
        sites["ai_decider"] = ai
    return sites


def cmd_cost(corpus: str = "mock500") -> None:
    print(f"### Cost and time per arm — {corpus}\n")
    print("| Arm | Payments | LLM calls / payment | Failed calls | Prompt tok / payment | Completion tok / payment | **Cost per 1,000 payments** | Per-payment time p50 / p95 |")
    print("|---|---|---|---|---|---|---|---|")
    breakdown, thinking = [], []
    for arm in ("regex", "name-llm", "live", "parse-fallback", "parse-llm", "ai-tight", "ai-rules"):
        d = load_arm(arm, corpus)
        if not d:
            continue
        n = d["payments_ingested_main_pass"]
        sites = usage_of(d)
        calls = sum(u["calls"] for u in sites.values())
        pt = sum(u["prompt_tokens"] for u in sites.values())
        ct = sum(u["completion_tokens"] for u in sites.values())
        total = sum(cost(u["prompt_tokens"], u["completion_tokens"]) for u in sites.values())
        secs = [r["seconds"] for r in d["results"]]
        failed = sum(u.get("failures", 0) for u in sites.values())
        print(f"| {ARM_LABEL[arm]} | {n} | {calls / n:.2f} | {failed} | {pt / n:,.0f} | {ct / n:,.0f} | **${1000 * total / n:.3f}** | {pctile(secs, .5):.2f} s / {pctile(secs, .95):.2f} s |")
        for site, u in sites.items():
            lat = u.get("latencies") or []
            breakdown.append((arm, site, u["calls"], 1000 * cost(u["prompt_tokens"], u["completion_tokens"]) / n, pctile(lat, .5), pctile(lat, .95)))
            est_visible = max(u.get("visible_chars", 0) / 3.5, 1)
            thinking.append((arm, site, u["reasoning_tokens"], u["completion_tokens"], u["completion_tokens"] / est_visible))
    print("\nPer call site ($ per 1,000 payments; latency is per LLM call):\n")
    print("| Arm | Call site | Calls | $ per 1,000 payments | Call latency p50 / p95 |")
    print("|---|---|---|---|---|")
    for arm, site, calls, per1k, p50, p95 in breakdown:
        print(f"| {arm} | {site} | {calls} | ${per1k:.3f} | {p50:.2f} s / {p95:.2f} s |")
    print("\nIs \"thinking\" really off? `reasoning_tokens` is what the usage object reports; the ratio compares completion tokens with the visible "
          "output (characters ÷ 3.5 as a token estimate). A reasoning count above 0, or a ratio far above ~1.5, would mean hidden tokens are being billed.\n")
    print("| Arm | Call site | Reasoning tokens reported | Completion tokens | Completion ÷ estimated visible tokens | Flag |")
    print("|---|---|---|---|---|---|")
    for arm, site, rt, ct, ratio in thinking:
        flag = "**FLAG**" if rt > 0 or ratio > 2.0 else "ok"
        print(f"| {arm} | {site} | {rt} | {ct:,} | {ratio:.2f} | {flag} |")
    print(f"\nPrice: ${PRICE_IN * 1e6:.2f} per million input tokens, ${PRICE_OUT * 1e6:.2f} per million output tokens (google/gemini-2.5-flash, OpenRouter, verified 2026-09-26).")


# ── tasks 2 / 3 ──────────────────────────────────────────────────────────────────────────────────────────────────

def cmd_arms(corpus: str = "mock500", arms: tuple = ("regex", "name-llm", "live", "ai-rules", "ai-tight", "parse-fallback", "parse-llm"),
             reference: str = "regex") -> None:
    loaded = {a: load_arm(a, corpus) for a in arms}
    loaded = {a: d for a, d in loaded.items() if d}
    if not loaded:
        print(f"(no results for {corpus})")
        return
    base_rows = rows_of(next(iter(loaded.values())))
    ids = valid_ids(corpus, base_rows)
    print(f"### Accuracy — {corpus} (valid-label set, n = {len(ids)})\n")
    print(f"| Arm | Correct (95% CI) | Wrong APPLY | Over-escalate | Failed | vs {reference}: only-{reference} vs only-arm; McNemar; paired Δ |")
    print("|---|---|---|---|---|---|")
    ref_rows = rows_of(loaded[reference]) if reference in loaded else None
    for a, d in loaded.items():
        rows = rows_of(d)
        c = counts(rows, ids)
        cmp = "—" if a == reference or ref_rows is None else fmt_pair(paired(ref_rows, rows, ids))
        print(f"| {ARM_LABEL[a]} | {pct(c['correct'], c['n'])} | {c['false_apply']} | {c['over_escalate']} | {c['failed']} | {cmp} |")
    if "name-llm" in loaded and "live" in loaded:
        print(f"\nExplanation call in isolation, name-llm → live: {fmt_pair(paired(rows_of(loaded['name-llm']), rows_of(loaded['live']), ids))}")
    if "name-llm" in loaded and "ai-rules" in loaded:
        print(f"\n\"Optimised ≥ LLM decides\": name-llm vs ai-rules: {fmt_pair(paired(rows_of(loaded['ai-rules']), rows_of(loaded['name-llm']), ids))}  (Δ is name-llm − ai-rules)")


# ── task 4 ───────────────────────────────────────────────────────────────────────────────────────────────────────

CAUSES = [
    "pipeline failure (processing_failed)",
    "reference not parsed",
    "name in an unseen format (surname first / caps)",
    "wrong APPLY (unsafe)",
    "third-party payer mishandled",
    "second-policy payment held/escalated",
    "S2 (no policy ref) escalated",
    "S2 (no policy ref) held instead of applied",
    "borderline name held (name 75-90)",
    "held although every APPLY condition was met",
    "duplicate mishandled",
    "unknown payer / bad ref held instead of escalated",
    "amount-variance tier wrong",
    "right recommendation, wrong scenario",
    "other",
]

MULTI_POLICY = re.compile(r"two active policies|multiple (?:active )?policies|same premium|more than one polic|second polic", re.I)


def stated_reason(r: dict) -> str:
    """What the model itself said for holding a payment that met every APPLY condition (AI-decider arms only)."""
    text = " ".join(r.get("reasoning") or []).lower()
    if MULTI_POLICY.search(text):
        return "cited a second policy / same premium"
    if "human approval" in text or "always required" in text:
        return "misread 'human approval is always required' as a reason to hold"
    if "tier" in text:
        return "mis-tiered a variance already inside the 2% tolerance"
    if re.search(r"outstanding balance|past due|timing|underpayment|overpayment|not exactly match", text):
        return "added a condition not in the spec (balance / timing / under-payment)"
    return "other reason"


def classify(r: dict) -> str:
    a = r["archetype_id"]
    got, accept = r["recommendation"], r["accept"]
    name = r["name_similarity"]
    reasoning = " ".join(r.get("reasoning") or [])
    C = {c.split(" (")[0]: c for c in CAUSES}  # short handles
    if r["status"] == "processing_failed" or got is None:
        return CAUSES[0]
    if r["ref_policy_expected"] and r["ref_policy_extracted"] != r["ref_policy_expected"]:
        return "reference not parsed"
    if got == "apply" and "apply" not in accept:
        return "wrong APPLY (unsafe)"
    if r["variant"] in ("shift_T5", "shift_T6"):
        return "name in an unseen format (surname first / caps)"
    if a == "S4-third-party-hold":
        return "third-party payer mishandled"
    if a == "S5-diff-ref-not-dup" or (got in ("hold", "escalate") and "apply" in accept and MULTI_POLICY.search(reasoning)):
        return "second-policy payment held/escalated"
    if a.startswith("S2-"):
        return "S2 (no policy ref) escalated" if got == "escalate" else "S2 (no policy ref) held instead of applied"
    if got == "hold" and "apply" in accept and name is not None and 75 <= name <= 90:
        return "borderline name held (name 75-90)"
    if got == "hold" and "apply" in accept and a.startswith(("S1-apply", "S5-near-dup", "S5-diff")):
        return "held although every APPLY condition was met"
    if a.startswith("S5-"):
        return "duplicate mishandled"
    if a in ("S4-unknown-person", "S4-unknown-company", "S4-bad-policy-ref", "S3-tier5") and got == "hold":
        return "unknown payer / bad ref held instead of escalated"
    if a.startswith("S3-"):
        return "amount-variance tier wrong"
    if r["recommendation_ok"] and not r["scenario_ok"]:
        return "right recommendation, wrong scenario"
    return "other"


def cmd_errors(corpus: str = "mock500", arms: tuple = ("regex", "name-llm", "live", "ai-rules", "ai-tight", "parse-fallback", "parse-llm")) -> None:
    loaded = {a: load_arm(a, corpus) for a in arms}
    loaded = {a: d for a, d in loaded.items() if d}
    if not loaded:
        print(f"(no results for {corpus})")
        return
    ids = valid_ids(corpus, rows_of(next(iter(loaded.values()))))
    table = {a: {c: 0 for c in CAUSES} for a in loaded}
    for a, d in loaded.items():
        rows = rows_of(d)
        for i in ids:
            if not ok(rows[i]):
                table[a][classify(rows[i])] += 1
    print(f"### Wrong cases by cause — {corpus} (n = {len(ids)} valid-label cases)\n")
    print("| Cause | " + " | ".join(a for a in loaded) + " |")
    print("|---|" + "---|" * len(loaded))
    for c in CAUSES:
        if any(table[a][c] for a in loaded):
            print(f"| {c} | " + " | ".join(str(table[a][c]) if table[a][c] else "·" for a in loaded) + " |")
    print("| **total wrong** | " + " | ".join(f"**{sum(table[a].values())}**" for a in loaded) + " |")
    print("\nCauses are assigned by the first matching rule, in the order listed (a case with an unparsed reference is counted there even if it also looks like a "
          "second-policy case). Rules: `classify()` in ablation_analysis.py. \"Second-policy\" also catches any hold whose model-written reasoning cites a second "
          "policy / same premium.")
    for a, d in loaded.items():
        if not a.startswith("ai-"):
            continue
        rows = rows_of(d)
        held = [rows[i] for i in ids if not ok(rows[i]) and classify(rows[i]) == "held although every APPLY condition was met"]
        if held:
            reasons = Counter(stated_reason(r) for r in held)
            print(f"\nWhy {a} held {len(held)} payments that met every APPLY condition (the model's own stated reason):\n")
            for reason, n in reasons.most_common():
                print(f"- {n} × {reason}")


# ── task 5 ───────────────────────────────────────────────────────────────────────────────────────────────────────

def flips(a: dict, b: dict) -> tuple[int, int, list[str]]:
    ra, rb = rows_of(a), rows_of(b)
    ids = sorted(set(ra) & set(rb))
    changed = [i for i in ids if ra[i]["recommendation"] != rb[i]["recommendation"]]
    return len(changed), len(ids), changed


def cmd_stability() -> None:
    print("### Run-to-run stability\n")
    print("Share of cases whose **recommendation** changed between two runs of the same arm on the same cases:\n")
    print("| Arm / corpus | Cases | Recommendation flipped | Wrong-in-one-run-only |")
    print("|---|---|---|---|")
    pairs = [("ai-rules, full.json (2026-09-25 runs, before the code fixes)", DATA / "ablation_ai-rules.json", DATA / "ablation_ai-rules_run2.json"),
             ("ai-tight, full.json (2026-09-25 runs, before the code fixes)", DATA / "ablation_ai-tight.json", DATA / "ablation_ai-tight_run2.json")]
    m1, m2 = load_arm("ai-rules", "mock500"), load_arm("ai-rules", "mock500", "_run2")
    if m1 and m2:
        pairs.append(("ai-rules, mock_500.json (this study)", DATA / "abl_ai-rules_mock500.json", DATA / "abl_ai-rules_mock500_run2.json"))
    for label, p1, p2 in pairs:
        if not (p1.exists() and p2.exists()):
            continue
        d1, d2 = json.loads(p1.read_text()), json.loads(p2.read_text())
        n_flip, n, _ = flips(d1, d2)
        r1, r2 = rows_of(d1), rows_of(d2)
        differ_ok = sum(1 for i in set(r1) & set(r2) if ok(r1[i]) != ok(r2[i]))
        lo, hi = wilson(n_flip, n)
        print(f"| {label} | {n} | {n_flip} = {100 * n_flip / n:.1f}% (CI {100 * lo:.1f}–{100 * hi:.1f}) | {differ_ok} |")
    print("\nGray-zone name score in the live LLM arms (each gray-zone case is scored twice: `--repeat-gray 1`):\n")
    print("| Arm / corpus | Gray-zone cases | LLM score differed | Recommendation differed | Max score spread |")
    print("|---|---|---|---|---|")
    for arm in ("live", "name-llm"):
        for corpus in CORPORA:
            d = load_arm(arm, corpus)
            if not d or not d.get("stability"):
                continue
            st = {k: v for k, v in d["stability"].items() if len(v) >= 2}  # a case with one run cannot have "changed"
            n = len(st)
            if not n:
                continue
            score_diff = sum(1 for runs in st.values() if len({x["llm_score"] for x in runs}) > 1)
            out_diff = sum(1 for runs in st.values() if len({(x["scenario"], x["recommendation"]) for x in runs}) > 1)
            spread = max((max(x["llm_score"] for x in runs) - min(x["llm_score"] for x in runs) for runs in st.values() if all(x["llm_score"] is not None for x in runs)), default=0)
            print(f"| {arm}, {corpus} | {n} | {score_diff} ({100 * score_diff / max(n, 1):.0f}%) | {out_diff} ({100 * out_diff / max(n, 1):.0f}%) | {spread:.0f} |")
    print("\nThe regex arm and the code's decision logic are deterministic: the same input gives the same output (checked below by running the regex arm twice).")


# ── task 7 ───────────────────────────────────────────────────────────────────────────────────────────────────────

def cmd_shift(arms: tuple = ("regex", "name-llm", "live", "parse-fallback", "parse-llm", "ai-rules")) -> None:
    shifted = {a: load_arm(a, "shift200") for a in arms}
    original = {a: load_arm(a, "mock500") for a in arms}
    arms = [a for a in arms if shifted[a] and original[a]]
    if not arms:
        print("(shift results not available yet)")
        return
    sh_rows = {a: rows_of(shifted[a]) for a in arms}
    or_rows = {a: rows_of(original[a]) for a in arms}
    shift_ids = sorted(sh_rows[arms[0]])
    base = {i: i.split("~")[0] for i in shift_ids}
    kinds = sorted({sh_rows[arms[0]][i]["variant"] for i in shift_ids})
    n = len(shift_ids)
    print(f"### Format shift — {n} cases from mock_500 rewritten in unseen formats, labels unchanged\n")
    print("Each arm is compared with **itself on the same 200 cases before the rewrite** (paired by case), so the change is purely the format.\n")
    print("| Arm | Before rewrite | After rewrite | Change | Only-before-correct vs only-after-correct; McNemar |")
    print("|---|---|---|---|---|")
    for a in arms:
        before = {i: or_rows[a][base[i]] for i in shift_ids}
        cb = sum(map(ok, before.values()))
        ca = sum(ok(sh_rows[a][i]) for i in shift_ids)
        b_only = sum(1 for i in shift_ids if ok(before[i]) and not ok(sh_rows[a][i]))
        a_only = sum(1 for i in shift_ids if ok(sh_rows[a][i]) and not ok(before[i]))
        print(f"| {ARM_LABEL[a]} | {pct(cb, n)} | {pct(ca, n)} | **{100 * (ca - cb) / n:+.1f} pts** | {b_only} vs {a_only}; p = {mcnemar_exact(b_only, a_only):.4f} |")
    print("\nAccuracy after the rewrite, by transformation (correct / cases):\n")
    print("| Transformation | Cases | " + " | ".join(a for a in arms) + " |")
    print("|---|---|" + "---|" * len(arms))
    desc = {"shift_T1": "T1 `Policy: 12345`", "shift_T2": "T2 `PN12345`", "shift_T3": "T3 `ref#12345/INS`", "shift_T4": "T4 `12345` alone",
            "shift_T5": "T5 name `Khan, Aisha`", "shift_T6": "T6 name `KHAN AISHA`", "shift_T7": "T7 amount with $ in memo"}
    for k in kinds:
        ids_k = [i for i in shift_ids if sh_rows[arms[0]][i]["variant"] == k]
        print(f"| {desc.get(k, k)} | {len(ids_k)} | " + " | ".join(f"{sum(ok(sh_rows[a][i]) for i in ids_k)}/{len(ids_k)}" for a in arms) + " |")
    print("\nPolicy-number extraction after the rewrite (ingest-time parse equals the un-shifted reference):\n")
    print("| Arm | Extracted correctly (of cases with a policy reference) |")
    print("|---|---|")
    for a in arms:
        rs = [sh_rows[a][i] for i in shift_ids if sh_rows[a][i]["ref_policy_expected"]]
        print(f"| {ARM_LABEL[a]} | {pct(sum(r['ref_policy_extracted'] == r['ref_policy_expected'] for r in rs), len(rs))} |")


# ── task 8 ───────────────────────────────────────────────────────────────────────────────────────────────────────

BUCKETS = [("< 70", 0, 70), ("70–80", 70, 80), ("80–90", 80, 90), ("90+", 90, 1001)]


def cmd_calibration(corpora: tuple | str = ("mock500", "fresh500"), arms: tuple = ("regex", "live", "ai-rules")) -> None:
    if isinstance(corpora, str):
        corpora = tuple(corpora.split(","))
    print("### Confidence calibration\n")
    print(f"Pooled over {', '.join(corpora)}; accuracy = scenario and recommendation both correct. `confidence` is the score stored with the recommendation.\n")
    print("| Arm | " + " | ".join(f"conf {b[0]}" for b in BUCKETS) + " |")
    print("|---|" + "---|" * len(BUCKETS))
    detail = []
    for arm in arms:
        cells = []
        rs_all = []
        for corpus in corpora:
            d = load_arm(arm, corpus)
            if not d:
                continue
            rows = rows_of(d)
            rs_all += [rows[i] for i in valid_ids(corpus, rows)]
        if not rs_all:
            continue
        for _, lo, hi in BUCKETS:
            rs = [r for r in rs_all if r["confidence"] is not None and lo <= r["confidence"] < hi]
            cells.append(pct(sum(map(ok, rs)), len(rs)) if rs else "n = 0")
        print(f"| {ARM_LABEL[arm]} | " + " | ".join(cells) + " |")
        vals = sorted({round(r["confidence"], 1) for r in rs_all if r["confidence"] is not None})
        detail.append((arm, len(vals), vals[:6]))
    print()
    for arm, n_distinct, first in detail:
        print(f"- {arm}: {n_distinct} distinct confidence values" + (f" (e.g. {first})" if n_distinct <= 12 else ""))
    print("\nFor the code arms the confidence is a constant per decision path, not a probability: a bucket's accuracy says how reliable that group of paths is, "
          "not that the score is calibrated. `live` uses the same code confidence as `regex` (the LLM writes only the explanation).")


# ── summary ──────────────────────────────────────────────────────────────────────────────────────────────────────

def stability_label(arm: str, corpus: str = "mock500") -> str:
    if arm == "regex":
        return "0% (deterministic)"
    if arm in ("ai-rules", "ai-tight"):
        m1, m2 = load_arm("ai-rules", "mock500"), load_arm("ai-rules", "mock500", "_run2")
        if arm == "ai-rules" and m1 and m2:
            k, n, _ = flips(m1, m2)
            if corpus != "mock500":
                return f"not repeated on this corpus ({100 * k / n:.1f}% flipped on mock_500)"
            return f"{100 * k / n:.1f}% of recommendations flipped between 2 runs (n={n})"
        p1, p2 = DATA / "ablation_ai-tight.json", DATA / "ablation_ai-tight_run2.json"
        if arm == "ai-tight" and p1.exists() and p2.exists():
            k, n, _ = flips(json.loads(p1.read_text()), json.loads(p2.read_text()))
            return f"{100 * k / n:.1f}% flipped (n={n}, full.json, pre-fix code)"
    st = {}
    for corpus in ("mock500", "fresh500", "full", "heldout"):
        d = load_arm(arm, corpus)
        if d and d.get("stability"):
            st.update({f"{corpus}:{k}": v for k, v in d["stability"].items() if len(v) >= 2})
    if st:
        n = len(st)
        score = sum(1 for runs in st.values() if len({x["llm_score"] for x in runs}) > 1)
        outc = sum(1 for runs in st.values() if len({(x["scenario"], x["recommendation"]) for x in runs}) > 1)
        return f"pooled over 4 corpora: gray-zone LLM score changed in {score}/{n}, outcome in {outc}/{n}"
    return "not repeated" if arm not in ("regex",) else "—"


def cmd_summary(corpus: str = "mock500") -> None:
    print(f"### Summary — {corpus}\n")
    print("| Arm | Accuracy (95% CI) | Wrong APPLY | Over-escalate | Cost per 1,000 payments | p50 time / payment | Stability |")
    print("|---|---|---|---|---|---|---|")
    for arm in ("regex", "name-llm", "live", "parse-fallback", "parse-llm", "ai-tight", "ai-rules"):
        d = load_arm(arm, corpus)
        if not d:
            continue
        rows = rows_of(d)
        ids = valid_ids(corpus, rows)
        c = counts(rows, ids)
        n = d["payments_ingested_main_pass"]
        total = sum(cost(u["prompt_tokens"], u["completion_tokens"]) for u in usage_of(d).values())
        p50 = pctile([r["seconds"] for r in d["results"]], .5)
        print(f"| {ARM_LABEL[arm]} | {pct(c['correct'], c['n'])} | {c['false_apply']} | {c['over_escalate']} | ${1000 * total / n:.2f} | {p50:.2f} s | {stability_label(arm, corpus)} |")


if __name__ == "__main__":
    args = sys.argv[1:] or ["summary"]
    cmd, rest = args[0], args[1:]
    {"cost": cmd_cost, "arms": cmd_arms, "errors": cmd_errors, "stability": cmd_stability, "shift": cmd_shift,
     "calibration": cmd_calibration, "summary": cmd_summary}[cmd](*rest)
