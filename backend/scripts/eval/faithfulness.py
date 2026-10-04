"""
Explanation faithfulness (hallucination) check for the LLM-written analyst explanations.

For every explanation produced by the live arm (data/abl_live_<corpus>.json, main pass only) it extracts each number,
percentage, dollar amount and policy / customer / payment / account ID from the text (reasoning bullets + suggested
action) and checks it against what the case actually contains:

  prompt   the facts the model was given (the context_summary passed to get_reasoning)
  case     the case's own inputs and computed signals (payment amount, premiums, name scores, variance, ids, ...), i.e.
           facts that are true of the case even though the model was not shown them

A fact is UNSUPPORTED when it matches neither. Unsupported facts are split into:
  threshold   equals a configured system threshold (2, 5, 15, 50, 70, 72, 75, 90, 92, 100, 200): the model asserts a
              business rule it was never told, which may or may not be right (needs a person to judge)
  invented    anything else: a number or ID that appears nowhere in the case

Also checks one categorical fact the prompt states explicitly: risk flags present / absent.

Matching tolerance: percentages within 0.6 points (rounding), dollar amounts within 0.5%, other numbers exactly.

Usage (from backend/):  python scripts/eval/faithfulness.py [--examples 12]
Writes data/faithfulness_flagged.json (every flagged explanation, for manual review) and prints markdown.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

from compare_runs import wilson

DATA = Path(__file__).parent / "data"
CORPORA = {"mock500": "mock_500.json", "full": "full.json", "heldout": "heldout.json",
           "fresh500": "fresh_500_seed7.json", "shift200": "shift_200.json"}
THRESHOLDS = {2, 5, 15, 50, 70, 72, 75, 90, 92, 100, 200}

ID_RE = re.compile(r"\b(?:POL|CUST|PMT|ACC)-[A-Za-z0-9]+\b")
MONEY_RE = re.compile(r"\$\s?\d[\d,]*(?:\.\d+)?")
PERCENT_RE = re.compile(r"(\d+(?:\.\d+)?)\s?%")
NUMBER_RE = re.compile(r"(?<![\w.$-])\d+(?:\.\d+)?(?![\w%])")


def facts_in(text: str) -> list[tuple[str, float | str]]:
    out: list[tuple[str, float | str]] = []
    for m in ID_RE.finditer(text):
        out.append(("id", m.group(0)))
    rest = ID_RE.sub(" ", text)
    for m in MONEY_RE.finditer(rest):
        out.append(("money", float(m.group(0).replace("$", "").replace(",", "").strip())))
    rest = MONEY_RE.sub(" ", rest)
    for m in PERCENT_RE.finditer(rest):
        out.append(("percent", float(m.group(1))))
    rest = PERCENT_RE.sub(" ", rest)
    for m in NUMBER_RE.finditer(rest):
        out.append(("number", float(m.group(0))))
    return out


def numbers_in(text: str) -> list[float]:
    return [v for kind, v in facts_in(text) if kind != "id"]  # type: ignore[misc]


def close(kind: str, value: float, pool: list[float]) -> bool:
    if kind == "percent":
        return any(abs(value - s) <= 0.6 for s in pool)
    if kind == "money":
        return any(abs(value - s) <= max(0.005 * abs(s), 0.01) for s in pool)
    return any(abs(value - s) < 0.01 for s in pool)


def case_facts(case: dict, row: dict, world_by_id: dict) -> tuple[list[float], set[str]]:
    p = case["payment"]
    nums = [p["amount_usd"], p["amount_usd"] * 100]
    nums += [row.get(k) for k in ("name_similarity", "deterministic_score", "llm_score", "amount_variance_pct", "confidence",
                                  "jaro_winkler", "levenshtein")]
    ids = {x for x in (case.get("target_customer_id"), case.get("target_policy_number"), row.get("customer_matched"), row.get("policy_matched"),
                       row.get("policy_expected"), row.get("ref_policy_extracted")) if x}
    cust = world_by_id.get(case.get("target_customer_id"))
    if cust:
        for pol in cust["policies"]:
            nums += [pol["premium_usd"], pol["premium_usd"] * 100, pol["outstanding_balance_usd"]]
            ids.add(pol["policy_number"])
            nums += [h["amount_usd"] for h in pol["history"]]
        nums.append(len([q for q in cust["policies"] if q["status"] == "active"]))
        nums.append(len(cust["policies"]))
    for prior in case.get("prior_payments", []):
        nums.append(prior["amount_usd"])
    return [float(x) for x in nums if x is not None], ids


FLAG_TERMS = {
    "Risk flags": re.compile(r"risk[- ]flags?|risk indicators?|flagged", re.I),
    "Third-party": re.compile(r"third[- ]party|third party", re.I),
    "Multi-period": re.compile(r"multi[- ]period", re.I),
    "Multi-method": re.compile(r"multi[- ]method|multiple (?:payment )?methods|split (?:premium|payment)", re.I),
}
NEG_WORDS = re.compile(r"\b(?:no|not|isn't|aren't|without|neither|nor|none|false|absent|absence|lack|lacks|rul(?:e|es|ed|ing) out|excluding|non|eliminat\w*)\b|n't\b", re.I)


def asserts_presence(sentence: str, match: re.Match) -> bool:
    """False when the term is negated in a small window around it (6 words before, 4 after), e.g. 'ruling out third-party',
    'no risk flags', 'the multi-period flag is false'. A window, not the whole sentence, so an unrelated 'no amount variance'
    elsewhere in the sentence does not flip the meaning."""
    before = sentence[:match.start()].split()[-6:]
    after = sentence[match.end():].split()[:4]
    return not (NEG_WORDS.search(" ".join(before)) or NEG_WORDS.search(" ".join(after)))


def stated_flags(summary: str) -> dict[str, bool]:
    """The boolean flags the prompt stated explicitly, e.g. 'Third-party: False (None)'."""
    return {name: value == "True" for name, value in re.findall(r"(Risk flags|Third-party|Multi-period|Multi-method): (True|False)", summary)}


def flag_contradictions(text: str, summary: str) -> tuple[int, list[str]]:
    """Sentence-level check of claims about the flags the prompt stated. Returns (claims checked, contradictions)."""
    truth = stated_flags(summary)
    checked, bad = 0, []
    for sentence in re.split(r"(?<=[.;])\s+|\n", text):
        for name, term in FLAG_TERMS.items():
            m = term.search(sentence) if name in truth else None
            if m is None:
                continue
            asserts_present = asserts_presence(sentence, m)
            checked += 1
            if asserts_present != truth[name] and not (asserts_present and not truth[name] and re.search(r"\bor\b|whether|if\b|check", sentence, re.I)):
                bad.append(f"{name}: text says {'present' if asserts_present else 'absent'}, prompt says {truth[name]} — “{sentence.strip()[:140]}”")
    return checked, bad


UNDER_RE = re.compile(r"under[- ]?pa(?:y|id|yment)|underpaid|short(?:fall)?\b|below (?:the )?expected|less than (?:the )?expected|lower than (?:the )?expected", re.I)
OVER_RE = re.compile(r"over[- ]?pa(?:y|id|yment)|overpaid|above (?:the )?expected|more than (?:the )?expected|exceed(?:s|ing)? (?:the )?expected|higher than (?:the )?expected", re.I)


def direction_claim(text: str) -> str | None:
    """'under' / 'over' when the text asserts the payment was below / above the premium (not both, not negated)."""
    hedge = re.compile(r"\b(?:not|no|n't|either|potential(?:ly)?|may|might|possib\w*|whether|could)\b|\bor (?:an? )?(?:over|under|incorrect|error|other)", re.I)
    t = " ".join(sentence for sentence in re.split(r"(?<=[.;])\s+", text) if not hedge.search(sentence))  # hedged sentences are not assertions
    under, over = bool(UNDER_RE.search(t)), bool(OVER_RE.search(t))
    return "under" if under and not over else "over" if over and not under else None


def true_direction(case: dict, world_by_id: dict) -> str | None:
    """Whether the payment was actually below or above the premium of its target policy."""
    cust = world_by_id.get(case.get("target_customer_id"))
    if not cust or not case.get("target_policy_number"):
        return None
    for pol in cust["policies"]:
        if pol["policy_number"] == case["target_policy_number"]:
            amount = case["payment"]["amount_usd"]
            return "under" if amount < pol["premium_usd"] else "over" if amount > pol["premium_usd"] else "exact"
    return None


def main(n_examples: int = 12) -> None:
    per_corpus: dict[str, Counter] = {}
    flagged: list[dict] = []
    wrong_direction: list[dict] = []
    for corpus, corpus_file in CORPORA.items():
        path = DATA / f"abl_live_{corpus}.json"
        if not path.exists():
            continue
        d = json.loads(path.read_text())
        src = json.loads((DATA / corpus_file).read_text())
        cases = {c["case_id"]: c for c in src["cases"]}
        world = {c["customer_id"]: c for c in src["world"]["customers"]}
        rows = {r["case_id"]: r for r in d["results"]}
        c = per_corpus.setdefault(corpus, Counter())
        for e in d["explanations"]:
            if e["pass"] != 0 or e["case_id"] not in cases:
                continue
            case, row = cases[e["case_id"]], rows[e["case_id"]]
            text = " ".join(e["reasoning"]) + " " + (e["suggested_action"] or "")
            c["explanations"] += 1
            if e["used_fallback"]:
                c["used_fallback"] += 1
                continue
            prompt_nums = numbers_in(e["context_summary"])
            prompt_ids = set(ID_RE.findall(e["context_summary"]))
            case_nums, case_ids = case_facts(case, row, world)
            unsupported: list[dict] = []
            n_facts = 0
            for kind, value in facts_in(text):
                n_facts += 1
                if kind == "id":
                    if value in prompt_ids or value in case_ids:
                        continue
                    unsupported.append({"kind": kind, "value": value, "class": "invented"})
                    continue
                if close(kind, value, prompt_nums):
                    continue
                if close(kind, value, case_nums):
                    c["supported_by_case_only"] += 1
                    continue
                cls = "threshold" if kind in ("percent", "number", "money") and value in THRESHOLDS else "invented"
                unsupported.append({"kind": kind, "value": value, "class": cls})
            c["facts"] += n_facts
            claim = direction_claim(text) if e["scenario"] in (1, 2, 3) else None
            if claim:
                c["direction_claims"] += 1
                truth = true_direction(case, world)
                if truth in ("under", "over") and claim != truth:
                    c["direction_wrong"] += 1
                    wrong_direction.append({"corpus": corpus, "case_id": e["case_id"], "text_says": claim, "truth": truth, "text": text[:400]})
            n_claims, bad_claims = flag_contradictions(text, e["context_summary"])
            c["flag_claims"] += n_claims
            contradiction = bool(bad_claims)
            if contradiction:
                c["risk_contradiction"] += 1
                c["flag_contradictions"] += len(bad_claims)
            if unsupported:
                c["with_unsupported"] += 1
                if any(u["class"] == "invented" for u in unsupported):
                    c["with_invented"] += 1
                if all(u["class"] == "threshold" for u in unsupported):
                    c["only_threshold"] += 1
                c["unsupported_facts"] += len(unsupported)
            if unsupported or contradiction:
                flagged.append({"corpus": corpus, "case_id": e["case_id"], "scenario": e["scenario"], "recommendation": e["recommendation"],
                                "unsupported": unsupported, "flag_contradictions": bad_claims,
                                "context_summary": e["context_summary"], "text": text})
    (DATA / "faithfulness_flagged.json").write_text(json.dumps({"flagged": flagged, "wrong_direction": wrong_direction}, indent=1))

    total = Counter()
    for c in per_corpus.values():
        total.update(c)
    print("### Explanation faithfulness (live arm, LLM-written explanations)\n")
    print("| Corpus | Explanations checked | Facts extracted (numbers, %, $, IDs) | ≥1 unsupported fact (95% CI) | …of which invented | only threshold-type | Flag claims checked | Flag claims that contradict the prompt (explanations) |")
    print("|---|---|---|---|---|---|---|---|")
    for name, c in list(per_corpus.items()) + [("**all**", total)]:
        checked = c["explanations"] - c["used_fallback"]
        if not checked:
            continue
        lo, hi = wilson(c["with_unsupported"], checked)
        print(f"| {name} | {checked} (LLM call failed: {c['used_fallback']}) | {c['facts']} | {c['with_unsupported']} = {100 * c['with_unsupported'] / checked:.1f}% (CI {100 * lo:.1f}–{100 * hi:.1f}) "
              f"| {c['with_invented']} | {c['only_threshold']} | {c['flag_claims']} | {c['flag_contradictions']} ({c['risk_contradiction']}) |")
    print(f"\nDirection of variance (scenarios 1-3; the prompt gives only the absolute variance, so under/over is a guess): "
          f"{total['direction_claims']} explanations assert under- or over-payment, {total['direction_wrong']} contradict the case "
          f"({100 * total['direction_wrong'] / max(total['direction_claims'], 1):.1f}%).")
    for w in wrong_direction[:6]:
        print(f"  - {w['corpus']}/{w['case_id']}: text says {w['text_says']}payment, actual {w['truth']}payment — “{w['text'][:200]}”")
    print(f"\nFacts supported only by the case (true, but not shown to the model): {total['supported_by_case_only']}.")
    kinds = Counter((u["class"], u["kind"]) for f in flagged for u in f["unsupported"])
    print("\nUnsupported facts by type:", ", ".join(f"{k[0]}/{k[1]} = {v}" for k, v in kinds.most_common()))
    if n_examples:
        print(f"\nExamples (flagged explanations are in data/faithfulness_flagged.json):\n")
    shown = 0
    for f in flagged:
        if shown >= n_examples:
            break
        if not any(u["class"] == "invented" for u in f["unsupported"]) and not f["flag_contradictions"]:
            continue
        shown += 1
        print(f"- **{f['case_id']}** (S{f['scenario']}, {f['recommendation']}): unsupported {[(u['kind'], u['value'], u['class']) for u in f['unsupported']]}"
              + (f"; flag claims: {f['flag_contradictions']}" if f["flag_contradictions"] else ""))
        print(f"  - given: `{f['context_summary'].replace(chr(10), ' | ')[:230]}`")
        print(f"  - wrote: {f['text'][:320]}")


if __name__ == "__main__":
    main(int(sys.argv[sys.argv.index("--examples") + 1]) if "--examples" in sys.argv else 12)
