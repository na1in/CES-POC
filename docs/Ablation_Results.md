# Ablation results: where does the LLM earn its place in CES?

**Date**: 2026-09-26 · **Code**: commit `a45ca38` (`backend/app` unmodified during these runs) · **Model**: `google/gemini-2.5-flash` via OpenRouter · **Reproduce**: `scripts/eval/` (see [Files](#files-and-reproduction))

27 result files, produced at commit(s) a45ca38 with `backend/app` unmodified (no uncommitted app changes), model google/gemini-2.5-flash. LLM spend recorded in them: **$9.74** at OpenRouter list price ($0.30 / $2.50 per million input / output tokens).

## Read this first: what these numbers can and cannot support

1. **The rules were fitted to failures found on these test sets.** The fixes shipped in commit `989befb` (Scenario 2 strong-match test, middle-initial rule, "policy no." pattern, duplicate window and others) were designed after reading failures on `full.json`, `heldout.json` and `mock_5000.json`. `mock_500.json` is a subset of `mock_5000.json`, and `heldout.json` was inspected too. So the 100% in-distribution scores of the rule-based arms are **by construction** and are not an accuracy estimate. Two checks limit the damage: `fresh_500_seed7.json` is the same generator with a new seed (zero identical payments, zero shared customer names), so it tests new *instances*; and `shift_200.json` tests new *formats*. It does not test new *templates*: every corpus comes from one generator with 22 archetypes.
2. **Labels come from the same specification the rules implement.** The best any arm can do is agree with the spec. These experiments cannot show that an LLM's *judgement* is better than the rules. That needs human outcomes (for example analysts' overrides).
3. **The one place the name LLM changes outcomes is excluded from scoring.** The `S1-hold-name` archetype (nickname and typo pairs scoring 75–90) is excluded because its label cannot be validated independently. See [Task 2](#task-2-the-optimised-configuration-as-its-own-arm).
4. **On today's code the reference parser is a regex**, so `live` (name LLM + LLM explanations) is exactly the "name-llm+explain" arm you asked for. The LLM *parser* is measured with two experiment-only arms (`parse-llm`, `parse-fallback`) that live in `scripts/eval/legacy_parser.py`, not in the app.
5. **Timings** are per-payment wall time in an in-process harness on one machine with three experiment lanes running concurrently; LLM call latencies are network-bound and comparable, but treat sub-second harness times as indicative.
6. **The manual review in Task 6 was done by an LLM (Claude), not a person.** Please re-score the sample (`data/faithfulness_sample40.json`, my labels in `data/faithfulness_manual_review.json`) before quoting it.

## Summary table

Corpus `mock_500` (465 valid-label cases; accuracy = scenario **and** recommendation correct, 95% Wilson CI).

| Arm | Accuracy (95% CI) | Wrong APPLY | Over-escalate | Cost per 1,000 payments | p50 time / payment | Stability |
|---|---|---|---|---|---|---|
| regex (no LLM) | 100.0% (465/465; CI 99.2–100.0) | 0 | 0 | $0.00 | 0.00 s | 0% (deterministic) |
| name-llm (optimised) | 100.0% (465/465; CI 99.2–100.0) | 0 | 0 | $0.01 | 0.01 s | pooled over 4 corpora: gray-zone LLM score changed in 1/81, outcome in 1/81 |
| live = name-llm+explain | 100.0% (465/465; CI 99.2–100.0) | 0 | 0 | $0.39 | 1.31 s | pooled over 4 corpora: gray-zone LLM score changed in 0/81, outcome in 0/81 |
| parse-fallback (regex → LLM) | 100.0% (465/465; CI 99.2–100.0) | 0 | 0 | $0.04 | 0.01 s | not repeated |
| parse-llm (old LLM parser) | 98.1% (456/465; CI 96.4–99.0) | 0 | 0 | $0.14 | 0.63 s | not repeated |
| ai-tight (LLM decides) | 81.9% (381/465; CI 78.2–85.2) | 1 | 70 | $1.68 | 1.56 s | 3.6% flipped (n=192, full.json, pre-fix code) |
| ai-rules (LLM decides) | 94.2% (438/465; CI 91.7–96.0) | 0 | 10 | $4.18 | 1.19 s | 6.6% of recommendations flipped between 2 runs (n=500) |

On the unseen-seed corpus (`fresh_500_seed7`, 465 valid-label cases):

| Arm | Accuracy (95% CI) | Wrong APPLY | Over-escalate | Cost per 1,000 payments | p50 time / payment | Stability |
|---|---|---|---|---|---|---|
| regex (no LLM) | 100.0% (465/465; CI 99.2–100.0) | 0 | 0 | $0.00 | 0.00 s | 0% (deterministic) |
| name-llm (optimised) | 100.0% (465/465; CI 99.2–100.0) | 0 | 0 | $0.01 | 0.01 s | pooled over 4 corpora: gray-zone LLM score changed in 1/81, outcome in 1/81 |
| live = name-llm+explain | 100.0% (465/465; CI 99.2–100.0) | 0 | 0 | $0.38 | 1.33 s | pooled over 4 corpora: gray-zone LLM score changed in 0/81, outcome in 0/81 |
| parse-fallback (regex → LLM) | 100.0% (465/465; CI 99.2–100.0) | 0 | 0 | $0.04 | 0.01 s | not repeated |
| parse-llm (old LLM parser) | 95.9% (446/465; CI 93.7–97.4) | 2 | 0 | $0.15 | 0.64 s | not repeated |
| ai-rules (LLM decides) | 91.8% (427/465; CI 89.0–94.0) | 0 | 14 | $4.16 | 1.23 s | not repeated on this corpus (6.6% flipped on mock_500) |

Under format shift (`shift_200`, 200 cases rewritten in formats the rules were not built for, labels unchanged):

| Arm | Correct (95% CI) | Wrong APPLY | Over-escalate | Failed | vs regex: only-regex vs only-arm; McNemar; paired Δ |
|---|---|---|---|---|---|
| regex (no LLM) | 32.0% (64/200; CI 25.9–38.8) | 0 | 45 | 0 | — |
| name-llm (optimised) | 32.0% (64/200; CI 25.9–38.8) | 0 | 45 | 0 | 0 vs 0; p = 1.000; Δ +0.0 pts (95% CI +0.0 to +0.0) |
| live = name-llm+explain | 32.0% (64/200; CI 25.9–38.8) | 0 | 45 | 0 | 0 vs 0; p = 1.000; Δ +0.0 pts (95% CI +0.0 to +0.0) |
| ai-rules (LLM decides) | 30.5% (61/200; CI 24.5–37.2) | 0 | 67 | 0 | 3 vs 0; p = 0.250; Δ -1.5 pts (95% CI -3.5 to +0.0) |
| parse-fallback (regex → LLM) | 33.0% (66/200; CI 26.9–39.8) | 0 | 45 | 0 | 0 vs 2; p = 0.500; Δ +1.0 pts (95% CI +0.0 to +2.5) |
| parse-llm (old LLM parser) | 23.0% (46/200; CI 17.7–29.3) | 0 | 45 | 0 | 18 vs 0; p = 0.000; Δ -9.0 pts (95% CI -13.0 to -5.5) |

Explanation call in isolation, name-llm → live: 0 vs 0; p = 1.000; Δ +0.0 pts (95% CI +0.0 to +0.0)

"Optimised ≥ LLM decides": name-llm vs ai-rules: 0 vs 3; p = 0.250; Δ +1.5 pts (95% CI +0.0 to +3.5)  (Δ is name-llm − ai-rules)

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

## Task 1: cost and time for every arm

What was measured: every live LLM call site is wrapped (`run_eval.py`, `_UsageClient`) and records prompt, completion and reasoning tokens and wall time per call; the AI-decider arms record the same. Main-pass usage only (the repeat pass for stability is excluded).

| Arm | Payments | LLM calls / payment | Failed calls | Prompt tok / payment | Completion tok / payment | **Cost per 1,000 payments** | Per-payment time p50 / p95 |
|---|---|---|---|---|---|---|---|
| regex (no LLM) | 549 | 0.00 | 0 | 0 | 0 | **$0.000** | 0.00 s / 0.01 s |
| name-llm (optimised) | 549 | 0.07 | 0 | 4 | 4 | **$0.010** | 0.01 s / 0.74 s |
| live = name-llm+explain | 549 | 1.07 | 0 | 179 | 135 | **$0.391** | 1.31 s / 2.00 s |
| parse-fallback (regex → LLM) | 549 | 0.27 | 0 | 24 | 12 | **$0.036** | 0.01 s / 0.78 s |
| parse-llm (old LLM parser) | 549 | 1.04 | 0 | 102 | 46 | **$0.145** | 0.63 s / 1.34 s |
| ai-tight (LLM decides) | 549 | 1.00 | 0 | 3,392 | 264 | **$1.678** | 1.56 s / 2.15 s |
| ai-rules (LLM decides) | 549 | 1.00 | 0 | 13,132 | 97 | **$4.183** | 1.19 s / 1.64 s |

Per call site ($ per 1,000 payments; latency is per LLM call):

| Arm | Call site | Calls | $ per 1,000 payments | Call latency p50 / p95 |
|---|---|---|---|---|
| name-llm | name_gray_zone | 37 | $0.010 | 0.75 s / 0.96 s |
| live | reasoning_text | 549 | $0.381 | 1.25 s / 1.72 s |
| live | name_gray_zone | 37 | $0.010 | 0.70 s / 0.96 s |
| parse-fallback | name_gray_zone | 37 | $0.010 | 0.69 s / 0.96 s |
| parse-fallback | reference_parse | 113 | $0.025 | 0.61 s / 0.89 s |
| parse-llm | reference_parse | 533 | $0.134 | 0.60 s / 0.85 s |
| parse-llm | name_gray_zone | 37 | $0.010 | 0.75 s / 0.98 s |
| ai-tight | ai_decider | 549 | $1.678 | 1.53 s / 2.17 s |
| ai-rules | ai_decider | 551 | $4.183 | 1.16 s / 1.61 s |

Is "thinking" really off? `reasoning_tokens` is what the usage object reports; the ratio compares completion tokens with the visible output (characters ÷ 3.5 as a token estimate). A reasoning count above 0, or a ratio far above ~1.5, would mean hidden tokens are being billed.

| Arm | Call site | Reasoning tokens reported | Completion tokens | Completion ÷ estimated visible tokens | Flag |
|---|---|---|---|---|---|
| name-llm | name_gray_zone | 0 | 2,034 | 1.00 | ok |
| live | reasoning_text | 0 | 72,158 | 0.90 | ok |
| live | name_gray_zone | 0 | 2,017 | 1.00 | ok |
| parse-fallback | name_gray_zone | 0 | 2,034 | 1.00 | ok |
| parse-fallback | reference_parse | 0 | 4,294 | 1.32 | ok |
| parse-llm | reference_parse | 0 | 23,047 | 1.42 | ok |
| parse-llm | name_gray_zone | 0 | 2,039 | 1.00 | ok |
| ai-tight | ai_decider | 0 | 144,922 | 1.21 | ok |
| ai-rules | ai_decider | 0 | 53,460 | 0.94 | ok |

Price: $0.30 per million input tokens, $2.50 per million output tokens (google/gemini-2.5-flash, OpenRouter, verified 2026-09-26).

Result: the whole LLM cost of the optimised configuration is the name call (about a cent per 1,000 payments). The **explanation call is the expensive one**: it is nearly all of the `live` arm's cost and about 1.3 s of its median time, for text that cannot change a decision. Letting an LLM decide costs about 10× the `live` arm and about 400× the optimised arm (and $4.18 against $0 for the code), and adds a second or more per payment. The old production parser made **two** calls per payment (at ingest and again in the pipeline); the `parse-llm` row counts one, so double it for the old system. Thinking is off: no call reported reasoning tokens and completion tokens track the visible output.

Same table on the second corpus (`fresh500`):

| Arm | Payments | LLM calls / payment | Failed calls | Prompt tok / payment | Completion tok / payment | **Cost per 1,000 payments** | Per-payment time p50 / p95 |
|---|---|---|---|---|---|---|---|
| regex (no LLM) | 549 | 0.00 | 0 | 0 | 0 | **$0.000** | 0.00 s / 0.01 s |
| name-llm (optimised) | 549 | 0.07 | 0 | 4 | 4 | **$0.011** | 0.01 s / 0.80 s |
| live = name-llm+explain | 549 | 1.05 | 10 | 176 | 133 | **$0.385** | 1.33 s / 2.18 s |
| parse-fallback (regex → LLM) | 549 | 0.29 | 0 | 25 | 12 | **$0.038** | 0.01 s / 0.76 s |
| parse-llm (old LLM parser) | 549 | 1.05 | 0 | 103 | 46 | **$0.147** | 0.64 s / 1.40 s |
| ai-rules (LLM decides) | 549 | 1.00 | 2 | 13,062 | 97 | **$4.160** | 1.23 s / 1.74 s |

Caveat: LLM calls fail occasionally (10 of the `live` arm's reasoning calls on `fresh500` timed out and used the template; 2 AI decisions failed and were counted as ESCALATE).

## Task 2: the optimised configuration as its own arm

`name-llm` = regex reference parser + LLM only for gray-zone names + template explanations. `name-llm+explain` = the same with the live LLM explanation call; on today's code this is identical to `live`, so it is run once and reported under both names, and the explanation is priced separately by subtraction.

**`full.json`** (192 cases, 179 valid)

| Arm | Correct (95% CI) | Wrong APPLY | Over-escalate | Failed | vs regex: only-regex vs only-arm; McNemar; paired Δ |
|---|---|---|---|---|---|
| regex (no LLM) | 100.0% (179/179; CI 97.9–100.0) | 0 | 0 | 0 | — |
| name-llm (optimised) | 100.0% (179/179; CI 97.9–100.0) | 0 | 0 | 0 | 0 vs 0; p = 1.000; Δ +0.0 pts (95% CI +0.0 to +0.0) |
| live = name-llm+explain | 100.0% (179/179; CI 97.9–100.0) | 0 | 0 | 0 | 0 vs 0; p = 1.000; Δ +0.0 pts (95% CI +0.0 to +0.0) |

Explanation call in isolation, name-llm → live: 0 vs 0; p = 1.000; Δ +0.0 pts (95% CI +0.0 to +0.0)

**`heldout.json`** (193 cases, 180 valid)

| Arm | Correct (95% CI) | Wrong APPLY | Over-escalate | Failed | vs regex: only-regex vs only-arm; McNemar; paired Δ |
|---|---|---|---|---|---|
| regex (no LLM) | 100.0% (180/180; CI 97.9–100.0) | 0 | 0 | 0 | — |
| name-llm (optimised) | 100.0% (180/180; CI 97.9–100.0) | 0 | 0 | 0 | 0 vs 0; p = 1.000; Δ +0.0 pts (95% CI +0.0 to +0.0) |
| live = name-llm+explain | 100.0% (180/180; CI 97.9–100.0) | 0 | 0 | 0 | 0 vs 0; p = 1.000; Δ +0.0 pts (95% CI +0.0 to +0.0) |

Explanation call in isolation, name-llm → live: 0 vs 0; p = 1.000; Δ +0.0 pts (95% CI +0.0 to +0.0)

**`mock_500.json`** (500 cases, 465 valid)

| Arm | Correct (95% CI) | Wrong APPLY | Over-escalate | Failed | vs regex: only-regex vs only-arm; McNemar; paired Δ |
|---|---|---|---|---|---|
| regex (no LLM) | 100.0% (465/465; CI 99.2–100.0) | 0 | 0 | 0 | — |
| name-llm (optimised) | 100.0% (465/465; CI 99.2–100.0) | 0 | 0 | 0 | 0 vs 0; p = 1.000; Δ +0.0 pts (95% CI +0.0 to +0.0) |
| live = name-llm+explain | 100.0% (465/465; CI 99.2–100.0) | 0 | 0 | 0 | 0 vs 0; p = 1.000; Δ +0.0 pts (95% CI +0.0 to +0.0) |

Explanation call in isolation, name-llm → live: 0 vs 0; p = 1.000; Δ +0.0 pts (95% CI +0.0 to +0.0)

Result: on every corpus the three arms are **identical on the scored labels** (0 discordant cases, McNemar p = 1.0). The explanation call and the name call therefore add **no measurable accuracy** here. The name LLM is asked on 81 of 1585 payments (5.1%) and changes the recommendation on 76. On the 86 `S1-hold-name` payments (label: HOLD; excluded from every accuracy figure above because the 75–90 band cannot be validated independently), the regex arm recommends HOLD 74 times and APPLY 2; the name-llm arm recommends HOLD 2 times and APPLY 74. (The other 10 escalate in both arms.)

What that means: the name LLM does act, but only on nickname and typo pairs (`Dan Lovato`/`Daniel Lovato`, `Galo Pasra`/`Galo Parsa`), and every time it converts HOLD into APPLY. By the spec's labels that is wrong; by the spec's own hybrid design (final score = max(deterministic, LLM), APPLY above 90) it is intended. Which is right is a business question these labels cannot settle, and the corpus has no *different-person* pair in the gray zone, so the LLM's false-match rate is **unmeasured**. It answered exactly 95 for all 21 distinct pairs it lifted.

## Task 3: does "rules / optimised ≥ LLM decides" hold at n = 465?

Arms on `mock_500` (465 valid-label cases). Paired columns give the discordant counts (cases only one arm gets right), the exact McNemar p and a paired-bootstrap 95% interval for the accuracy difference.

**`mock_500.json`**

| Arm | Correct (95% CI) | Wrong APPLY | Over-escalate | Failed | vs regex: only-regex vs only-arm; McNemar; paired Δ |
|---|---|---|---|---|---|
| regex (no LLM) | 100.0% (465/465; CI 99.2–100.0) | 0 | 0 | 0 | — |
| name-llm (optimised) | 100.0% (465/465; CI 99.2–100.0) | 0 | 0 | 0 | 0 vs 0; p = 1.000; Δ +0.0 pts (95% CI +0.0 to +0.0) |
| live = name-llm+explain | 100.0% (465/465; CI 99.2–100.0) | 0 | 0 | 0 | 0 vs 0; p = 1.000; Δ +0.0 pts (95% CI +0.0 to +0.0) |
| ai-rules (LLM decides) | 94.2% (438/465; CI 91.7–96.0) | 0 | 10 | 0 | 27 vs 0; p = 0.000; Δ -5.8 pts (95% CI -8.0 to -3.9) |
| ai-tight (LLM decides) | 81.9% (381/465; CI 78.2–85.2) | 1 | 70 | 0 | 84 vs 0; p = 0.000; Δ -18.1 pts (95% CI -21.7 to -14.8) |
| parse-fallback (regex → LLM) | 100.0% (465/465; CI 99.2–100.0) | 0 | 0 | 0 | 0 vs 0; p = 1.000; Δ +0.0 pts (95% CI +0.0 to +0.0) |
| parse-llm (old LLM parser) | 98.1% (456/465; CI 96.4–99.0) | 0 | 0 | 0 | 9 vs 0; p = 0.004; Δ -1.9 pts (95% CI -3.2 to -0.9) |

Explanation call in isolation, name-llm → live: 0 vs 0; p = 1.000; Δ +0.0 pts (95% CI +0.0 to +0.0)

"Optimised ≥ LLM decides": name-llm vs ai-rules: 0 vs 27; p = 0.000; Δ +5.8 pts (95% CI +3.9 to +8.0)  (Δ is name-llm − ai-rules)

**`fresh_500_seed7.json`** (unseen seed)

| Arm | Correct (95% CI) | Wrong APPLY | Over-escalate | Failed | vs regex: only-regex vs only-arm; McNemar; paired Δ |
|---|---|---|---|---|---|
| regex (no LLM) | 100.0% (465/465; CI 99.2–100.0) | 0 | 0 | 0 | — |
| name-llm (optimised) | 100.0% (465/465; CI 99.2–100.0) | 0 | 0 | 0 | 0 vs 0; p = 1.000; Δ +0.0 pts (95% CI +0.0 to +0.0) |
| live = name-llm+explain | 100.0% (465/465; CI 99.2–100.0) | 0 | 0 | 0 | 0 vs 0; p = 1.000; Δ +0.0 pts (95% CI +0.0 to +0.0) |
| ai-rules (LLM decides) | 91.8% (427/465; CI 89.0–94.0) | 0 | 14 | 0 | 38 vs 0; p = 0.000; Δ -8.2 pts (95% CI -10.8 to -5.8) |
| parse-fallback (regex → LLM) | 100.0% (465/465; CI 99.2–100.0) | 0 | 0 | 0 | 0 vs 0; p = 1.000; Δ +0.0 pts (95% CI +0.0 to +0.0) |
| parse-llm (old LLM parser) | 95.9% (446/465; CI 93.7–97.4) | 2 | 0 | 0 | 19 vs 0; p = 0.000; Δ -4.1 pts (95% CI -6.0 to -2.4) |

Explanation call in isolation, name-llm → live: 0 vs 0; p = 1.000; Δ +0.0 pts (95% CI +0.0 to +0.0)

"Optimised ≥ LLM decides": name-llm vs ai-rules: 0 vs 38; p = 0.000; Δ +8.2 pts (95% CI +5.8 to +10.8)  (Δ is name-llm − ai-rules)

Result: yes, and by a margin that is not noise. On `mock_500` the optimised arm beats the LLM-decides arm by 5.8 points (27 cases only the rules get right, 0 the other way, p < 0.001); on the unseen-seed corpus by 8.2 points (38 vs 0). The per-scenario checklist prompt (`ai-tight`) is worse still (81.9%): 83 of its 84 errors are Scenario 2 payments (70 escalated, 13 held) where the variance signal is null and the checklist made the model read "variance ≤ 15%" literally as false. Caveat: the rules were built from this spec and these templates, so "rules ≥ LLM" here means "the rules faithfully implement the spec"; the LLM was given the spec verbatim and still misapplied it (Task 4).

## Task 4: error analysis by cause and arm

Every wrong case (scenario or recommendation not as labelled) is assigned one cause by the first matching rule (`classify()` in `ablation_analysis.py`). For the AI-decider arms the cause is refined with what the model itself wrote.

**`mock_500.json`**

| Cause | regex | name-llm | live | ai-rules | ai-tight | parse-fallback | parse-llm |
|---|---|---|---|---|---|---|---|
| reference not parsed | · | · | · | · | · | · | 9 |
| wrong APPLY (unsafe) | · | · | · | · | 1 | · | · |
| third-party payer mishandled | · | · | · | 10 | · | · | · |
| second-policy payment held/escalated | · | · | · | 5 | · | · | · |
| S2 (no policy ref) escalated | · | · | · | · | 70 | · | · |
| S2 (no policy ref) held instead of applied | · | · | · | · | 13 | · | · |
| held although every APPLY condition was met | · | · | · | 12 | · | · | · |
| **total wrong** | **0** | **0** | **0** | **27** | **84** | **0** | **9** |

Causes are assigned by the first matching rule, in the order listed (a case with an unparsed reference is counted there even if it also looks like a second-policy case). Rules: `classify()` in ablation_analysis.py. "Second-policy" also catches any hold whose model-written reasoning cites a second policy / same premium.

Why ai-rules held 12 payments that met every APPLY condition (the model's own stated reason):

- 6 × added a condition not in the spec (balance / timing / under-payment)
- 3 × misread 'human approval is always required' as a reason to hold
- 3 × mis-tiered a variance already inside the 2% tolerance

**`fresh_500_seed7.json`**

| Cause | regex | name-llm | live | ai-rules | parse-fallback | parse-llm |
|---|---|---|---|---|---|---|
| reference not parsed | · | · | · | · | · | 19 |
| third-party payer mishandled | · | · | · | 12 | · | · |
| second-policy payment held/escalated | · | · | · | 6 | · | · |
| S2 (no policy ref) escalated | · | · | · | 2 | · | · |
| S2 (no policy ref) held instead of applied | · | · | · | 5 | · | · |
| held although every APPLY condition was met | · | · | · | 13 | · | · |
| **total wrong** | **0** | **0** | **0** | **38** | **0** | **19** |

Causes are assigned by the first matching rule, in the order listed (a case with an unparsed reference is counted there even if it also looks like a second-policy case). Rules: `classify()` in ablation_analysis.py. "Second-policy" also catches any hold whose model-written reasoning cites a second policy / same premium.

Why ai-rules held 13 payments that met every APPLY condition (the model's own stated reason):

- 8 × misread 'human approval is always required' as a reason to hold
- 3 × added a condition not in the spec (balance / timing / under-payment)
- 2 × other reason

**`shift_200.json`** (rule-based arms lose their points here)

| Cause | regex | name-llm | live | ai-rules | parse-fallback | parse-llm |
|---|---|---|---|---|---|---|
| reference not parsed | 76 | 76 | 76 | 76 | 74 | 94 |
| name in an unseen format (surname first / caps) | 60 | 60 | 60 | 60 | 60 | 60 |
| third-party payer mishandled | · | · | · | 1 | · | · |
| held although every APPLY condition was met | · | · | · | 2 | · | · |
| **total wrong** | **136** | **136** | **136** | **139** | **134** | **154** |

Causes are assigned by the first matching rule, in the order listed (a case with an unparsed reference is counted there even if it also looks like a second-policy case). Rules: `classify()` in ablation_analysis.py. "Second-policy" also catches any hold whose model-written reasoning cites a second policy / same premium.

Why ai-rules held 2 payments that met every APPLY condition (the model's own stated reason):

- 2 × added a condition not in the spec (balance / timing / under-payment)

Result: the LLM-decides arm fails in three characteristic ways on both corpora: it escalates or holds **third-party payers** the spec says to HOLD, it holds payments that name a policy because the customer has a **second policy with the same premium**, and it holds clean Scenario 1 payments by **adding conditions that are not in the spec** (it misread "human approval is always required" as a reason to hold, invented balance and timing conditions, and mis-tiered a variance of 0.85% as "Tier 2 (2–15%)"). The rule-based arms have no errors in distribution; under format shift **all** of their errors come from two causes, an unparsed reference and a surname-first name (Task 7).

## Task 5: consistency (run-to-run stability)

Share of cases whose **recommendation** changed between two runs of the same arm on the same cases:

| Arm / corpus | Cases | Recommendation flipped | Wrong-in-one-run-only |
|---|---|---|---|
| ai-rules, full.json (2026-09-25 runs, before the code fixes) | 192 | 10 = 5.2% (CI 2.9–9.3) | 10 |
| ai-tight, full.json (2026-09-25 runs, before the code fixes) | 192 | 7 = 3.6% (CI 1.8–7.3) | 3 |
| ai-rules, mock_500.json (this study) | 500 | 33 = 6.6% (CI 4.7–9.1) | 33 |

Gray-zone name score in the live LLM arms (each gray-zone case is scored twice: `--repeat-gray 1`):

| Arm / corpus | Gray-zone cases | LLM score differed | Recommendation differed | Max score spread |
|---|---|---|---|---|
| live, mock500 | 37 | 0 (0%) | 0 (0%) | 0 |
| live, full | 3 | 0 (0%) | 0 (0%) | 0 |
| live, heldout | 2 | 0 (0%) | 0 (0%) | 0 |
| live, fresh500 | 39 | 0 (0%) | 0 (0%) | 0 |
| name-llm, mock500 | 37 | 1 (3%) | 1 (3%) | 10 |
| name-llm, full | 3 | 0 (0%) | 0 (0%) | 0 |
| name-llm, heldout | 2 | 0 (0%) | 0 (0%) | 0 |
| name-llm, fresh500 | 39 | 0 (0%) | 0 (0%) | 0 |

The regex arm and the code's decision logic are deterministic: the same input gives the same output (checked below by running the regex arm twice).

Accuracy of `ai-rules` on `mock_500`: run 1 = 94.2%, run 2 = 93.1% (paired p = 0.49, i.e. the same accuracy). Of the 46 cases that were wrong in at least one run, 13 were wrong in both and 33 (72%) in only one, so most of the LLM's errors are not repeatable. The regex arm was run twice on `mock_500`: **0 of 500** cases differ in any of scenario, recommendation, decision path, confidence, name score, extracted policy, matched customer or matched policy (`data/abl_regex_mock500_run2.json`). The gray-zone name call now sets `temperature=0` (commit `989befb`): its score changed in 1 of 81 gray-zone cases in the `name-llm` arm and in 0 of 81 in `live`, against about 6% before the change (measured on a different case set, so not a controlled before/after).

## Task 6: are the LLM's explanations faithful?

What was measured: for every explanation the live arm wrote (1,801 across five corpora, main pass, including the prior payment of duplicate cases), every number, percentage, dollar amount and policy / customer / payment ID was extracted and checked against (a) the facts the model was given and (b) the case's own inputs and signals. Categorical claims about risk flags, third-party, multi-period and multi-method were checked against the flags the prompt stated. A separate check compares any confident claim of under- or over-payment with the actual payment and premium. Finally 40 explanations (seeded, 8 per scenario) were read by hand.

| Corpus | Explanations checked | Facts extracted (numbers, %, $, IDs) | ≥1 unsupported fact (95% CI) | …of which invented | only threshold-type | Flag claims checked | Flag claims that contradict the prompt (explanations) |
|---|---|---|---|---|---|---|---|
| mock500 | 549 (LLM call failed: 0) | 1442 | 0 = 0.0% (CI -0.0–0.7) | 0 | 0 | 502 | 3 (3) |
| full | 246 (LLM call failed: 0) | 754 | 2 = 0.8% (CI 0.2–2.9) | 2 | 0 | 195 | 0 (0) |
| heldout | 246 (LLM call failed: 0) | 773 | 0 = 0.0% (CI 0.0–1.5) | 0 | 0 | 193 | 2 (2) |
| fresh500 | 539 (LLM call failed: 10) | 1388 | 1 = 0.2% (CI 0.0–1.0) | 1 | 0 | 490 | 0 (0) |
| shift200 | 221 (LLM call failed: 0) | 411 | 0 = 0.0% (CI 0.0–1.7) | 0 | 0 | 79 | 0 (0) |
| **all** | 1801 (LLM call failed: 10) | 4768 | 3 = 0.2% (CI 0.1–0.5) | 3 | 0 | 1459 | 5 (5) |

Direction of variance (scenarios 1-3; the prompt gives only the absolute variance, so under/over is a guess): 18 explanations assert under- or over-payment, 2 contradict the case (11.1%).
  - mock500/S3-tier4-0128~ref_noise: text says underpayment, actual overpayment — “The payment amount has a significant 65.0% variance from the expected amount, suggesting underpayment. The payment is not for multiple periods, nor does it involve multiple payment methods, simplifyin”
  - fresh500/S1-apply-a-0794: text says overpayment, actual underpayment — “Sender and policyholder names are an exact match, indicating the correct recipient. The policy reference 'POL-12059' is explicitly provided. The amount variance is minimal (1.0%), suggesting a minor r”

Facts supported only by the case (true, but not shown to the model): 0.

Unsupported facts by type: invented/number = 3

**Manual review of 40 explanations** (reviewer: Claude, not a person; first pass):

| Label | Count of 40 | Meaning |
|---|---|---|
| Clean | 16 (40%) | every statement traces to the prompt |
| Minor overreach | 17 (42.5%) | inference or overstatement that is not checkably false ("first-time transaction", "exact match" for a name that differs by an initial) |
| External claim | 5 (12.5%) | domain facts not in the input ("ACH offers less recourse than credit card", "Wire often requires manual reconciliation") |
| **Wrong** | **2 (5%; CI 1.4–16.5)** | item 24 says "suggesting underpayment" for a payment that was an **overpayment** ($505.04 against a $306.00 premium); item 27 says "Unidentified payment method: ACH" |

Result: the explanations almost never invent a number or ID (3 of 1,801 flagged automatically; on reading, two were one real fabrication, an invented "24-hour look-back period" for a duplicate found at 30 hours when the window is 72 hours, and one was correct rounding), and none contradicted a stated flag (all automated flag warnings were false positives on reading). But the model **guesses what the prompt does not say**: the prompt gives only the absolute variance, and of the 18 explanations that confidently state under- or over-payment 2 (11%) are wrong. In the hand-read sample 17.5% (7/40; CI 8.7–32.0) contained a claim the input does not support (external or wrong). Caveats: the numeric checker cannot see wrongly *reasoned* claims (the manual sample can, at n = 40 and with one non-independent reviewer); an explanation cannot change the decision, but an analyst reading a wrong direction could be misled.

## Task 7: robustness to format shift

`shift_200.json` (built by `build_shift.py`, seed 20260926) takes 200 cases from `mock_500` and rewrites each in one format the rules were not built for; labels are unchanged. Reference formats `Policy: 12345` (T1), `PN12345` (T2), `ref#12345/INS` (T3), bare `12345` (T4); names `Khan, Aisha` (T5) and `KHAN AISHA` (T6); a currency amount in the memo (T7). For duplicate cases the same format is applied to the prior payment. The regex was written before these formats were chosen; T1 and T7 happen to be covered by it, T2-T4 are not.

Each arm is compared with **itself on the same 200 cases before the rewrite** (paired by case), so the change is purely the format.

| Arm | Before rewrite | After rewrite | Change | Only-before-correct vs only-after-correct; McNemar |
|---|---|---|---|---|
| regex (no LLM) | 100.0% (200/200; CI 98.1–100.0) | 32.0% (64/200; CI 25.9–38.8) | **-68.0 pts** | 136 vs 0; p = 0.0000 |
| name-llm (optimised) | 100.0% (200/200; CI 98.1–100.0) | 32.0% (64/200; CI 25.9–38.8) | **-68.0 pts** | 136 vs 0; p = 0.0000 |
| live = name-llm+explain | 100.0% (200/200; CI 98.1–100.0) | 32.0% (64/200; CI 25.9–38.8) | **-68.0 pts** | 136 vs 0; p = 0.0000 |
| parse-fallback (regex → LLM) | 100.0% (200/200; CI 98.1–100.0) | 33.0% (66/200; CI 26.9–39.8) | **-67.0 pts** | 134 vs 0; p = 0.0000 |
| parse-llm (old LLM parser) | 100.0% (200/200; CI 98.1–100.0) | 23.0% (46/200; CI 17.7–29.3) | **-77.0 pts** | 154 vs 0; p = 0.0000 |
| ai-rules (LLM decides) | 92.5% (185/200; CI 88.0–95.4) | 30.5% (61/200; CI 24.5–37.2) | **-62.0 pts** | 124 vs 0; p = 0.0000 |

Accuracy after the rewrite, by transformation (correct / cases):

| Transformation | Cases | regex | name-llm | live | parse-fallback | parse-llm | ai-rules |
|---|---|---|---|---|---|---|---|
| T1 `Policy: 12345` | 30 | 30/30 | 30/30 | 30/30 | 30/30 | 12/30 | 28/30 |
| T2 `PN12345` | 30 | 2/30 | 2/30 | 2/30 | 3/30 | 2/30 | 2/30 |
| T3 `ref#12345/INS` | 30 | 5/30 | 5/30 | 5/30 | 5/30 | 5/30 | 5/30 |
| T4 `12345` alone | 30 | 7/30 | 7/30 | 7/30 | 8/30 | 7/30 | 7/30 |
| T5 name `Khan, Aisha` | 30 | 0/30 | 0/30 | 0/30 | 0/30 | 0/30 | 0/30 |
| T6 name `KHAN AISHA` | 30 | 0/30 | 0/30 | 0/30 | 0/30 | 0/30 | 0/30 |
| T7 amount with $ in memo | 20 | 20/20 | 20/20 | 20/20 | 20/20 | 20/20 | 19/20 |

Policy-number extraction after the rewrite (ingest-time parse equals the un-shifted reference):

| Arm | Extracted correctly (of cases with a policy reference) |
|---|---|
| regex (no LLM) | 43.4% (69/159; CI 35.9–51.2) |
| name-llm (optimised) | 43.4% (69/159; CI 35.9–51.2) |
| live = name-llm+explain | 43.4% (69/159; CI 35.9–51.2) |
| parse-fallback (regex → LLM) | 44.7% (71/159; CI 37.1–52.4) |
| parse-llm (old LLM parser) | 31.4% (50/159; CI 24.7–39.0) |
| ai-rules (LLM decides) | 43.4% (69/159; CI 35.9–51.2) |

Result: **every arm collapses under format shift**: the rule-based arms lose 68 points (100% → 32%), the LLM-decides arm 62 (92.5% → 30.5%) and the old LLM parser 77 (100% → 23%). All of the rule-based arms' errors have two causes: 76 unparsed references (T2-T4) and 60 surname-first names (T5, T6: 0 of 60 correct). The LLM is **not** a fix with today's prompts: the LLM-fallback arm (regex first, then the LLM) recovers only 2 more of the 159 policy references; a direct probe shows why, since the production parse prompt asks for "a string matching pattern POL-XXXXX, or null", so the model returns `null` for `PN12731`, `ref#10344/INS`, a bare `13102`, and even `Policy: 13186` (8 probes, `legacy_parser.llm_parse`). A prompt written for these formats might do better; designing it against this set would be tuning on the test set, so that work needs a second shift set. The hybrid name scorer cannot rescue T5/T6 either: a surname-first name scores below the gray-zone floor of 70, so the LLM is never asked.

Caveats: T1 and T7 are covered by design, so −68 points measures how far outside its coverage the regex falls, not how often such formats occur in real data (unknown). The shift set derives from `mock_500`, whose cases the rules were fitted to.

## Task 8: confidence calibration

In distribution (`mock_500` + `fresh_500`), where the rule-based arms are correct everywhere:

Pooled over mock500, fresh500; accuracy = scenario and recommendation both correct. `confidence` is the score stored with the recommendation.

| Arm | conf < 70 | conf 70–80 | conf 80–90 | conf 90+ |
|---|---|---|---|---|
| regex (no LLM) | 100.0% (341/341; CI 98.9–100.0) | 100.0% (33/33; CI 89.6–100.0) | 100.0% (179/179; CI 97.9–100.0) | 100.0% (377/377; CI 99.0–100.0) |
| live = name-llm+explain | 100.0% (340/340; CI 98.9–100.0) | 100.0% (30/30; CI 88.6–100.0) | 100.0% (180/180; CI 97.9–100.0) | 100.0% (380/380; CI 99.0–100.0) |
| ai-rules (LLM decides) | 87.6% (190/217; CI 82.5–91.3) | 94.1% (160/170; CI 89.5–96.8) | 91.3% (168/184; CI 86.3–94.6) | 96.7% (347/359; CI 94.2–98.1) |

- regex: 19 distinct confidence values
- live: 16 distinct confidence values
- ai-rules: 13 distinct confidence values

For the code arms the confidence is a constant per decision path, not a probability: a bucket's accuracy says how reliable that group of paths is, not that the score is calibrated. `live` uses the same code confidence as `regex` (the LLM writes only the explanation).

Under format shift, where they are wrong two times in three:

Pooled over shift200; accuracy = scenario and recommendation both correct. `confidence` is the score stored with the recommendation.

| Arm | conf < 70 | conf 70–80 | conf 80–90 | conf 90+ |
|---|---|---|---|---|
| regex (no LLM) | 34.6% (36/104; CI 26.2–44.2) | 4.0% (1/25; CI 0.7–19.5) | 13.7% (7/51; CI 6.8–25.7) | 100.0% (20/20; CI 83.9–100.0) |
| live = name-llm+explain | 34.6% (36/104; CI 26.2–44.2) | 4.0% (1/25; CI 0.7–19.5) | 13.7% (7/51; CI 6.8–25.7) | 100.0% (20/20; CI 83.9–100.0) |
| ai-rules (LLM decides) | 23.6% (21/89; CI 16.0–33.4) | 34.9% (15/43; CI 22.4–49.8) | 13.3% (6/45; CI 6.3–26.2) | 82.6% (19/23; CI 62.9–93.0) |

- regex: 11 distinct confidence values (e.g. [0.0, 10.0, 20.0, 50.0, 60.0, 65.0])
- live: 11 distinct confidence values (e.g. [0.0, 10.0, 20.0, 50.0, 60.0, 65.0])
- ai-rules: 10 distinct confidence values (e.g. [0.0, 33.0, 40.0, 60.0, 70.0, 75.0])

For the code arms the confidence is a constant per decision path, not a probability: a bucket's accuracy says how reliable that group of paths is, not that the score is calibrated. `live` uses the same code confidence as `regex` (the LLM writes only the explanation).

Result: in distribution the bucket table is uninformative because there is nothing to separate. Under shift the code's confidence is **informative**: answers at confidence 90+ were right 20 of 20 times, while every wrong answer sits below 90, so the stored confidence does drop when the input is unfamiliar and could be used to rank the review queue. The LLM-decides arm's self-reported confidence is only weakly related to correctness (87.6% correct below 70, 96.7% at 90+, non-monotonic in between). Caveat: the code's confidence is a constant per decision path (16-19 distinct values), not a probability, and in `live` it depends on the name score, so it differs slightly from `regex`.

## Task 9: ship the regex parser (not run: needs your confirmation)

You asked for this only on confirmation, so **no application code was changed** for these experiments (`backend/app` is byte-identical to commit `a45ca38`; every result file records `app_dirty: false`).

Two things differ from the plan as written, and you should decide on both:

- **Most of it already shipped in commit `989befb`** (on `origin/nalin-dev`): the LLM reference parser was replaced by a regex, the ingest parse is passed to the pipeline (parsed once; passed, not persisted), and the gray-zone name call sets `temperature=0`. It shipped **without** an LLM fallback.
- **The evidence in this study does not support adding the fallback as designed.** With the production prompt the fallback recovers 2 of 159 shifted references (44.7% vs 43.4% extraction) for about $0.025 per 1,000 payments (the fallback's calls; the arm's $0.036 total includes the name call) and one extra LLM call on 27% of payments. It would only be worth having with a prompt written and validated on a *second* shift set.

Still open from your list if you confirm: adding the fallback; persisting the parse; `temperature=0` on the reasoning call; and the stale "Claude Haiku" docstring on `_llm_score` in `matching.py`.

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
