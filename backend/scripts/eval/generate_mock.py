"""
Deterministic mock-data generator: a synthetic world + 5,000 labelled test payments.

No LLM is used. Every case is built from the same human-written ARCHETYPES table as generate.py
(expected scenario + recommendation come from the spec, never from a model), then verified with
generate.py's independent check_case(). Cases that fail their checks are regenerated.

Output is in the same format as data/full.json, so run_eval.py can run it directly:
  python scripts/eval/generate_mock.py                      # writes data/mock_5000.json, data/mock_500.json, CSVs
  python scripts/eval/run_eval.py --data scripts/eval/data/mock_500.json     # quick stratified run
  python scripts/eval/run_eval.py --data scripts/eval/data/mock_5000.json    # full run (hours; ~3 LLM calls per payment)

This is SYNTHETIC data. It is not the dataset CES provided and says nothing about real payment volumes.
The archetype mix below is chosen so ~87% of payments stay with the analyst and ~13% are escalations
(duplicates, unknown payers, extreme variance), roughly matching the shares observed in the CES dataset.
"""
import argparse
import csv
import difflib
import json
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import generate as g  # noqa: E402  (reuses ARCHETYPE, check_case, noise helpers, proto-derived enums)
import jellyfish  # noqa: E402  (same library the pipeline uses for name matching)

SEED = 42
N_CUSTOMERS = 360
BENEFICIARY = "CES Insurance"

# Archetype mix (sums to 5,000). Escalations: S3-tier5 + S4 escalates + S5 escalates ≈ 12.8%.
MIX = {
    "S1-apply-a": 1160, "S1-apply-b": 600, "S1-hold-name": 350, "S1-hold-risk": 150,
    "S2-apply-single": 450, "S2-apply-single-card": 200, "S2-apply-multi-unique": 250, "S2-hold-multi-ambiguous": 150,
    "S3-tier3-above": 300, "S3-tier3-below": 250, "S3-tier4": 150, "S3-tier5": 50,
    "S4-third-party-hold": 150, "S4-unknown-person": 150, "S4-unknown-company": 90, "S4-bad-policy-ref": 60,
    "S5-dup-exact": 150, "S5-dup-tolerance": 80, "S5-dup-balance": 60, "S5-diff-account-dup": 60,
    "S5-near-dup-control": 80, "S5-diff-ref-not-dup": 60,
}
assert sum(MIX.values()) == 5000

# Share of cases turned into messy variants (same labels, harder inputs)
NOISE = {"ref_noise": 0.25, "name_case": 0.08, "name_typo": 0.06}

NICKNAMES = {
    "Robert": "Bob", "William": "Bill", "Elizabeth": "Liz", "Katherine": "Kate", "Michael": "Mike", "Jennifer": "Jen",
    "Christopher": "Chris", "Alexander": "Alex", "Jonathan": "Jon", "Nicholas": "Nick", "Samantha": "Sam",
    "Margaret": "Maggie", "Daniel": "Dan", "Matthew": "Matt", "Rebecca": "Becky", "Benjamin": "Ben", "Anthony": "Tony",
    "Victoria": "Vicky", "Joseph": "Joe", "Patricia": "Patty", "Stephanie": "Steph", "Andrew": "Andy", "Thomas": "Tom",
}
POLICY_MEMOS = {"Auto": ["Auto Premium", "auto policy", "Car insurance"], "Home": ["Home Insurance", "home policy", "Homeowners"],
                "Life": ["Annual Life", "life premium", "Life policy"], "Health": ["Health Payment", "health premium", "Medical plan"]}
PLAIN_REFS = ["Insurance premium", "Insurance", "Premium payment", "ins pymt", "monthly premium", "payment"]
CO_A = ["Blue", "Summit", "Harbor", "Granite", "Maple", "Silver", "Northfield", "Crescent", "Evergreen", "Pioneer", "Redwood",
        "Lakeside", "Ironwood", "Sunrise", "Westgate", "Cobalt", "Juniper", "Beacon", "Falcon", "Orchard"]
CO_B = ["Ridge", "Point", "Valley", "Bay", "Creek", "Stone", "Peak", "Field", "Grove", "Crest"]
CO_C = ["Trading", "Logistics", "Supply", "Imports", "Builders", "Partners", "Marine", "Foods", "Textiles", "Analytics"]
TP_KIND = ["Payroll LLC", "Payroll Services", "Mortgage Escrow", "Family Trust", "Holdings Inc", "Properties LLC"]


def rules_name_score(a: str, b: str) -> float:
    """Mirror of app/services/signals/matching.py::_deterministic_score (the rule-based part, before any LLM)."""
    a, b = a.strip().lower(), b.strip().lower()
    if not a or not b:
        return 0.0
    jw = jellyfish.jaro_winkler_similarity(a, b) * 100
    lev = (1 - jellyfish.levenshtein_distance(a, b) / max(len(a), len(b))) * 100
    sdx = 10.0 if jellyfish.soundex(a) == jellyfish.soundex(b) else 0.0
    return min((jw * 0.5 + lev * 0.3 + sdx) / 0.9, 100.0)


