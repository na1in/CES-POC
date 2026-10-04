"""
Builds data/shift_200.json: 200 cases from data/mock_500.json re-written in formats the rules were never built for,
with the labels unchanged. It measures how much each arm degrades when the input format shifts.

Seven transformations (each case gets exactly one, so a loss can be attributed to a format):
  T1  reference "Policy: 12345"           (30)     T5  name "Khan, Aisha"        (30)
  T2  reference "PN12345"                 (30)     T6  name "KHAN AISHA"         (30)  (surname first, upper case)
  T3  reference "ref#12345/INS"           (30)     T7  a currency amount in the memo, e.g. "pmt $1,500.00"  (20)
  T4  reference "12345" alone             (30)

Rules
- Deterministic (seeded); nothing here is tuned on results. The regex parser was written before these formats were
  chosen; "Policy: 12345" happens to be covered by it, PN12345 / ref#12345/INS / bare 12345 are not.
- The same format is applied to prior payments in duplicate cases (the duplicate rule compares the reference and the
  sender name exactly, so transforming only one payment would turn a real duplicate into a non-duplicate and change the
  label).
- The original, un-shifted references are kept in noise_detail.before, which run_eval.py uses as the ground truth for
  policy-number extraction.
- Cases whose labels cannot be validated independently (S1-hold-name, near-duplicate controls paid by Wire/Check) are
  excluded, as everywhere else.

Usage (from backend/):  python scripts/eval/build_shift.py
"""
import copy
import json
import random
import re
from pathlib import Path

DATA = Path(__file__).parent / "data"
SEED = 20260926
POL = re.compile(r"POL-(\d{5})")
LOW_RISK_METHODS = ("ACH", "Credit Card")

REF_FORMATS = {
    "T1": lambda n: f"Policy: {n}",
    "T2": lambda n: f"PN{n}",
    "T3": lambda n: f"ref#{n}/INS",
    "T4": lambda n: f"{n}",
}
SIZES = {"T1": 30, "T2": 30, "T3": 30, "T4": 30, "T5": 30, "T6": 30, "T7": 20}
PERSON_ARCHETYPES = ("S1-apply-a", "S1-apply-b", "S1-hold-risk", "S2-apply-single", "S2-apply-single-card",
                     "S2-apply-multi-unique", "S3-tier3-above", "S3-tier3-below")


def original_refs(case: dict) -> tuple[str, str]:
    before = (case.get("noise_detail") or {}).get("before")
    p = case["payment"]
    return (before["reference_field_1"], before["reference_field_2"]) if before else (p["reference_field_1"], p["reference_field_2"])


def excluded(case: dict) -> bool:
    return case["archetype_id"] == "S1-hold-name" or (
        case["archetype_id"] == "S5-near-dup-control" and case["payment"]["payment_method"] not in LOW_RISK_METHODS)


def reorder_name(name: str, upper: bool) -> str:
    tokens = name.replace(",", " ").split()
    if len(tokens) < 2:
        return name
    first, last, middle = tokens[0], tokens[-1], tokens[1:-1]
    given = " ".join([first, *middle])
    return f"{last} {given}".upper() if upper else f"{last}, {given}"


def transform_payment(payment: dict, kind: str) -> dict:
    p = copy.deepcopy(payment)
    if kind in REF_FORMATS:
        match = POL.search(p["reference_field_1"])
        if match:
            number = match.group(1)
            p["reference_field_1"] = REF_FORMATS[kind](number) if kind == "T4" else POL.sub(REF_FORMATS[kind](number), p["reference_field_1"])
    elif kind == "T5":
        p["sender_name"] = reorder_name(p["sender_name"], upper=False)
    elif kind == "T6":
        p["sender_name"] = reorder_name(p["sender_name"], upper=True)
    elif kind == "T7":
        memo = f"pmt ${p['amount_usd']:,.2f}"
        p["reference_field_2"] = f"{p['reference_field_2']} {memo}".strip()
    return p


def main() -> None:
    src = json.loads((DATA / "mock_500.json").read_text())
    rng = random.Random(SEED)
    pool = sorted((c for c in src["cases"] if not c["checks"]["failures"] and not excluded(c) and c.get("variant", "clean") == "clean"),
                  key=lambda c: c["case_id"])

    has_policy_ref = [c for c in pool if POL.search(original_refs(c)[0])]
    person = [c for c in pool if c["archetype_id"] in PERSON_ARCHETYPES and len(c["payment"]["sender_name"].split()) >= 2]
    chosen: dict[str, list[dict]] = {}
    used: set[str] = set()

    def take(kind: str, candidates: list[dict]) -> None:
        candidates = [c for c in candidates if c["case_id"] not in used]
        rng.shuffle(candidates)
        picked = candidates[:SIZES[kind]]
        assert len(picked) == SIZES[kind], f"not enough eligible cases for {kind}: {len(picked)}"
        used.update(c["case_id"] for c in picked)
        chosen[kind] = picked

    for kind in ("T1", "T2", "T3", "T4"):
        take(kind, has_policy_ref)
    for kind in ("T5", "T6"):
        take(kind, person)
    take("T7", pool)

    cases = []
    for kind, picked in chosen.items():
        for c in picked:
            new = copy.deepcopy(c)
            o1, o2 = original_refs(c)
            new["case_id"] = f"{c['case_id']}~{kind}"
            new["variant"] = f"shift_{kind}"
            new["payment"] = transform_payment(c["payment"], kind)
            new["prior_payments"] = [transform_payment(p, kind) for p in c["prior_payments"]]
            new["noise_detail"] = {"before": {"reference_field_1": o1, "reference_field_2": o2},
                                   "shift": kind, "original_sender": c["payment"]["sender_name"],
                                   "original_reference_field_1": c["payment"]["reference_field_1"]}
            cases.append(new)

    out = {"meta": {"source": "mock_500.json", "seed": SEED, "sizes": SIZES,
                    "note": "labels unchanged; formats the rules were not built for (see build_shift.py)"},
           "world": src["world"], "cases": cases}
    (DATA / "shift_200.json").write_text(json.dumps(out))
    print(f"wrote shift_200.json: {len(cases)} cases")
    for kind, picked in chosen.items():
        c = next(x for x in cases if x["variant"] == f"shift_{kind}")
        print(f"  {kind}: {len(picked):>2} cases | e.g. sender {c['payment']['sender_name']!r} refs {c['payment']['reference_field_1']!r} | {c['payment']['reference_field_2']!r}"
              f"   (was {c['noise_detail']['original_sender']!r}, {c['noise_detail']['original_reference_field_1']!r})")


if __name__ == "__main__":
    main()
