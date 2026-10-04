# Evaluation Harness — Synthetic Test Set and Results

**Location**: `backend/scripts/eval/` · **Last run**: 2026-09-26 · **Status**: methodology stable; the defects found on 2026-09-18 and 2026-09-25/26 are fixed except F5 (partly) and F7 (design) — see [Findings](#findings)

## What this measures — and what it does not

It measures **agreement between the live pipeline and spec-derived expected outcomes** on a synthetic test set: did a payment reach the intended scenario (1–5) and the intended recommendation (APPLY / HOLD / ESCALATE)?

It is **not** accuracy against real analyst decisions. The expected outcomes come from `docs/Final_Scenario_Definitions.md`, encoded by a human-written archetype table; the data is LLM-generated (Gemini 2.5 Flash, the same model family the pipeline uses for parsing and name scoring). Any figure quoted from this harness must say **"synthetic test set"**.

## How it works

```
generate.py                                                 run_eval.py
  1 world   Gemini builds customers/policies/history          5 load world into isolated DB (ces_eval)
            in chunks (JSON-schema-constrained output,        6 per case: clear payments, ingest prior payment
            enums derived from the .proto files)                 (if any) then the payment through the REAL
  2 cases   Gemini instantiates each ARCHETYPE, batched         POST /api/payments/ingest + pipeline
            per archetype, with an eligibility hint and       7 live LLM calls; gray-zone cases re-run N times
            a repair loop                                     8 score route + recommendation; report by
  3 checks  plain arithmetic, no pipeline code, rejects         variant / scenario / archetype, confusion
            cases that violate their archetype                  matrix, false-APPLY, identity, parsing,
  4 noise   seeded deterministic perturbations ("twins")        latency, gray-zone stability
```

Design decisions worth keeping:

- **Labels never come from the LLM.** Expected outcomes live in `ARCHETYPES` in `generate.py`; the LLM only supplies realistic data. This avoids grading the system against a model's opinion of the spec.
- **Independent checks.** `check_case()` verifies each generated case with arithmetic (variance %, duplicate window, policy counts) and imports nothing from the pipeline.
- **Isolation.** Payments are cleared between cases so cases cannot trigger each other's duplicate detection. Only a case's own prior payment is ingested first.
- **Safety guard.** `run_eval.py` refuses to run unless the target database name ends in `_eval`, so it can never wipe the dev database.
- **Determinism where it matters.** Noise is seeded (`NOISE_SEED = 7`) and applied in code, not by an LLM. LLM generation is *not* reproducible: regenerating produces a different dataset, so `data/full.json` is the frozen corpus.

## Files and commands

| File | Purpose |
|------|---------|
| `backend/scripts/eval/generate.py` | World + case generation, independent checks, noise twins |
| `backend/scripts/eval/run_eval.py` | Runs cases through the real pipeline and reports |
| `backend/scripts/eval/data/full.json` | Frozen corpus: 42-customer world + 192 cases |
| `backend/scripts/eval/data/full_results_before_dup_fix.json` | Results before the duplicate-rule fix |
| `backend/scripts/eval/data/full_results.json` | Results after the fix |

One-time setup of the isolated database (from the repo root; adjust the host port to your compose file):

```bash
docker compose exec db psql -U ces_user -d ces -c "CREATE DATABASE ces_eval OWNER ces_user;"
cd backend
export DATABASE_URL="postgresql+asyncpg://ces_user:ces_password@localhost:5432/ces_eval"
python -m alembic upgrade head
python - <<'EOF'
import asyncio, sys
sys.path.insert(0, "scripts")
import seed  # binds to DATABASE_URL at import
async def go():
    assert seed.settings.DATABASE_URL.endswith("/ces_eval")
    async with seed.Session() as db:
        await seed.seed_users(db)
        await seed.seed_configuration_thresholds(db)   # users + thresholds only; the harness loads its own world
        await db.commit()
    await seed.engine.dispose()
asyncio.run(go())
EOF
unset DATABASE_URL
```

Run (from `backend/`; needs `OPENROUTER_API_KEY` in `backend/.env`; the eval DB URL is derived from `backend/.env` by swapping the database name, or set `EVAL_DATABASE_URL`):

```bash
python scripts/eval/generate.py --full          # optional: regenerates the corpus (different data every time)
python scripts/eval/run_eval.py --repeat-gray 4 # ~13 minutes for 192 cases at ~2.6 s per payment
```

Add `--limit N` to `run_eval.py` for a quick smoke test. Without `--full`, `generate.py` runs a 1-case-per-archetype pilot.

## Test set composition (`data/full.json`)

- **World**: 42 synthetic customers — three chunks of 12 (mixed: risk-flagged, inactive, single-policy, multi-policy, positive-balance, high-premium) plus 6 customers who each hold two identical-premium active policies. Built in chunks because a single 30-customer call drifted on size and identifiers.
- **Base cases**: 22 archetypes × 6 = **132** (16 of 165 generated cases, 9.7%, were rejected by the independent checks).
- **Noise twins**: **60** — 40 `ref_noise` (messy policy references such as `pol 90003 - ins.`, `Policy #90014`, `ref POL90001`), 17 `name_case` (case/whitespace/punctuation), 3 `name_typo` (single-character typo; APPLY or HOLD accepted).
- **Total**: **192** cases.

| Archetype | Expected | Archetype | Expected |
|-----------|----------|-----------|----------|
| S1-apply-a (trivial name variant) | S1 / APPLY | S4-unknown-person | S4 / ESCALATE |
| S1-apply-b (exact name, card) | S1 / APPLY | S4-unknown-company | S4 / ESCALATE |
| S1-hold-name (75–90% name) ¹ | S1 / HOLD | S4-third-party-hold | S4 / HOLD |
| S1-hold-risk (risk flag) | S1 / HOLD | S4-bad-policy-ref | S4 / ESCALATE |
| S2-apply-single | S2 / APPLY | S5-dup-exact | S5 / ESCALATE |
| S2-apply-multi-unique | S2 / APPLY | S5-dup-tolerance ($1 diff) | S5 / ESCALATE |
| S2-apply-single-card | S2 / APPLY | S5-dup-balance (balance > 0) | S5 / HOLD |
| S2-hold-multi-ambiguous | S2 / HOLD | S5-near-dup-control ($10 diff) ² | S1 / APPLY |
| S3-tier3-above / below | S3 / HOLD | S5-diff-ref-not-dup (probe) | S1 / APPLY |
| S3-tier4 | S3 / HOLD | S5-diff-account-dup (probe) | S5 / ESCALATE |
| S3-tier5 | S3 / ESCALATE | | |

¹ Unverifiable: a name-similarity band cannot be validated independently of a similarity function. All 8 cases were excluded from scoring.
² The generator was told to use ACH but the checker did not enforce it; 5 cases used Wire/Check (correctly HOLD) and were excluded.

## Results (2026-09-18, one main pass, live LLM)

The **valid-label set** is the 192 cases minus 13 whose labels were wrong (8 × S1-hold-name, 5 × S5-near-dup-control with a non-low-risk method). Those exclusions were decided after seeing the results; the raw figures are shown too.

| | Before duplicate fix | After duplicate fix |
|---|---|---|
| Valid-label set, scenario **and** recommendation correct | 156/179 = 87.2% | **169/179 = 94.4%** (95% CI 90.0–96.9) |
| Scenario routing alone (184 cases with a valid scenario label) | 162/184 = 88.0% | 176/184 = 95.7% |
| Raw, all 192 cases | 156/192 = 81.2% | 169/192 = 88.0% |
| Duplicate-rule probes (18) | 0/18 | 16/18 |
| Unsafe APPLY in the valid-label set | 10 | 3 |

After the fix, by expected scenario (valid-label set): S2 34/34, S4 32/32, S3 34/36 (the two misses are reference-parser cases). Scenarios 1 and 5 were dragged down mainly by the duplicate-rule probes.

- **Run-to-run noise**: three cases got worse between the runs (a gray-zone name flip, a reference-parse miss, and one duplicate miss that did not reproduce in 36 isolated runs). Treat single-run differences of about three cases as noise. The 12 clean duplicate probes going from 0/12 to 12/12 is not noise.
- **Latency per payment** (ingest → recommendation, local machine, live LLM, n = 192): p50 2.6 s, p95 3.4 s, max 4.1 s. Pipeline `processing_time_ms`: p50 1.9 s, p95 2.7 s.
- **Gray-zone stability**: 9 of 192 cases used the LLM name score, each run 5 times. Before the fix 2/9 changed outcome (APPLY↔HOLD) and 5/9 changed name score; after, 1/9 and 6/9. Max name-score spread 7.5 points.
- **Processing failures**: 3/192 in both runs (finding F4).

## Findings

Status as of 2026-09-26 (F1–F9 reported 2026-09-18; F10–F16 found 2026-09-25/26). "Evidence" points at code read during the investigation.

| # | Finding | Evidence | Status |
|---|---------|----------|--------|
| F1 | Duplicate check matched on **sender account** instead of the **policy reference** required by the spec: duplicates from another account were missed (APPLY), and two identical-premium policies paid from one account were escalated | `duplicate.py`; 18/18 probes | **Fixed** — now sender + method + `reference_field_1` (exact) + amount ±$2 within 72 h |
| F2 | Reference is parsed **twice** by the LLM (`pipeline.py:255`, "not persisted at ingest") and the second parse decides routing. The parser is inconsistent: identical messy references gave different outputs across 3 calls for 7/40; `pol-91006` parsed correctly 4/10 times (sequential, no errors logged) vs 5/5 for `POL-91006`; malformed `POL90001` is accepted un-normalised | direct re-parse tests | **Fixed 2026-09-26** — deterministic regex parser in the app (`ingest.py`): normalised to POL-XXXXX, parsed once (ingest passes its parse to the pipeline). 4650/4650 policy numbers extracted on the 5,000-case set |
| F3 | `sc2.py:48` turns a missing variance into 0 (`or 0`), so when the policy is not identified a single-policy customer can get APPLY for a payment far below premium (observed: $1,500 vs $2,000 premium → APPLY). Scenario 2 also appears not to check risk flags (**unverified**: observed once, not confirmed in code) | `S3-tier3-below-05~ref_noise`, `S1-hold-risk-05~ref_noise` | **Fixed 2026-09-26** — S2 takes the variance from the customer's active policy and HOLDs when it cannot be computed; confirmed S2 ignored risk flags, so an S2 APPLY for a risk-flagged customer now becomes HOLD (a new rule, documented in the scenario docs) |
| F4 | `sc1.py:82` formats a `None` variance (`signals.get("amount_variance_pct", 0)` only defaults when the key is absent) → `TypeError`, non-retryable → `PROCESSING_FAILED`, triggered by malformed/non-existent policy numbers from the parser | 3/192 payments | **Fixed 2026-09-26** — `sc1.py` no longer formats a `None` variance |
| F5 | Gray-zone name scoring is unstable: `_llm_score` (`matching.py`) sets no temperature; the model answers in round numbers (90/95) against a ">90" apply threshold; the spec's own middle-initial example (`James R Wilson` vs `James Wilson`) got an LLM score of 50 | 2/9 gray-zone cases flipped outcome | **Partly fixed 2026-09-26** — `temperature=0` is now set on the name call; not re-measured. The model still answers in round numbers (90/95) against a ">90" threshold. Middle initials no longer reach it (deterministic rule, see below) |
| F6 | `run_signal_engine` reads `reference_1`/`reference_2`, but the pipeline supplies DB column names (`reference_field_1/2`), so reference-text keyword detection for third-party payments receives `None` in production; the engine's own tests use `reference_1`, so they do not catch it | code read; not run-tested | **Fixed 2026-09-26** — the engine reads `reference_field_1/2` (legacy keys still accepted); test added |
| F7 | Initial + surname names (`C. Gomez` vs `Carlos Gomez`) score 61–66 deterministically, skip the LLM (below 70) and ESCALATE to Scenario 4 even with an exact policy number and amount. Spec-conformant (< 75% escalates) — a coverage gap, not a bug | 4 `S1-hold-name` cases | Open (design) |
| F8 | The duplicate query skips payments with status `processing_failed`, so a crashed first payment could let a later duplicate through. **Hypothesis** for one unexplained missed duplicate; not reproduced | `duplicate.py` SQL | **Fixed 2026-09-26** — only `returned` payments are ignored (a `processing_failed` payment is money that arrived) |
| F9 | 26 of 396 unit tests fail on a clean seeded database: stale expectations (e.g. expecting `applied`/`escalated` where the pipeline now lands `held`) and seed-data collisions | pytest baseline | **Fixed 2026-09-26** — 0 failures, 452 tests. Causes: stale `held` expectations, the LLM patches in `conftest.py` never took effect (F16), a missing import (F11), a renamed response key, a changed rollback permission, migration drift (F12) |
| F10 | The duplicate window had **no upper bound** (`payment_date >= cutoff` only), so a payment dated months later counted as a "prior" duplicate (`hours_since_duplicate` in the thousands); and `LIMIT 1` ran before the amount test, so the newest same-sender payment could hide an older exact duplicate | seeded September payments made the May-dated S2 e2e tests route to Scenario 5 | **Fixed 2026-09-26** — window is ±72 h, amount tolerance is in the `WHERE` |
| F11 | `POST /api/payments/{id}/reprocess` raised `NameError: _target_status` after the pipeline had run (the function was never imported), so every reprocess returned a 500 | `approvals.py:355`; 2 e2e tests | **Fixed 2026-09-26** |
| F12 | Alembic migration drift: `policy_attached` was in `db/schema.sql` and the proto but not in the migration, so `attach-policy` failed on any database built with `alembic upgrade head` (the dev DB had been patched by hand) | `test_attach_policy` (3 failures on `ces_test`) | **Fixed 2026-09-26** — migration `0002` (idempotent) + `tests/test_schema_parity.py` compares every enum in `schema.sql` with the database |
| F13 | Scenario 2 tested the **blended** `customer_match_confidence` (name 60% + account 20% + history 20%) against the 90 threshold, so an exact name with no account or history match was ESCALATED (spec: name ≥ 90% is a strong match) | 262 of 900 S2 apply-type payments in the 5,000-case set | **Fixed 2026-09-26** — tests the name similarity score |
| F14 | Middle-initial names ("Boris P. Ulker" vs "Boris Ulker") scored 76–90 and went to HOLD unless the LLM lifted them | 499 of 1,160 `S1-apply-a` payments | **Fixed 2026-09-26** — deterministic initials rule in `normalise_name_pair`. Nicknames are not expanded (business decision) |
| F15 | `historical_match` was almost always true: `compute_historical_consistency` returned 100 for constant histories (stdev 0) and for < 2 records, so it held for 721 of 750 payments 15–184% off premium; and `amount_match` could never be set in S2 (no premium to compare) | 100% true in S1/S2 archetypes | **Fixed 2026-09-26** — spread floored at 2% of the mean, ≥ 2 records required, S2 derives `amount_match` from policy premiums |
| F16 | `conftest.py` patched the LLM at the wrong place (`ingest.parse_reference_fields`, `reasoning.get_reasoning`) while callers import those names, so **the test suite made real LLM calls** (95 s, non-deterministic, spending money) | suite time 95 s → 3.8 s after the fix | **Fixed 2026-09-26** — patches applied where the names are used |

## Ablation and follow-up experiments (2026-09-25/26)

Question: does the LLM add value over code, and would an LLM make a better final decision? New tooling, all in `backend/scripts/eval/`:

| Item | Purpose |
|------|---------|
| `run_eval.py --llm live\|regex\|defaults\|name-llm\|ai-rules\|ai-open\|ai-tight`, `--out` | Arms. `regex` = no LLM anywhere (the app's own deterministic parser, deterministic name score, fallback reasoning text). `defaults` = parser finds nothing. `name-llm` = as `regex` but the gray-zone name LLM is live (isolates it). `ai-*` = an LLM makes the final APPLY/HOLD/ESCALATE (`ai_decider.py`). A tripwire counts any LLM request in a no-LLM arm; it must be 0. `--out` stops a run overwriting a stored result |
| `compare_runs.py [--corpus X] arm=file ...` | Scores arms on the valid-label set, paired discordant cases, exact McNemar test, gray-zone table |
| `ai_decider.py` | The three AI-decider prompts: `ai-rules` (full spec), `ai-open` (goal only), `ai-tight` (only the routed scenario's section + a checklist) |
| `data/heldout.json` | A second corpus (193 cases) generated 2026-09-25 with `generate.py --full`; never used to design a prompt |
| `data/mock_5000.json`, `mock_500.json` | Deterministic corpus from `generate_mock.py` (seed 42, same 22 archetypes and checks, 360 customers); `mock_initials_500.json` is a seeded random 500 of the 1,160 middle-initial payments |

The valid-label rule used everywhere: exclude every `S1-hold-name` (band unverifiable) and `S5-near-dup-control` paid by Wire/Check. That reproduces the 13 exclusions above on `full.json`, and gives 350 on `mock_5000.json`.

**Results** (valid-label set; all synthetic, spec-labelled):

| Experiment | Result |
|------------|--------|
| LLM vs code, original corpus (179 cases) | live LLM 169 (94.4%) and 171 (95.5%) in two runs; code-only 174 (97.2%); LLM down (parser defaults) 94 (52.5%, 40 false-APPLY). Live vs code: 3 vs 8 discordant, exact McNemar p = 0.23 — not distinguishable |
| Who makes the decision (original / held-out) | code 174 / 163; AI with the full spec 164 & 162 / 157; AI with a tight per-scenario checklist prompt 150 / 150; AI with no rulebook 121 (of 179). The AI never beat the code on the original corpus (10–0, p = 0.002); it changed its answer on 10 of 192 payments between two identical runs (code: 0). The tight prompt lost mainly by reading a null variance literally |
| Name LLM on 500 random middle-initial payments | code-only 266 (53.2%); name LLM live 472 (94.4%); it lifted 210 of 220 payments the deterministic score could not clear, but 93% of the lifts were an exact "95", 6% of scores changed between identical passes, 2% flipped the outcome. A deterministic "ignore an unmatched initial" rule reaches 100% of the 1,160 (F14) |
| Cost and speed, live pipeline (100 random payments, $0.30 / $2.50 per million input / output tokens) | reference parse 1.98 calls per payment ($0.28 per 1,000 payments), reasoning text 1.00 ($0.39), name gray zone 0.21 ($0.03): **about $0.70 per 1,000 payments**; median 2.6 s per payment vs 8 ms code-only. The reasoning call cannot change a decision (the recommendation is fixed before it runs) |
| Code-only arm before → after the 2026-09-26 fixes (F2–F4, F6, F8, F10, F13–F15) | original 174/179 (97.2%) → 179/179; held-out 163/180 (90.6%) → 180/180; mock 5,000: 3,768/4,650 (81.0%) → 4,649/4,650. No case went from right to wrong |

**Read the last row with care.** The failure patterns were found on these same synthetic sets, so the near-perfect scores show the fixes cover what the generator exercises, not accuracy on real payments. Nothing here measures genuinely messy real references, nickname handling, or whether the AI's judgement beats the rules (the labels come from the same spec).

**Still open:** F7 (initial + surname, design); F5 (the name LLM answers in round numbers); a Scenario 2 payment whose variance is computed from the customer's single policy and exceeds 15% is HELD in S2 rather than rerouted to Scenario 3's tiers (so >100% variance holds instead of escalating); one `S4-unknown-person` payment routes to S2 (the recommendation, ESCALATE, is right). **About the result files.** Committed: the corpora (`full.json`, `heldout.json`, `mock_initials_500.json`) and every result that cannot be regenerated cheaply, namely the live-LLM ones (`ablation_live`, `ablation_ai-*`, `heldout_ai-*`, `initials500_name-llm`) and the code-only "before" results on the two small corpora (`ablation_regex`, `ablation_defaults`, `heldout_regex`). Not committed: deterministic outputs that regenerate in seconds with `run_eval.py --llm regex --out ...`, and the 8 MB 5,000-case results (the "before" 81.0% is from the app code at commit `9390122`). Files produced before 2026-09-26 used a harness-side regex parser in mode `regex`; since then `regex` runs the app's own deterministic parser. The `mock_*` corpora come from `generate_mock.py` and are not in the repository.

## Limitations

- Synthetic data, generated from the same spec the labels come from, by the same model family the pipeline calls; the result says the system conforms to its spec on these cases, not how it performs on real payments.
- One main pass; the only repeated measurements are the gray-zone cases.
- 13 label exclusions were decided after seeing results (disclosed above); the S1-hold-name archetype cannot be validated independently.
- Small samples for the typo twins (n = 3) and for individual archetypes (n = 6).
- The 95% intervals are Wilson intervals and assume independent cases; twins of the same base case are not fully independent.

## Environments and safety

| Database | Purpose |
|----------|---------|
| `ces` | Development data — never touched by the harness |
| `ces_eval` | Evaluation sandbox; wiped and reloaded on every run |
| `ces_test` | Optional: a freshly migrated + seeded database for `pytest` (the dev DB accumulates demo payments that collide with test fixtures) |

Do **not** run `backend/scripts/demo_restore.py` to clean up after evaluation work: it deletes all non-seed payments, resets thresholds and removes governance records from whichever database it targets.

## Extending

- New scenario rule → add an archetype (expected outcome from the spec, a construction brief, a check in `check_case`) and an eligibility rule in `eligible_ids` if it needs particular customers.
- After fixing a finding, re-run `run_eval.py` on the same `full.json` and keep the previous results file for a before/after comparison, as was done for F1.
