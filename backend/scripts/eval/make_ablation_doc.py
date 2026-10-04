"""
Writes docs/Ablation_Results.md. Tables come straight from the result files (via ablation_analysis.py and
faithfulness.py); the prose is the interpretation written on 2026-09-26. Re-running regenerates the tables only.

Usage (from backend/):  python scripts/eval/make_ablation_doc.py
"""
import contextlib
import io
import json
import re
import subprocess
import sys
from pathlib import Path

import ablation_analysis as A
import faithfulness as F
from spend import file_spend

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "docs" / "Ablation_Results.md"


def capture(fn, *args) -> str:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
        fn(*args)
    return re.sub(r"^### .*\n+", "", buf.getvalue(), count=1).strip()


def h(text: str) -> str:
    return text.strip() + "\n"


def name_llm_action() -> str:
    """Where the gray-zone name LLM acts, and what it does to the excluded S1-hold-name archetype."""
    used = total = changed = 0
    for corpus in ("full", "heldout", "mock500", "fresh500", "shift200"):
        ra, rb = A.rows_of(A.load_arm("regex", corpus)), A.rows_of(A.load_arm("name-llm", corpus))
        total += len(rb)
        u = [i for i in rb if rb[i]["used_llm"]]
        used += len(u)
        changed += sum(1 for i in u if ra[i]["recommendation"] != rb[i]["recommendation"])
    hn = {arm: [0, 0, 0] for arm in ("regex", "name-llm")}
    for corpus in ("full", "heldout", "mock500", "fresh500"):
        for arm in hn:
            rs = [r for r in A.rows_of(A.load_arm(arm, corpus)).values() if r["archetype_id"] == "S1-hold-name"]
            hn[arm][0] += len(rs)
            hn[arm][1] += sum(r["recommendation"] == "hold" for r in rs)
            hn[arm][2] += sum(r["recommendation"] == "apply" for r in rs)
    rest = hn["regex"][0] - hn["regex"][1] - hn["regex"][2]
    return (f"The name LLM is asked on {used} of {total} payments ({100 * used / total:.1f}%) and changes the recommendation on {changed}. "
            f"On the {hn['regex'][0]} `S1-hold-name` payments (label: HOLD; excluded from every accuracy figure above because the 75–90 band cannot be "
            f"validated independently), the regex arm recommends HOLD {hn['regex'][1]} times and APPLY {hn['regex'][2]}; the name-llm arm recommends HOLD "
            f"{hn['name-llm'][1]} times and APPLY {hn['name-llm'][2]}. (The other {rest} escalate in both arms.)")


def provenance() -> str:
    files = sorted(A.DATA.glob("abl_*.json"))
    commits, dirty, models = set(), set(), set()
    for f in files:
        d = json.loads(f.read_text())
        if isinstance(d, dict) and "meta" in d:
            commits.add(d["meta"]["commit"][:7])
            dirty.add(d["meta"]["app_dirty"])
            models.add(d["meta"]["model"])
    spend = sum(file_spend(f) for f in files)
    return f"{len(files)} result files, produced at commit(s) {', '.join(sorted(commits))} with `backend/app` unmodified ({'no' if dirty == {False} else 'SOME'} uncommitted app changes), model {', '.join(models)}. LLM spend recorded in them: **${spend:.2f}** at OpenRouter list price ($0.30 / $2.50 per million input / output tokens)."