def ratio(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()


# ── World ────────────────────────────────────────────────────────────────────

def make_world(rng: random.Random):
    firsts, lasts = FIRST_NAMES[:], LAST_NAMES[:]
    rng.shuffle(firsts)
    rng.shuffle(lasts)
    customer_firsts = firsts[:450] + list(NICKNAMES)            # guarantees some nickname-able customers
    reserved = {"firsts": firsts[450:], "lasts": lasts[500:]}  # disjoint pools for unknown payers
    names: list[str] = []
    li = 0
    while len(names) < N_CUSTOMERS:
        name = f"{rng.choice(customer_firsts)} {lasts[li]}"
        li += 1
        if all(ratio(name, n) < 0.75 for n in names):
            names.append(name)

    # Segments give every archetype enough eligible customers
    segments = (["risk"] * 24 + ["inactive"] * 10 + ["single"] * 120 + ["diff"] * 70 + ["ident"] * 45
                + ["balance"] * 30 + ["big"] * 30 + ["mixed"] * (N_CUSTOMERS - 329))
    rng.shuffle(segments)
    pol_seq = iter(range(10001, 99000, 7))
    customers = []
    for i, (name, seg) in enumerate(zip(names, segments)):
        acct = f"ACC-{50001 + i}"

        def policy(kind=None, premium=None, freq=None, balance=0.0, status="active"):
            kind = kind or rng.choice(["Auto", "Health", "Home", "Life"])
            if premium is None:
                if kind in ("Auto", "Health"):
                    premium, freq = float(rng.randrange(80, 451)), "monthly"
                elif kind == "Home":
                    premium, freq = float(rng.randrange(900, 2501)), rng.choice(["semi_annual", "annual"])
                else:
                    premium, freq = float(rng.randrange(300, 5001)), "annual"
            step = {"monthly": 30, "quarterly": 91, "semi_annual": 182, "annual": 365}[freq]
            start = rng.randrange(3, step)
            history = [{"days_ago": start + k * step, "amount_usd": premium,
                        "payment_method": rng.choice(["ACH", "ACH", "Credit Card", "Check"]),
                        "sender_account": acct, "status": "applied"} for k in range(6)]
            return {"policy_number": f"POL-{next(pol_seq):05d}", "policy_type": kind, "premium_usd": premium,
                    "premium_frequency": freq, "status": status, "outstanding_balance_usd": balance,
                    "next_due_in_days": rng.randrange(-5, 31), "history": history}

        flags, status = [], "active"
        if seg == "risk":
            flags = [rng.choice(["fraud_history", "chronic_late_payments"])]
            pols = [policy()]
        elif seg == "inactive":
            status, pols = "inactive", [policy(status="inactive")]
        elif seg == "single":
            pols = [policy()] + ([policy(status="closed")] if rng.random() < 0.2 else [])
        elif seg == "diff":
            a = policy(rng.choice(["Auto", "Health"]))
            b = policy(rng.choice(["Home", "Life"]))
            if max(a["premium_usd"], b["premium_usd"]) <= 1.3 * min(a["premium_usd"], b["premium_usd"]):
                b = policy("Home", premium=a["premium_usd"] * 3, freq="annual")
            pols = [a, b]
        elif seg == "ident":
            kind = rng.choice(["Auto", "Home"])
            a = policy(kind)
            pols = [a, policy(kind, premium=a["premium_usd"], freq=a["premium_frequency"])]
        elif seg == "balance":
            p = policy()
            p["outstanding_balance_usd"] = round(p["premium_usd"] * rng.choice([0.5, 1, 2]), 2)
            pols = [p]
        elif seg == "big":
            pols = [policy(rng.choice(["Home", "Life"]), premium=float(rng.randrange(600, 3001)), freq="annual")]
        else:
            pols = [policy() for _ in range(rng.choice([1, 2]))]
        customers.append({"customer_id": f"CUST-{5001 + i}", "name": name, "account_number": acct, "status": status,
                          "risk_flags": flags, "policies": pols})
    return {"customers": customers}, reserved


# ── Cases ────────────────────────────────────────────────────────────────────

class Builder:
    def __init__(self, world, reserved, rng):
        self.world, self.rng, self.reserved = world, rng, reserved
        self.names = [c["name"] for c in world["customers"]]
        self.by_id = {c["customer_id"]: c for c in world["customers"]}
        self.policy_numbers = {p["policy_number"] for c in world["customers"] for p in c["policies"]}
        act = lambda c: [p for p in c["policies"] if p["status"] == "active"]  # noqa: E731
        clean = [c for c in world["customers"] if c["status"] == "active" and not c["risk_flags"]]
        ident = lambda c: len(act(c)) >= 2 and len({p["premium_usd"] for p in act(c)}) < len(act(c))  # noqa: E731
        self.act = act
        self.pools = {
            "clean": [c for c in clean if act(c)],
            "risk": [c for c in world["customers"] if c["status"] == "active" and c["risk_flags"] and act(c)],
            "single": [c for c in clean if len(act(c)) == 1],
            "diff": [c for c in clean if len(act(c)) >= 2
                     and max(p["premium_usd"] for p in act(c)) > 1.3 * min(p["premium_usd"] for p in act(c))],
            "ident": [c for c in clean if ident(c) and all(p["outstanding_balance_usd"] == 0 for p in act(c))],
            "zero_bal": [c for c in clean if any(p["outstanding_balance_usd"] == 0 for p in act(c))],
            "pos_bal": [c for c in clean if any(p["outstanding_balance_usd"] > 0 for p in act(c))],
            "big": [c for c in clean if any(p["premium_usd"] >= 600 and p["outstanding_balance_usd"] == 0 for p in act(c))],
            "nick": [c for c in clean if act(c) and c["name"].split()[0] in NICKNAMES],
        }

    def pay(self, sender, amount, method="ACH", ref1="", ref2="", account="", hours=None):
        return {"sender_name": sender, "sender_account": account, "beneficiary_name": BENEFICIARY,
                "payment_method": method, "amount_usd": round(amount, 2),
                "hours_ago": hours if hours is not None else round(self.rng.uniform(0.5, 48), 1),
                "reference_field_1": ref1, "reference_field_2": ref2}

    def unknown_person(self):
        r = self.rng
        for _ in range(200):
            name = f"{r.choice(self.reserved['firsts'])} {r.choice(self.reserved['lasts'])}"
            if max(ratio(name, n) for n in self.names) < 0.6:
                return name
        raise RuntimeError("could not find a dissimilar name")

    def company(self):
        r = self.rng
        for _ in range(200):
            name = f"{r.choice(CO_A)} {r.choice(CO_B)} {r.choice(CO_C)}"
            words = set(name.lower().split())
            if not any(words & set(n.lower().split()) for n in self.names) and max(ratio(name, n) for n in self.names) < 0.6:
                return name
        raise RuntimeError("could not find a company name")

    def build(self, aid: str) -> dict:
        r, act = self.rng, self.act
        _, scenario, rec, _ = g.ARCHETYPE[aid]
        memo = lambda p: r.choice(POLICY_MEMOS[p["policy_type"]])  # noqa: E731
        near = lambda prem, pct=1.0: prem if r.random() < 0.7 else round(prem * (1 + r.uniform(-pct, pct) / 100), 2)  # noqa: E731
        cust, pol, prior = None, None, []

        if aid in ("S1-apply-a", "S1-apply-b", "S1-hold-name", "S1-hold-risk"):
            pool = {"S1-hold-risk": "risk", "S1-hold-name": "nick" if r.random() < 0.5 else "clean"}.get(aid, "clean")
            cust = r.choice(self.pools[pool])
            pol = r.choice(act(cust))
            first, last = cust["name"].split(" ", 1)
            if aid == "S1-apply-a":
                sender = f"{first} {r.choice('ABCDEFGHJKLMNPRSTW')}. {last}"
            elif aid == "S1-hold-name":
                if first in NICKNAMES and r.random() < 0.8:
                    sender = f"{NICKNAMES[first]} {last}"
                else:
                    if len(last) >= 5:
                        i = r.randrange(1, len(last) - 2)
                        variant = last[:i] + last[i + 1] + last[i] + last[i + 2:]  # transposed surname letters
                    else:
                        variant = last[:2] + last[1:]  # doubled letter in a short surname
                    sender = f"{first} {variant}"
            else:
                sender = cust["name"]
            amount = pol["premium_usd"] if aid == "S1-hold-risk" else near(pol["premium_usd"])
            payment = self.pay(sender, amount, "Credit Card" if aid == "S1-apply-b" else "ACH", pol["policy_number"], memo(pol),
                               cust["account_number"] if r.random() < 0.8 else "")

        elif aid.startswith("S2"):
            key = {"S2-apply-single": "single", "S2-apply-single-card": "single",
                   "S2-apply-multi-unique": "diff", "S2-hold-multi-ambiguous": "ident"}[aid]
            cust = r.choice(self.pools[key])
            pol = r.choice(act(cust))
            ref1 = "" if aid == "S2-apply-single-card" else r.choice(PLAIN_REFS)
            method = "Credit Card" if aid == "S2-apply-single-card" else "ACH"
            amount = pol["premium_usd"] if key in ("diff", "ident") else near(pol["premium_usd"])
            payment = self.pay(cust["name"], amount, method, ref1, r.choice(["", "thanks", "premium"]),
                               cust["account_number"] if r.random() < 0.7 else "")
            if key == "ident":
                pol = None  # ambiguous by design: no single target policy

        elif aid.startswith("S3"):
            cust = r.choice(self.pools["clean"])
            pol = r.choice(act(cust))
            factor = {"S3-tier3-above": (1.21, 1.39), "S3-tier3-below": (0.61, 0.79),
                      "S3-tier4": (1.61, 1.84), "S3-tier5": (2.61, 2.84)}[aid]
            amount = round(pol["premium_usd"] * r.uniform(*factor), 2)
            payment = self.pay(cust["name"], amount, "Wire" if aid == "S3-tier3-below" else "ACH", pol["policy_number"], memo(pol),
                               cust["account_number"])

        elif aid == "S4-third-party-hold":
            cust = r.choice(self.pools["clean"])
            pol = r.choice(act(cust))
            last = cust["name"].split()[-1]
            kind = r.choice(TP_KIND)
            sender = f"{last} {kind}" if "Trust" in kind else f"{r.choice(CO_A)} {r.choice(CO_B)} {kind}"
            payment = self.pay(sender, round(pol["premium_usd"] * r.uniform(0.95, 1.05), 2), r.choice(["ACH", "Wire"]),
                               pol["policy_number"], f"{cust['name']} premium", f"ACC-{r.randrange(70000, 79999)}")
            cust_id, pol_no = "", pol["policy_number"]
            return self.case(aid, scenario, rec, "", pol_no, payment, [])

        elif aid in ("S4-unknown-person", "S4-unknown-company", "S4-bad-policy-ref"):
            sender = self.company() if aid == "S4-unknown-company" else self.unknown_person()
            method = r.choice(["Wire", "Check"]) if aid == "S4-unknown-company" else r.choice(g.METHODS)
            if aid == "S4-bad-policy-ref":
                while True:
                    fake = f"POL-{r.randrange(99001, 99999):05d}"
                    if fake not in self.policy_numbers:
                        break
                ref1 = fake
            else:
                ref1 = r.choice(["", "Insurance", "invoice 2231", "payment"])
            payment = self.pay(sender, float(r.randrange(80, 2600)), method, ref1, "",
                               f"ACC-{r.randrange(80000, 89999)}" if r.random() < 0.6 else "")
            return self.case(aid, scenario, rec, "", "", payment, [])

        else:  # S5 family
            if aid == "S5-diff-ref-not-dup":
                cust = r.choice(self.pools["ident"])
                a, pol = act(cust)[:2]
                gap = r.uniform(20, 60)
                payment = self.pay(cust["name"], pol["premium_usd"], "ACH", pol["policy_number"], memo(pol), cust["account_number"])
                prior = [dict(payment, reference_field_1=a["policy_number"], reference_field_2=memo(a),
                              hours_ago=round(payment["hours_ago"] + gap, 1))]
                return self.case(aid, scenario, rec, cust["customer_id"], pol["policy_number"], payment, prior)
            pool = {"S5-dup-balance": "pos_bal", "S5-near-dup-control": "big"}.get(aid, "zero_bal")
            cust = r.choice(self.pools[pool])
            want_pos = aid == "S5-dup-balance"
            cands = [p for p in act(cust) if (p["outstanding_balance_usd"] > 0) == want_pos
                     and (aid != "S5-near-dup-control" or p["premium_usd"] >= 600)]
            pol = r.choice(cands)
            prem = pol["premium_usd"]
            prior_amt = prem
            amount = {"S5-dup-tolerance": prem + r.choice([1.0, -1.0]), "S5-near-dup-control": prem + 10.0}.get(aid, prem)
            gap = r.uniform(20, 60)
            payment = self.pay(cust["name"], amount, "ACH", pol["policy_number"], memo(pol), cust["account_number"])
            prior_acct = f"CARD-{r.randrange(1000, 9999)}" if aid == "S5-diff-account-dup" else cust["account_number"]
            prior = [dict(payment, amount_usd=prior_amt, sender_account=prior_acct, hours_ago=round(payment["hours_ago"] + gap, 1))]

        return self.case(aid, scenario, rec, cust["customer_id"] if cust else "", pol["policy_number"] if pol else "", payment, prior)

    @staticmethod
    def case(aid, scenario, rec, cust_id, pol_no, payment, prior):
        return {"archetype_id": aid, "target_customer_id": cust_id, "target_policy_number": pol_no, "payment": payment,
                "prior_payments": prior, "rationale": f"Deterministic mock case for archetype {aid}.",
                "expected_scenario": scenario, "expected_recommendation": rec, "variant": "clean"}


def add_noise(case: dict, exact_names: set, rng: random.Random) -> dict:
    """Turn a clean case into a messy variant in place, mirroring generate.py's twin rules."""
    aid, scenario = case["archetype_id"], case["expected_scenario"]
    options = []
    if case["payment"]["reference_field_1"].strip() and g.POLICY_RE.search(case["payment"]["reference_field_1"]):
        options.append("ref_noise")
    if scenario != 4 and case["payment"]["sender_name"].lower() in exact_names:
        options.append("name_case")
        if aid in g.TYPO_ARCHETYPES:
            options.append("name_typo")
    roll = rng.random()
    tag, acc = None, 0.0
    for t in ("ref_noise", "name_case", "name_typo"):
        acc += NOISE[t]
        if roll < acc:
            tag = t
            break
    if tag not in options:
        return case
    before = {k: case["payment"][k] for k in ("sender_name", "reference_field_1", "reference_field_2")}
    if tag == "ref_noise":
        cache, ref2_case = {}, rng.choice([str.upper, str.lower, str])
        for p in [case["payment"], *case["prior_payments"]]:
            if p["reference_field_1"] not in cache:
                cache[p["reference_field_1"]] = g.noisy_ref(p["reference_field_1"], rng)
            p["reference_field_1"] = cache[p["reference_field_1"]]
            p["reference_field_2"] = ref2_case(p["reference_field_2"])
        token = g.POLICY_RE.search(before["reference_field_1"])
        if token and token.group(0)[4:] not in case["payment"]["reference_field_1"]:
            return None
    else:
        new = g.noisy_case(before["sender_name"], rng) if tag == "name_case" else g.typo(before["sender_name"], rng)
        if new == before["sender_name"]:
            return None
        for p in [case["payment"], *case["prior_payments"]]:
            p["sender_name"] = new
        if tag == "name_typo":
            case["accept"] = ["apply", "hold"]
    case["variant"] = tag
    case["noise_detail"] = {"before": before, "after": {k: case["payment"][k] for k in before}}
    return case


def main(out_dir: Path, seed: int) -> None:
    rng = random.Random(seed)
    world, reserved = make_world(rng)
    world_model = g.World(**world)
    builder = Builder(world, reserved, rng)
    exact_names = {c["name"].lower() for c in world["customers"]}

    cases, rejected, n = [], Counter(), 0
    for aid, count in MIX.items():
        made = 0
        while made < count:
            case = builder.build(aid)
            base_id = f"{aid}-{made + 1:04d}"
            case["case_id"] = base_id
            # Independent checks run on the clean case; noise is applied afterwards (as generate.py does for twins),
            # because messy references / names are exactly what the checks' exact-format rules would reject.
            fails, warns = g.check_case(g.GenCase(**{k: case[k] for k in g.GenCase.model_fields}), world_model)
            n += 1
            if not fails and aid.startswith("S1"):
                # S1 labels depend on the name-similarity band, so pin each case to the band its label assumes
                score = rules_name_score(case["payment"]["sender_name"], builder.by_id[case["target_customer_id"]]["name"])
                case["name_score_rules"] = round(score, 1)
                if aid == "S1-hold-name" and not 75 <= score <= 90:
                    fails = [f"rule-based name score {score:.0f} outside 75-90"]
                elif aid in ("S1-apply-b", "S1-hold-risk") and score <= 90:
                    fails = [f"rule-based name score {score:.0f} not above 90"]
            if fails:
                rejected[f"{aid}: {fails[0]}"] += 1
                continue
            noisy = add_noise(json.loads(json.dumps(case)), exact_names, rng)
            if noisy is not None and noisy["variant"] != "clean":
                noisy["base_case"] = base_id
                noisy["case_id"] = f"{base_id}~{noisy['variant']}"
                case = noisy
                if aid.startswith("S1"):  # score what the pipeline will actually see
                    case["name_score_rules"] = round(rules_name_score(
                        case["payment"]["sender_name"], builder.by_id[case["target_customer_id"]]["name"]), 1)
            case["checks"] = {"failures": [], "warnings": warns}
            cases.append(case)
            made += 1

    rng.shuffle(cases)
    esc = sum(1 for c in cases if c["expected_recommendation"] == "escalate")
    needing_llm = sum(1 for c in cases if c["archetype_id"] == "S1-apply-a" and c.get("name_score_rules", 100) <= 90)
    meta = {
        "generator": "generate_mock.py (deterministic, no LLM)", "seed": seed, "synthetic": True,
        "note": "Synthetic test data. Not the CES dataset. S1 cases carry name_score_rules (the rule-based similarity before any LLM). "
                "S1-hold-name cases are pinned to a 75-90 rule score; the live LLM gray-zone step (70-92) can still raise some to Apply. "
                "S1-apply-a cases with a rule score of 90 or below only reach Apply through the LLM step, so they separate the "
                "rules-only and live-LLM arms of an ablation.",
        "s1_apply_a_needing_llm": needing_llm,
        "world_customers": len(world["customers"]),
        "world_policies": sum(len(c["policies"]) for c in world["customers"]),
        "cases": len(cases), "attempted": n, "rejected_by_checks": dict(rejected),
        "by_archetype": dict(Counter(c["archetype_id"] for c in cases)),
        "by_expected_scenario": dict(Counter(c["expected_scenario"] for c in cases)),
        "by_expected_recommendation": dict(Counter(c["expected_recommendation"] for c in cases)),
        "by_variant": dict(Counter(c["variant"] for c in cases)),
        "escalation_share": round(esc / len(cases), 3),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "mock_5000.json").write_text(json.dumps({"meta": meta, "world": world, "cases": cases}, indent=1))

    # Stratified 10% sample for quick runs
    by_arch: dict[str, list] = {}
    for c in cases:
        by_arch.setdefault(c["archetype_id"], []).append(c)
    sample = [c for aid, group in by_arch.items() for c in group[: max(3, round(len(group) * 0.1))]]
    (out_dir / "mock_500.json").write_text(json.dumps(
        {"meta": dict(meta, cases=len(sample), note=meta["note"] + " Stratified ~10% sample of mock_5000.json.",
                      by_archetype=dict(Counter(c["archetype_id"] for c in sample))),
         "world": world, "cases": sample}, indent=1))

    # Flat CSVs for spreadsheets / other tools
    with open(out_dir / "mock_5000_payments.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["case_id", "archetype_id", "variant", "expected_scenario", "expected_recommendation", "accept",
                    "target_customer_id", "target_policy_number", "sender_name", "sender_account", "beneficiary_name",
                    "payment_method", "amount_usd", "hours_ago", "reference_field_1", "reference_field_2",
                    "prior_sender_account", "prior_amount_usd", "prior_hours_ago", "prior_reference_field_1"])
        for c in cases:
            p, pr = c["payment"], (c["prior_payments"] or [{}])[0]
            w.writerow([c["case_id"], c["archetype_id"], c["variant"], c["expected_scenario"], c["expected_recommendation"],
                        "|".join(c.get("accept") or [c["expected_recommendation"]]), c["target_customer_id"],
                        c["target_policy_number"], p["sender_name"], p["sender_account"], p["beneficiary_name"],
                        p["payment_method"], p["amount_usd"], p["hours_ago"], p["reference_field_1"], p["reference_field_2"],
                        pr.get("sender_account", ""), pr.get("amount_usd", ""), pr.get("hours_ago", ""), pr.get("reference_field_1", "")])
    with open(out_dir / "mock_world_policies.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["customer_id", "name", "account_number", "customer_status", "risk_flags", "policy_number", "policy_type",
                    "premium_usd", "premium_frequency", "policy_status", "outstanding_balance_usd", "next_due_in_days"])
        for c in world["customers"]:
            for p in c["policies"]:
                w.writerow([c["customer_id"], c["name"], c["account_number"], c["status"], "|".join(c["risk_flags"]),
                            p["policy_number"], p["policy_type"], p["premium_usd"], p["premium_frequency"], p["status"],
                            p["outstanding_balance_usd"], p["next_due_in_days"]])
    print(json.dumps(meta, indent=2))


