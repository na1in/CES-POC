"""
Paired comparison of run_eval.py result files (LLM ablation).

Scores every arm on the same valid-label set and, for each pair of arms, lists the discordant cases (right in one
arm, wrong in the other) with an exact two-sided McNemar test.

Caveat when reading the "policy-parse" column: results record only the ingest-time parse of the reference text. The
pipeline parses it again (pipeline.py, finding F2) and that second parse decides routing, so with a live LLM two
arms can show the same recorded parse and still route differently.

Usage (from backend/):
  python scripts/eval/compare_runs.py live=data/ablation_live.json regex=data/ablation_regex.json [name=path ...]
The first arm is the reference. Paths are relative to scripts/eval/ unless absolute.
"""
import json
import math
import sys
from itertools import combinations
from pathlib import Path

EVAL_DIR = Path(__file__).parent
CORPUS = EVAL_DIR / "data" / "full.json"
LOW_RISK_METHODS = ("ACH", "Credit Card")


def load_arm(path: str) -> dict[str, dict]:
    p = Path(path) if Path(path).is_absolute() else EVAL_DIR / path
    return {r["case_id"]: r for r in json.loads(p.read_text())["results"]}


def excluded_case_ids(corpus: Path = CORPUS) -> set[str]:
    """The 13 cases the harness doc excludes from the valid-label set of full.json: every S1-hold-name (band
    unverifiable) and S5-near-dup-control paid by a method that is not low-risk (the label assumed ACH). The same
    two rules are applied to any other corpus passed with --corpus."""
    out = set()
    for c in json.loads(corpus.read_text())["cases"]:
        if c["checks"]["failures"]:
            continue
        if c["archetype_id"] == "S1-hold-name" or (
            c["archetype_id"] == "S5-near-dup-control" and c["payment"]["payment_method"] not in LOW_RISK_METHODS
        ):
            out.add(c["case_id"])
    return out


def ok(r: dict) -> bool:
    return bool(r["scenario_ok"] and r["recommendation_ok"])


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return centre - half, centre + half


def mcnemar_exact(b: int, c: int) -> float:
    """Two-sided exact p-value on the discordant pairs (b = only-first-right, c = only-second-right)."""
    n = b + c
    if n == 0:
        return 1.0
    tail = sum(math.comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def summarise(name: str, rs: list[dict]) -> None:
    n = len(rs)
    k = sum(map(ok, rs))
    lo, hi = wilson(k, n)
    false_apply = sum(r["recommendation"] == "apply" and "apply" not in r["accept"] for r in rs)
    over = sum(r["recommendation"] == "escalate" and "escalate" not in r["accept"] for r in rs)
    missed = sum(r["recommendation"] in ("apply", "hold") and r["accept"] == ["escalate"] for r in rs)
    failed = sum(r["status"] == "processing_failed" for r in rs)
    parse_ok = sum(r["ref_policy_extracted"] == r["ref_policy_expected"] for r in rs)
    print(f"  {name:<12} both-correct {k:>3}/{n} = {100 * k / n:5.1f}%  (95% CI {100 * lo:.1f}-{100 * hi:.1f})  "
          f"route {sum(r['scenario_ok'] for r in rs):>3}  rec {sum(r['recommendation_ok'] for r in rs):>3}  "
          f"false-APPLY {false_apply:>2}  missed-ESCALATE {missed}  over-escalate {over:>2}  "
          f"failed {failed}  policy-parse {parse_ok}/{n}")


def main(specs: list[str], corpus: Path = CORPUS) -> None:
    arms = {}
    for spec in specs:
        name, path = spec.split("=", 1)
        arms[name] = load_arm(path)
    ids = set.intersection(*(set(a) for a in arms.values()))
    excl = excluded_case_ids(corpus)
    valid = sorted(ids - excl)
    print(f"Arms: {', '.join(arms)}   cases in every arm: {len(ids)}   excluded: {len(ids & excl)}   valid-label set: {len(valid)}")

    print("\nEach arm on the valid-label set")
    for name, arm in arms.items():
        summarise(name, [arm[i] for i in valid])

    print("\nBy variant (both-correct)")
    variants = sorted({arms[next(iter(arms))][i]["variant"] for i in valid})
    for v in variants:
        vids = [i for i in valid if arms[next(iter(arms))][i]["variant"] == v]
        print(f"  {v:<10} n={len(vids):>3}  " + "  ".join(f"{name} {sum(ok(arm[i]) for i in vids):>3}" for name, arm in arms.items()))

    for (an, a), (bn, b) in combinations(arms.items(), 2):
        only_a = [i for i in valid if ok(a[i]) and not ok(b[i])]
        only_b = [i for i in valid if ok(b[i]) and not ok(a[i])]
        print(f"\n{an} vs {bn}:  right only in {an}: {len(only_a)}   right only in {bn}: {len(only_b)}   "
              f"exact McNemar p = {mcnemar_exact(len(only_a), len(only_b)):.3f}")
        for label, group, first, second in ((f"only {an} right", only_a, a, b), (f"only {bn} right", only_b, b, a)):
            for i in group:
                r, o = first[i], second[i]
                print(f"    [{label}] {i:<36} expected S{r['expected_scenario']}/{'|'.join(r['accept'])}  "
                      f"{an}=S{a[i]['scenario']}/{a[i]['recommendation']} {bn}=S{b[i]['scenario']}/{b[i]['recommendation']}  "
                      f"parse {an}={a[i]['ref_policy_extracted']} {bn}={b[i]['ref_policy_extracted']} (truth {r['ref_policy_expected']})")

    print("\nGray-zone name score (cases where any arm used the LLM name score)")
    for i in sorted(ids):
        if any(arm[i]["used_llm"] for arm in arms.values()):
            cells = "  ".join(f"{n}: name={arm[i]['name_similarity']} -> S{arm[i]['scenario']}/{arm[i]['recommendation']}" for n, arm in arms.items())
            first = arms[next(iter(arms))][i]
            print(f"  {i:<36} {'(excluded)' if i in excl else '          '} expected S{first['expected_scenario']}/{'|'.join(first['accept'])}   {cells}")


if __name__ == "__main__":
    args = sys.argv[1:]
    corpus = CORPUS
    if args[:1] == ["--corpus"]:
        corpus = Path(args[1]) if Path(args[1]).is_absolute() else EVAL_DIR / args[1]
        args = args[2:]
    if len(args) < 1:
        sys.exit(__doc__)
    main(args, corpus)