def main() -> None:
    sections: list[str] = []
    add = sections.append

    add(h(f"""
# Ablation results: where does the LLM earn its place in CES?

**Date**: 2026-09-26 · **Code**: commit `a45ca38` (`backend/app` unmodified during these runs) · **Model**: `google/gemini-2.5-flash` via OpenRouter · **Reproduce**: `scripts/eval/` (see [Files](#files-and-reproduction))

{provenance()}

## Read this first: what these numbers can and cannot support

1. **The rules were fitted to failures found on these test sets.** The fixes shipped in commit `989befb` (Scenario 2 strong-match test, middle-initial rule, "policy no." pattern, duplicate window and others) were designed after reading failures on `full.json`, `heldout.json` and `mock_5000.json`. `mock_500.json` is a subset of `mock_5000.json`, and `heldout.json` was inspected too. So the 100% in-distribution scores of the rule-based arms are **by construction** and are not an accuracy estimate. Two checks limit the damage: `fresh_500_seed7.json` is the same generator with a new seed (zero identical payments, zero shared customer names), so it tests new *instances*; and `shift_200.json` tests new *formats*. It does not test new *templates*: every corpus comes from one generator with 22 archetypes.
2. **Labels come from the same specification the rules implement.** The best any arm can do is agree with the spec. These experiments cannot show that an LLM's *judgement* is better than the rules. That needs human outcomes (for example analysts' overrides).
3. **The one place the name LLM changes outcomes is excluded from scoring.** The `S1-hold-name` archetype (nickname and typo pairs scoring 75–90) is excluded because its label cannot be validated independently. See [Task 2](#task-2-the-optimised-configuration-as-its-own-arm).
4. **On today's code the reference parser is a regex**, so `live` (name LLM + LLM explanations) is exactly the "name-llm+explain" arm you asked for. The LLM *parser* is measured with two experiment-only arms (`parse-llm`, `parse-fallback`) that live in `scripts/eval/legacy_parser.py`, not in the app.
5. **Timings** are per-payment wall time in an in-process harness on one machine with three experiment lanes running concurrently; LLM call latencies are network-bound and comparable, but treat sub-second harness times as indicative.
6. **The manual review in Task 6 was done by an LLM (Claude), not a person.** Please re-score the sample (`data/faithfulness_sample40.json`, my labels in `data/faithfulness_manual_review.json`) before quoting it.

## Summary table

Corpus `mock_500` (465 valid-label cases; accuracy = scenario **and** recommendation correct, 95% Wilson CI).

{capture(A.cmd_summary, "mock500")}

On the unseen-seed corpus (`fresh_500_seed7`, 465 valid-label cases):

{capture(A.cmd_summary, "fresh500")}

Under format shift (`shift_200`, 200 cases rewritten in formats the rules were not built for, labels unchanged):

{capture(A.cmd_arms, "shift200", ("regex", "name-llm", "live", "ai-rules", "parse-fallback", "parse-llm"), "regex")}
"""))

    add(h("""
## What you can and cannot claim in a case study

**Defensible, with the numbers above:**

1. *Letting an LLM make the final decision, with the full specification in its prompt, was worse than the rule engine and less stable:* 94.2% on `mock_500` and 91.8% on an unseen-seed corpus against 100% for the rules on the same cases (27 and 38 cases only the rules got right, 0 the other way; p < 0.001), 6.6% of recommendations flipped between two identical runs, about $4.18 per 1,000 payments against $0. Its errors are systematic: third-party payers, a second same-premium policy, and conditions it invented.
2. *LLM-written explanations cannot change a decision and are the largest LLM cost in the pipeline:* $0.38 per 1,000 payments (97% of the live arm's LLM spend), about 1.3 s per payment. They almost never invent numbers (3 of 1,801 flagged, 2 confirmed), but in a hand-read sample of 40 (one reviewer, an LLM) 5% contained a wrong statement and 12.5% asserted domain facts that were not in the input; when they state whether a payment was over or under the premium they are wrong 2 times in 18, because the prompt does not say.
3. *The old LLM reference parser lost to a regex on this data:* 98.1% and 95.9% against 100%, at twice the calls per payment in production.
4. *The gray-zone name LLM is cheap and rarely used but its value is unproven:* it runs on 5.1% of payments for about a cent per 1,000, changes nothing on the scored labels, and its only effect is to turn HOLD into APPLY for nickname and typo pairs, an unlabelled area.
5. *Everything, rules and LLMs alike, fails under unseen input formats:* the rule engine falls from 100% to 32%, the LLM-decides arm from 92.5% to 30.5%.

**Not defensible from these experiments:**

- "The rule engine is 100% accurate": its rules were fitted to failures on these templates. Say "agrees with the specification on 100% of unseen-seed instances of the same templates".
- "LLMs are worse than rules": the labels come from the rules' own specification, so the LLM could at best tie. The claim is about faithfully applying a specification, not about judgement.
- "The LLM parser is worse in general": the prompt was the one production used; a prompt written for messy references was not tried (that needs a second shift set).
- Any real-world accuracy or cost figure: the data is synthetic and the volumes are unmeasured.
"""))

    add(h(f"""
## Task 1: cost and time for every arm

What was measured: every live LLM call site is wrapped (`run_eval.py`, `_UsageClient`) and records prompt, completion and reasoning tokens and wall time per call; the AI-decider arms record the same. Main-pass usage only (the repeat pass for stability is excluded).

{capture(A.cmd_cost, "mock500")}

Result: the whole LLM cost of the optimised configuration is the name call (about a cent per 1,000 payments). The **explanation call is the expensive one**: it is nearly all of the `live` arm's cost and about 1.3 s of its median time, for text that cannot change a decision. Letting an LLM decide costs about 10× the `live` arm and about 400× the optimised arm (and $4.18 against $0 for the code), and adds a second or more per payment. The old production parser made **two** calls per payment (at ingest and again in the pipeline); the `parse-llm` row counts one, so double it for the old system. Thinking is off: no call reported reasoning tokens and completion tokens track the visible output.

Same table on the second corpus (`fresh500`):

{capture(A.cmd_cost, "fresh500").split("Per call site")[0].strip()}

Caveat: LLM calls fail occasionally (10 of the `live` arm's reasoning calls on `fresh500` timed out and used the template; 2 AI decisions failed and were counted as ESCALATE).
"""))

    add(h(f"""
## Task 2: the optimised configuration as its own arm

`name-llm` = regex reference parser + LLM only for gray-zone names + template explanations. `name-llm+explain` = the same with the live LLM explanation call; on today's code this is identical to `live`, so it is run once and reported under both names, and the explanation is priced separately by subtraction.

**`full.json`** (192 cases, 179 valid)

{capture(A.cmd_arms, "full", ("regex", "name-llm", "live"), "regex")}

**`heldout.json`** (193 cases, 180 valid)

{capture(A.cmd_arms, "heldout", ("regex", "name-llm", "live"), "regex")}

**`mock_500.json`** (500 cases, 465 valid)

{capture(A.cmd_arms, "mock500", ("regex", "name-llm", "live"), "regex")}

Result: on every corpus the three arms are **identical on the scored labels** (0 discordant cases, McNemar p = 1.0). The explanation call and the name call therefore add **no measurable accuracy** here. {name_llm_action()}

What that means: the name LLM does act, but only on nickname and typo pairs (`Dan Lovato`/`Daniel Lovato`, `Galo Pasra`/`Galo Parsa`), and every time it converts HOLD into APPLY. By the spec's labels that is wrong; by the spec's own hybrid design (final score = max(deterministic, LLM), APPLY above 90) it is intended. Which is right is a business question these labels cannot settle, and the corpus has no *different-person* pair in the gray zone, so the LLM's false-match rate is **unmeasured**. It answered exactly 95 for all 21 distinct pairs it lifted.
"""))

    add(h(f"""
## Task 3: does "rules / optimised ≥ LLM decides" hold at n = 465?

Arms on `mock_500` (465 valid-label cases). Paired columns give the discordant counts (cases only one arm gets right), the exact McNemar p and a paired-bootstrap 95% interval for the accuracy difference.

**`mock_500.json`**

{capture(A.cmd_arms, "mock500")}

**`fresh_500_seed7.json`** (unseen seed)

{capture(A.cmd_arms, "fresh500")}

Result: yes, and by a margin that is not noise. On `mock_500` the optimised arm beats the LLM-decides arm by 5.8 points (27 cases only the rules get right, 0 the other way, p < 0.001); on the unseen-seed corpus by 8.2 points (38 vs 0). The per-scenario checklist prompt (`ai-tight`) is worse still (81.9%): 83 of its 84 errors are Scenario 2 payments (70 escalated, 13 held) where the variance signal is null and the checklist made the model read "variance ≤ 15%" literally as false. Caveat: the rules were built from this spec and these templates, so "rules ≥ LLM" here means "the rules faithfully implement the spec"; the LLM was given the spec verbatim and still misapplied it (Task 4).
"""))

    add(h(f"""
## Task 4: error analysis by cause and arm

Every wrong case (scenario or recommendation not as labelled) is assigned one cause by the first matching rule (`classify()` in `ablation_analysis.py`). For the AI-decider arms the cause is refined with what the model itself wrote.

**`mock_500.json`**

{capture(A.cmd_errors, "mock500")}

**`fresh_500_seed7.json`**

{capture(A.cmd_errors, "fresh500")}

**`shift_200.json`** (rule-based arms lose their points here)

{capture(A.cmd_errors, "shift200")}

Result: the LLM-decides arm fails in three characteristic ways on both corpora: it escalates or holds **third-party payers** the spec says to HOLD, it holds payments that name a policy because the customer has a **second policy with the same premium**, and it holds clean Scenario 1 payments by **adding conditions that are not in the spec** (it misread "human approval is always required" as a reason to hold, invented balance and timing conditions, and mis-tiered a variance of 0.85% as "Tier 2 (2–15%)"). The rule-based arms have no errors in distribution; under format shift **all** of their errors come from two causes, an unparsed reference and a surname-first name (Task 7).
"""))

    add(h(f"""
## Task 5: consistency (run-to-run stability)

{capture(A.cmd_stability)}

Accuracy of `ai-rules` on `mock_500`: run 1 = 94.2%, run 2 = 93.1% (paired p = 0.49, i.e. the same accuracy). Of the 46 cases that were wrong in at least one run, 13 were wrong in both and 33 (72%) in only one, so most of the LLM's errors are not repeatable. The regex arm was run twice on `mock_500`: **0 of 500** cases differ in any of scenario, recommendation, decision path, confidence, name score, extracted policy, matched customer or matched policy (`data/abl_regex_mock500_run2.json`). The gray-zone name call now sets `temperature=0` (commit `989befb`): its score changed in 1 of 81 gray-zone cases in the `name-llm` arm and in 0 of 81 in `live`, against about 6% before the change (measured on a different case set, so not a controlled before/after).
"""))

    add(h(f"""
## Task 6: are the LLM's explanations faithful?

What was measured: for every explanation the live arm wrote (1,801 across five corpora, main pass, including the prior payment of duplicate cases), every number, percentage, dollar amount and policy / customer / payment ID was extracted and checked against (a) the facts the model was given and (b) the case's own inputs and signals. Categorical claims about risk flags, third-party, multi-period and multi-method were checked against the flags the prompt stated. A separate check compares any confident claim of under- or over-payment with the actual payment and premium. Finally 40 explanations (seeded, 8 per scenario) were read by hand.

{capture(F.main, 0)}

**Manual review of 40 explanations** (reviewer: Claude, not a person; first pass):

| Label | Count of 40 | Meaning |
|---|---|---|
| Clean | 16 (40%) | every statement traces to the prompt |
| Minor overreach | 17 (42.5%) | inference or overstatement that is not checkably false ("first-time transaction", "exact match" for a name that differs by an initial) |
| External claim | 5 (12.5%) | domain facts not in the input ("ACH offers less recourse than credit card", "Wire often requires manual reconciliation") |
| **Wrong** | **2 (5%; CI 1.4–16.5)** | item 24 says "suggesting underpayment" for a payment that was an **overpayment** ($505.04 against a $306.00 premium); item 27 says "Unidentified payment method: ACH" |

Result: the explanations almost never invent a number or ID (3 of 1,801 flagged automatically; on reading, two were one real fabrication, an invented "24-hour look-back period" for a duplicate found at 30 hours when the window is 72 hours, and one was correct rounding), and none contradicted a stated flag (all automated flag warnings were false positives on reading). But the model **guesses what the prompt does not say**: the prompt gives only the absolute variance, and of the 18 explanations that confidently state under- or over-payment 2 (11%) are wrong. In the hand-read sample 17.5% (7/40; CI 8.7–32.0) contained a claim the input does not support (external or wrong). Caveats: the numeric checker cannot see wrongly *reasoned* claims (the manual sample can, at n = 40 and with one non-independent reviewer); an explanation cannot change the decision, but an analyst reading a wrong direction could be misled.
"""))

    add(h(f"""
## Task 7: robustness to format shift

`shift_200.json` (built by `build_shift.py`, seed 20260926) takes 200 cases from `mock_500` and rewrites each in one format the rules were not built for; labels are unchanged. Reference formats `Policy: 12345` (T1), `PN12345` (T2), `ref#12345/INS` (T3), bare `12345` (T4); names `Khan, Aisha` (T5) and `KHAN AISHA` (T6); a currency amount in the memo (T7). For duplicate cases the same format is applied to the prior payment. The regex was written before these formats were chosen; T1 and T7 happen to be covered by it, T2-T4 are not.

{capture(A.cmd_shift)}

Result: **every arm collapses under format shift**: the rule-based arms lose 68 points (100% → 32%), the LLM-decides arm 62 (92.5% → 30.5%) and the old LLM parser 77 (100% → 23%). All of the rule-based arms' errors have two causes: 76 unparsed references (T2-T4) and 60 surname-first names (T5, T6: 0 of 60 correct). The LLM is **not** a fix with today's prompts: the LLM-fallback arm (regex first, then the LLM) recovers only 2 more of the 159 policy references; a direct probe shows why, since the production parse prompt asks for "a string matching pattern POL-XXXXX, or null", so the model returns `null` for `PN12731`, `ref#10344/INS`, a bare `13102`, and even `Policy: 13186` (8 probes, `legacy_parser.llm_parse`). A prompt written for these formats might do better; designing it against this set would be tuning on the test set, so that work needs a second shift set. The hybrid name scorer cannot rescue T5/T6 either: a surname-first name scores below the gray-zone floor of 70, so the LLM is never asked.

Caveats: T1 and T7 are covered by design, so −68 points measures how far outside its coverage the regex falls, not how often such formats occur in real data (unknown). The shift set derives from `mock_500`, whose cases the rules were fitted to.
"""))

    add(h(f"""
## Task 8: confidence calibration

In distribution (`mock_500` + `fresh_500`), where the rule-based arms are correct everywhere:

{capture(A.cmd_calibration, "mock500,fresh500")}

Under format shift, where they are wrong two times in three:

{capture(A.cmd_calibration, "shift200")}

Result: in distribution the bucket table is uninformative because there is nothing to separate. Under shift the code's confidence is **informative**: answers at confidence 90+ were right 20 of 20 times, while every wrong answer sits below 90, so the stored confidence does drop when the input is unfamiliar and could be used to rank the review queue. The LLM-decides arm's self-reported confidence is only weakly related to correctness (87.6% correct below 70, 96.7% at 90+, non-monotonic in between). Caveat: the code's confidence is a constant per decision path (16-19 distinct values), not a probability, and in `live` it depends on the name score, so it differs slightly from `regex`.
"""))

    add(h("""
## Task 9: ship the regex parser (not run: needs your confirmation)

You asked for this only on confirmation, so **no application code was changed** for these experiments (`backend/app` is byte-identical to commit `a45ca38`; every result file records `app_dirty: false`).

Two things differ from the plan as written, and you should decide on both:

- **Most of it already shipped in commit `989befb`** (on `origin/nalin-dev`): the LLM reference parser was replaced by a regex, the ingest parse is passed to the pipeline (parsed once; passed, not persisted), and the gray-zone name call sets `temperature=0`. It shipped **without** an LLM fallback.
- **The evidence in this study does not support adding the fallback as designed.** With the production prompt the fallback recovers 2 of 159 shifted references (44.7% vs 43.4% extraction) for about $0.025 per 1,000 payments (the fallback's calls; the arm's $0.036 total includes the name call) and one extra LLM call on 27% of payments. It would only be worth having with a prompt written and validated on a *second* shift set.

Still open from your list if you confirm: adding the fallback; persisting the parse; `temperature=0` on the reasoning call; and the stale "Claude Haiku" docstring on `_llm_score` in `matching.py`.
"""))

    add(h(f"""
## Files and reproduction

| File | Purpose |
|---|---|
| `scripts/eval/run_eval.py --llm <arm> --data <corpus> --out data/abl_<arm>_<corpus>.json [--repeat-gray 1]` | runs an arm; records provenance, per-call-site usage, explanations |
| arms | `regex`, `name-llm`, `name-llm+explain` (= `live`), `parse-llm`, `parse-fallback`, `ai-rules`, `ai-tight` |
| `scripts/eval/legacy_parser.py` | experiment-only LLM parser arms (production LLM parser copied from commit `9390122`; regex → LLM fallback) |
| `scripts/eval/build_shift.py` | builds `data/shift_200.json` |
| `scripts/eval/ablation_analysis.py` | every table in this document (`cost`, `arms`, `errors`, `stability`, `shift`, `calibration`, `summary`) |
| `scripts/eval/faithfulness.py` | Task 6 checker; `data/faithfulness_flagged.json`, `faithfulness_sample40.json`, `faithfulness_manual_review.json` |
| `scripts/eval/spend.py` | adds up recorded LLM spend; the runners stopped AI-decider runs above $11 |
| `scripts/eval/make_ablation_doc.py` | regenerates this document's tables |
| corpora | `full.json` (192), `heldout.json` (193), `mock_500.json`, `fresh_500_seed7.json` (`generate_mock.py --seed 7`), `shift_200.json` |

Valid-label set: exclude every `S1-hold-name` and every `S5-near-dup-control` paid by Wire/Check (`compare_runs.excluded_case_ids`). Accuracy is scenario and recommendation both correct; intervals are Wilson; McNemar is exact and two-sided; paired differences use a seeded bootstrap (4,000 resamples).
"""))

    OUT.write_text("\n".join(sections))
    print(f"wrote {OUT}  ({len(OUT.read_text().splitlines())} lines)")


if __name__ == "__main__":
    main()