# ── Name pools (ASCII, generated once from Faker across 18 locales; embedded so no extra dependency) ──
FIRST_NAMES = ["Aarini", "Aarush", "Abeer", "Abril", "Achille", "Adina", "Aditya", "Adoracion", "Ahsen", "Akcabay", "Akshay", "Alaeddin", "Alderano", "Aldonza", "Alemsah", "Alessandra", "Alex", "Alexa", "Alexandre", "Alexia", "Alfonso", "Alix", "Almast", "Almudena", "Alpcan", "Alpsu", "Alvar", "Amadeo", "Amado", "Amaro", "Amber", "Amin", "Amleto", "Amy", "Anais", "Anamika", "Anastasie", "Anastazja", "Anatolij", "Anders", "Andre", "Andreas", "Anna", "Annaliese", "Annamaria", "Anneli", "Annetta", "Annica", "Anouk", "Antonello", "Antonietta", "Antonino", "Anya", "Aria", "Ariadna", "Ariane", "Ariel", "Arif", "Aristides", "Armida", "Armin", "Arnaldo", "Arnd", "Ase", "Ashley", "Astrid", "Asuncion", "Atalay", "Augusto", "Aurelia", "Aureliano", "Autumn", "Aya", "Ayden", "Aykutalp", "Aynimah", "Ayoub", "Aytoz", "Azra", "Bakhshi", "Balhaar", "Balvan", "Bartek", "Batirhan", "Baykan", "Beatriz", "Behrem", "Bella", "Benjamin", "Bernarda", "Bettina", "Beyler", "Beyzade", "Bhavani", "Bhavya", "Bilender", "Bilgen", "Bill", "Birgit", "Blanca", "Blas", "Boris", "Bradley", "Brandi", "Brayan", "Brigitte", "Brittany", "Bror", "Bryan", "Bunyamun", "Burkhard", "Calebe", "Calim", "Calisto", "Camilla", "Candace", "Candelas", "Capkan", "Carl", "Carlito", "Carmela", "Carol", "Carolyn", "Casey", "Celikyurek", "Cesar", "Chaitaly", "Charlene", "Charvi", "Cheryl", "Chiara", "Chris", "Christer", "Christian", "Christiane", "Christina", "Christophe", "Cindy", "Cipriano", "Cirino", "Ciro", "Clara", "Clare", "Claudius", "Clemente", "Clinton", "Collin", "Concepcion", "Concetta", "Conny", "Constanze", "Consuelo", "Cora", "Corrado", "Cristal", "Cristian", "Cristina", "Cristobal", "Crystal", "Daan", "Dalia", "Daphne", "Darsh", "Dave", "Deger", "Demetrio", "Denise", "Dev", "Devika", "Diana", "Diane", "Diedrich", "Diethelm", "Dogan", "Dolun", "Dom", "Dominik", "Donatello", "Dorothe", "Dragan", "Dylano", "Eckhardt", "Edward", "Efil", "Ekber", "Elaine", "Eleonore", "Elgin", "Eli", "Ellen", "Ellie", "Eloa", "Elodia", "Elwira", "Emal", "Emelina", "Emil", "Emiliano", "Erdemer", "Erdogan", "Erhard", "Erick", "Erika", "Eris", "Ermes", "Ernesto", "Erogul", "Espartaco", "Ester", "Esther", "Eta", "Etelvina", "Evi", "Evita", "Fabian", "Fabricio", "Faith", "Falan", "Farhan", "Fayize", "Feliciana", "Fenna", "Fildan", "Fiorenzo", "Floortje", "Frederique", "Frida", "Friedbert", "Fryderyk", "Fulgencio", "Gabel", "Gabrielle", "Gaja", "Galo", "Gaston", "Gaurang", "Gaurav", "Gautam", "Georgia", "Georgina", "Gerda", "Gerold", "Gervasio", "Gianmarco", "Gianpaolo", "Gillian", "Gionata", "Giovanni", "Girolamo", "Giuliano", "Gok", "Goncafer", "Gopal", "Gordon", "Gosta", "Goyo", "Grace", "Gregoire", "Gretl", "Guiseppe", "Gulbani", "Gulel", "Gulper", "Gunar", "Gunebakan", "Gunnar", "Gunvor", "Gustavo", "Gzy", "Hadassa", "Hafiza", "Hamiyet", "Hanedan", "Harry", "Hartwig", "Hassan", "HbWb", "Hedwig", "Hellena", "Heloisa", "Hemang", "Henning", "Henric", "Henriette", "Henrik", "Henrique", "Henry", "Heraclio", "Hifzullah", "Hilary", "Hilda", "Hilma", "Hiral", "Hmyd", "Holly", "Honore", "Howard", "HqWy", "Hrth", "Hubert", "Humberto", "Hzm", "Ignacy", "Igor", "Ildem", "Imam", "Imaran", "Imke", "Imrihan", "Inaya", "Ingrid", "Irena", "Irfan", "Isaac", "Isabel", "Isabella", "Ishwar", "Ismet", "Ivonne", "Jacinto", "Jacqueline", "Jacques", "Jan", "Janice", "Janne", "Januja", "Jean", "Jeannine", "Jeffery", "Jemma", "Jenna", "Jenny", "Jesse", "Jill", "Jillian", "Jodi", "Jolie", "Jolijn", "Josefine", "Josephine", "Joshua", "Joyce", "Jozef", "Juan", "Juanita", "Judith", "Juliana", "Julianna", "Julius", "Juliusz", "Jyoti", "Kalina", "Kalle", "Kalpit", "Kamil", "Kamila", "Kandef", "Karaca", "Karan", "Karin", "Karla", "Karol", "Kasim", "Katherina", "Kayla", "Kayrabay", "Kendra", "Kerstin", "Kevin", "Kifaye", "Kiki", "Klas", "Klaudia", "Kocak", "Konstanty", "Kosemen", "Kriemhild", "Kristen", "Kristian", "Kristina", "Krystian", "Krystyna", "Kyano", "Ladli", "Lando", "Lars", "Lauretta", "Leah", "Lee", "Leela", "Leif", "Lena", "Leo", "Leonardo", "Leoncio", "Leonel", "Liam", "Lilia", "Lily", "Lindsey", "Ling", "Linn", "Liwia", "Lize", "Lodovico", "Lorena", "Lorenzo", "Luana", "Lucia", "Luciano", "Lucie", "Ludovico", "Luigina", "Luka", "Luke", "Luz", "Lydia", "Maaike", "Maartje", "Madhav", "Madhavi", "Madlen", "Magda", "Magdalena", "Magnus", "Mahir", "Mahmut", "Maksude", "Malin", "Marcela", "Marcio", "Marek", "Margarita", "Margaud", "Marguerite", "Mariane", "Marianne", "Marie", "Marika", "Marilyn", "Mariusz", "Martha", "Martyn", "Maryse", "Maside", "Mathilde", "Matthias", "Maureen", "Maurilio", "Maxim", "Meera", "Mekhala", "Melchor", "Melina", "Melissa", "Merel", "Mevludiye", "Michail", "Mihrab", "Mila", "Milena", "Miranda", "Mirthe", "Modesto", "Monica", "Morena", "Mugdha", "Muvaffak", "Nachiket", "Nacho", "Nakul", "Naomi", "Natalio", "Natan", "Nathaniel", "Necilal", "Neha", "Nelly", "Netra", "Nezengul", "Nicolai", "Nicolas", "Nicoletta", "Nieves", "Niko", "Nikodem", "Nilima", "Noud", "Nurbanu", "Nurmelek", "Nurtac", "Nynke", "Octavio", "Olga", "Oncel", "Orlando", "Oscar", "Otavio", "Ottavio", "Otto", "Ozlu", "Ozudogru", "Patrick", "Patrik", "Patryk", "Pekkan", "Pepe", "Per", "Petter", "Philip", "Pierangelo", "Pierre", "Pilar", "Piotr", "Pippa", "Piran", "Porfirio", "Preston", "Priscila", "Priscilla", "Priska", "Puccio", "Purcek", "Rachit", "Radoslaw", "Rael", "Rafael", "Rahel", "Rahiye", "Raksha", "Ramiro", "Ramon", "Ranbir", "Randall", "Ranveer", "Raphael", "Raul", "Raven", "Reginald", "Remy", "Ren", "Renato", "Rene", "Rens", "Reyes", "Reynaldo", "Reza", "Rico", "Robert", "Rocco", "Rocio", "Rohan", "Rolf", "Ronald", "Ronaldo", "Rosa", "Rosaura", "Rosie", "Roxana", "Rozalia", "Ruby", "Ruggiero", "Ruhugul", "SHb", "Sachi", "Safinaz", "Saga", "Sai", "Salome", "Salvador", "Salvi", "Samarth", "Samuel", "Sarina", "Scott", "Sean", "Sebastian", "Sebastien", "Secme", "Selaheddin", "Sem", "Seniha", "Serena", "Sergio", "Severiano", "Severo", "Seyfullah", "Shaurya", "Shirley", "Siegbert", "Silja", "Silvano", "Simonetta", "Siya", "Songurkan", "Sonja", "Sosimo", "Soykut", "Stanley", "Stella", "Stellan", "Stijn", "Sudiksha", "Summer", "Susana", "Susi", "Svea", "Sven", "Swen", "Syl", "Sylvia", "Sylvio", "Tage", "Tamanna", "Tangul", "Tanish", "Tasar", "Taylak", "Tejas", "Teksoy", "Teodora", "Teresa", "Thibaut", "Thierry", "Tijmen", "Tijn", "Tilde", "Tilly", "Timoteo", "Tiziana", "Tonia", "Trinidad", "TyWb", "Tygo", "Ubaldo", "Udarsh", "Ulf", "Ulkum", "Ulrike", "Ulu", "Umberto", "Umutcan", "Unlen", "Uriel", "Ursula", "Utkucan", "Uygun", "Vaishnavi", "Valentim", "Valentina", "Valentine", "Valerio", "Varenya", "Vedika", "Vefia", "Venancio", "Veronique", "Victoire", "Vide", "Viktoria", "Vince", "Vincenzo", "Viraj", "Virgilio", "Virginia", "Virginie", "Vito", "Vittorio", "Volker", "Vritti", "Walentina", "Walther", "Warda", "Warjas", "Watika", "Wazir", "Wenzel", "Wiktor", "Wolf", "Wolfgang", "Xavier", "Xenia", "Xue", "Yago", "Yahvi", "Yalin", "Yamini", "Yan", "Yanki", "Yara", "Yetisal", "Yfke", "Yilmaz", "Yngve", "Yolanda", "Zaid", "Zaitra", "Zekayi", "Zhi", "Zilmil"]
LAST_NAMES = ["Aalts", "Ackermann", "Acuna", "Adams", "Agostinelli", "Ahmed", "Akar", "Alberdi", "Alboni", "Alcaraz", "Alegre", "Alfaro", "Ali", "Allison", "Almeida", "Almgren", "Alvarez", "Alvaro", "Amat", "Amato", "Anaya", "Andersen", "Andres", "Angeli", "Anguissola", "Anne", "Antelami", "Antonucci", "Aranda", "Archuleta", "Arcos", "Arellano", "Argento", "Argurio", "Arias", "Armas", "Armenta", "Arnau", "Arora", "Arregui", "Arvidsson", "Aschman", "Aslan", "Astrom", "Atzler", "Augustsson", "Austermuhle", "Ayala", "Azorin", "Babu", "Badal", "Bahr", "Bailly", "Bajak", "Bakiera", "Bal", "Balderas", "Bancerz", "Barber", "Barej", "Barents", "Baresi", "Barnes", "Barragan", "Barreda", "Barrera", "Barrett", "Barros", "Bartkowicz", "Basadonna", "Bastek", "Bastiaense", "Bates", "Batog", "Batta", "Baudry", "Baum", "Beckmann", "Bedi", "Beekman", "Beernink", "Bejarano", "Bellini", "Beltran", "Benavente", "Benitez", "Benson", "Berg", "Bergstrand", "Bergstrom", "Beska", "Bhardwaj", "Bianchi", "Biggen", "Bilgin", "Biswas", "Bixio", "Bjork", "Bjorklund", "Bjorkman", "Black", "Blanc", "Blanchard", "Blanco", "Blankenship", "Blazquez", "Blot", "Bogus", "Boiardo", "Bokenkamp", "Bolkesteijn", "Bolzmann", "Bonatti", "Bonino", "Bonomo", "Borde", "Borgia", "Borja", "Borrego", "Borromini", "Bossi", "Bostrom", "Botella", "Botello", "Boucher", "Boulay", "Bouvet", "Brito", "Brizee", "Broman", "Brouwer", "Browarczyk", "Brown", "Browne", "Bruce", "Brugnaro", "Brumleve", "Buchholz", "Buendia", "Bullock", "Bulzoni", "Burns", "Burton", "Bustos", "Butala", "Cabello", "Cabo", "Calgari", "Callegari", "Callegaro", "Camino", "Campoy", "Canales", "Canali", "Cardona", "Carlos", "Carpentier", "Carre", "Carreras", "Carrero", "Carsten", "Carter", "Casalodi", "Castro", "Cavalcanti", "Cavazos", "Ceballos", "Ceci", "Cervantes", "Ceynowa", "Chad", "Chakraborty", "Chaudhari", "Chaudhary", "Chaudry", "Chauveau", "Chauvet", "Chevresson", "Chico", "Chokshi", "Chopra", "Choros", "Chuchla", "Ciarka", "Ciezka", "Cifuentes", "Cimarosa", "Cimini", "Cirino", "Clark", "Clayton", "Cochran", "Coll", "Collin", "Colon", "Comboni", "Conrad", "Cornelissen", "Cortes", "Cossiga", "Cotto", "Courtier", "Couturier", "Cuda", "Cuesta", "Cunha", "Dachgelt", "Dacko", "Dada", "Dahlgren", "Dang", "Dar", "Dash", "Davies", "Dayal", "Delahaye", "Deledda", "Demirel", "Denis", "Dennenberg", "Dennis", "Deo", "Descamps", "Deshmukh", "Deshpande", "Dhar", "Dietz", "Dirksen", "Ditschlerin", "Dixit", "Dobson", "Dohn", "Dominguez", "Doorhof", "Dorr", "Dossetti", "Doyle", "Drewes", "Drozd", "Duarte", "Duffy", "Dumas", "Duncan", "Dunn", "Dupuy", "Duran", "Durmus", "Dutta", "Dzwonnik", "Echeverria", "Eckhardt", "Edin", "Eigenwillig", "Eijkelboom", "Ellis", "Emmen", "Emo", "Engman", "Engstrom", "Ericsson", "Eriksson", "Escalante", "Escamilla", "Escriva", "Escudero", "Esquivel", "Estes", "Estevez", "Evans", "Exposito", "Fabra", "Faggiani", "Fajardo", "Fal", "Falco", "Fantozzi", "Fattori", "Faugno", "Faust", "Fedyk", "Ferguson", "Fermi", "Ferran", "Ferrara", "Ferrero", "Ficino", "Fidler", "Fierro", "Figueras", "Figueroa", "Filek", "Filzi", "Finzi", "Firat", "Fischer", "Flaiano", "Flink", "Fogaca", "Font", "Ford", "Francois", "Franke", "Franzese", "Fremie", "Friberg", "Gaggini", "Gaillard", "Gaitan", "Gala", "Galek", "Gallagher", "Gallego", "Gallegos", "Gandhi", "Garay", "Gargallo", "Garrido", "Gentili", "Gera", "Gertz", "Getka", "Ghose", "Gibson", "Gil", "Gilbert", "Gimenez", "Ginesio", "Goel", "Goicoechea", "Golgi", "Gordillo", "Goyal", "Graj", "Grebowiec", "Grossi", "Grottner", "Gryka", "Grzelczyk", "Grzenia", "Guclu", "Guerrero", "Guevara", "Guillon", "Gute", "Gwizdek", "Hagendoorn", "Hakansson", "Halka", "Hall", "Handke", "Hansson", "Hapka", "Hardy", "Haro", "Harris", "Hart", "Hartmann", "Harvey", "Hawkins", "Hayre", "Hayward", "Heath", "Hedman", "Hedstrom", "Heintze", "Hekker", "Hellgren", "Helmerhorst", "Henriksson", "Heras", "Herrera", "Herrero", "Hervas", "Hess", "Hethur", "Hidalgo", "Higueras", "Hiller", "Hoarau", "Hoedemakers", "Holgersson", "Holland", "Holmes", "Holthuis", "Honing", "Hoz", "Huberts", "Huijs", "Huurdeman", "Iglesia", "Iglesias", "Ingvarsson", "Iyer", "Jarvis", "Jasina", "Jaskowiec", "Jedra", "Jenkins", "Jesus", "Jewula", "Jiminez", "Johansson", "Johnsson", "Joly", "Jonasson", "Jonczyk", "Jones", "Jop", "Jopich", "Jordan", "Joshi", "Juan", "Julien", "Jungfer", "Junken", "Kade", "Kambs", "Kamdar", "Kant", "Kari", "Karz", "Keller", "Kielbik", "Kinal", "Klapp", "Klein", "Klemt", "Kling", "Klinger", "Kobza", "Koczy", "Kojder", "Kolarczyk", "Konda", "Koniecko", "Koning", "Korek", "Koret", "Korgul", "Koruturk", "Koska", "Koster", "Kramer", "Krebs", "Krein", "Kremer", "Kristiansson", "Kroker", "Krueger", "Kruschwitz", "Kryk", "Krywult", "Ksel", "Kuhnert", "Kurian", "Kurpanik", "Kutek", "Lachmann", "Lad", "Lagerweij", "Lala", "Laporte", "Larrea", "Leach", "Lecomte", "Ledoux", "Lee", "Lees", "Leiva", "Lemaire", "Lemoine", "Lensen", "Leonard", "Leone", "Lepianka", "Leszcz", "Lettiere", "Levin", "Lewis", "Lindau", "Lindberg", "Lindqvist", "Lindstrom", "Linschoten", "Lira", "Little", "Ljunggren", "Llopis", "Lloyd", "Lollobrigida", "Lombard", "Lovato", "Lucas", "Lundkvist", "Lundqvist", "Lundstrom", "Luque", "Lussu", "Luthra", "Lutterveld", "Luz", "Lynn", "Mace", "Machniak", "Magar", "Magnusson", "Mahajan", "Mahal", "Maharaj", "Maillot", "Majczyna", "Majewski", "Maksym", "Mallien", "Malm", "Mandal", "Mandrysz", "Mangold", "Mannoia", "Manunta", "Marceron", "Marion", "Mariscal", "Markiel", "Marrero", "Marsh", "Marshall", "Martens", "Martensson", "Mastroianni", "Mateo", "Mateu", "Mathol", "Matos", "Matthai", "Matus", "Mazzacurati", "Mccall", "Mckinney", "Mecik", "Meeusen", "Mejia", "Mende", "Mendes", "Mercantini", "Merchant", "Merda", "Merle", "Merritt", "Metz", "Michielsen", "Miller", "Mistry", "Mizgala", "Montalvo", "Montenegro", "Montero", "Montes", "Mora", "Moraes", "Morales", "Mordak", "Morera", "Morosini", "Morris", "Morucci", "Mosur", "Muhle", "Mulder", "Mulet", "Munoz", "Murcia", "Murillo", "Murthy", "Murty", "Mustafa", "Nagi", "Nagorka", "Naidu", "Naik", "Narasimhan", "Narvaez", "Natarajan", "Naumiuk", "Navarrete", "Nayar", "Neureuther", "Neuschafer", "Neuteboom", "Niewiara", "Nigam", "Nogueira", "Nogues", "Nojman", "Nolan", "Noordijk", "Norberg", "Nordio", "Norris", "Nugnes", "Ochal", "Oleskiewicz", "Oliva", "Olivas", "Oliveira", "Olivera", "Ollivier", "Olofsson", "Olsson", "Omar", "Onisto", "Oquendo", "Ornelas", "Orta", "Ortiz", "Owens", "Pablo", "Pachla", "Pacura", "Padovano", "Paillet", "Palla", "Palomares", "Palomino", "Palsson", "Pant", "Paredes", "Parmar", "Parsa", "Parsons", "Passalacqua", "Pastor", "Patalas", "Patel", "Patla", "Pau", "Pawlonka", "Payet", "Payne", "Pazera", "Pearce", "Pedraza", "Pedro", "Pelayo", "Pelletier", "Perales", "Perez", "Pergolesi", "Peri", "Peronne", "Persijn", "Persson", "Petrocelli", "Pham", "Piekara", "Pieper", "Pieszak", "Pinamonte", "Pineiro", "Pires", "Pisacane", "Pizarro", "Pla", "Plebanek", "Podsiedlik", "Polasik", "Politz", "Polo", "Porta", "Porto", "Pottier", "Powell", "Praga", "Prat", "Pratesi", "Proc", "Pruchnik", "Pruitt", "Puerta", "Puga", "Quasimodo", "Quintanilla", "Rael", "Ragus", "Ram", "Ramakrishnan", "Raman", "Ramaswamy", "Ramis", "Rasala", "Ratti", "Raya", "Razo", "Redondo", "Reese", "Reimes", "Reising", "Rendon", "Renner", "Renteria", "Reyes", "Reyna", "Reynaud", "Riba", "Richards", "Rico", "Ridder", "Rienzo", "Riera", "Rijcken", "Rios", "Riou", "Robbins", "Robles", "Roda", "Rodgers", "Rodriguez", "Rogal", "Rogula", "Rohleder", "Rolon", "Romero", "Romo", "Rose", "Roskoth", "Rossetti", "Roszkiewicz", "Roy", "Rychel", "Sabbatini", "Safak", "Sager", "Sahni", "Salcedo", "Salinas", "Salvi", "Samele", "Sanchez", "Sandberg", "Sandhu", "Sandin", "Santana", "Sarabia", "Sastry", "Sauer", "Saunders", "Savant", "Schenkel", "Schmiedecke", "Schwartsbach", "Schwital", "Segni", "Sehgal", "Sem", "Serrato", "Shah", "Sharpe", "Short", "Shroff", "Simmons", "Singh", "Sisneros", "Sitters", "Skolik", "Sladek", "Slysz", "Smutek", "Snow", "Sobus", "Soderstrom", "Soding", "Solana", "Solich", "Solis", "Soman", "Somoza", "Soprano", "Soranzo", "Spaan", "Spiess", "Stark", "Stawczyk", "Steinberg", "Stewart", "Stoffelsz", "Stradivari", "Stranc", "Strid", "Stromberg", "Stupak", "Suarez", "Subramaniam", "Subramanian", "Sule", "Sundin", "Sundstrom", "Sureda", "Suresh", "Surian", "Svensson", "Swaminathan", "Sych", "Sydny", "Tagliafierro", "Tailor", "Tandon", "Tata", "Tate", "Teixeira", "Tekieli", "Tella", "Tello", "Teran", "Teruel", "Texier", "Thatcher", "Thout", "Tirie", "Tlustek", "Todd", "Tolosa", "Tomaszuk", "Tornqvist", "Torres", "Toso", "Toussaint", "Tozzi", "Tqsh", "Travaglia", "Travia", "Trebbi", "Trentin", "Trub", "Trussardi", "Trzop", "Turk", "Tusk", "Tyler", "Udinese", "Ulker", "Ungaretti", "Urena", "Urrutia", "Valenciano", "Vallee", "Valles", "Vallet", "Varano", "Vazquez", "Velez", "Verbeek", "Verdejo", "Verduzco", "Verheij", "Vermeulen", "Vidoni", "Vilar", "Villareal", "Wagner", "Walkusz", "Walla", "Wallgren", "Walters", "Warczak", "Warmer", "Warrior", "Wasala", "Watson", "Wawrzyn", "Wegrzyniak", "Wende", "Westberg", "Widuch", "Wielgo", "Wika", "Wikstrom", "Williams", "Williamson", "Wilusz", "Winnrich", "Witon", "Wochna", "Wojtanowicz", "Wolters", "Woods", "Wooning", "Wosiek", "Wright", "Wujek", "Wydrych", "Yildirim", "Zachariah", "Zambrano", "Zampa", "Zanichelli", "Zelazek", "Zengin", "Zielke", "Zimmerman", "Zmyslony"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=Path(__file__).parent / "data")
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()
    main(args.out_dir, args.seed)
