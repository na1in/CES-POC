# Stage 2: Compute Signals (Context & Knowledge Layer)

**Purpose:** Compute all 19 analytical signals about a payment using customer, policy, and payment history data. Snapshot the results for auditability.

---

## Overview

Before the AI can make a decision, we need to gather "facts" about the payment. These facts are called **signals** — numerical scores, boolean flags, and classifications that describe:
- How well does this payment match a known customer/policy?
- Does the amount make sense?
- Is the timing normal?
- Are there any red flags?
- Have we seen this payment before?

Signals are organized into **5 categories** with **19 total signals**, computed in **3 waves** (because some depend on others).

---

## Signal Categories

### Category 1: Matching & Identification

| Signal | Range | Method |
|--------|-------|--------|
| Name Similarity Score | 0-100% | Hybrid approach (see below) |
| Policy Match Confidence | 0-100% | Direct match = 100%, fuzzy = 70-95%, indirect = 60-80% |
| Customer Match Confidence | 0-100% | Exact name = 100%, fuzzy < 100% |
| Supporting Signals | 0-3 booleans | account_match, amount_match, historical_match |

### Category 2: Amount & Variance

| Signal | Range | Method |
|--------|-------|--------|
| Amount Variance % | 0-∞% | `abs(payment - expected) / expected * 100` |
| Overpayment/Underpayment | Enum + cents | OVER / UNDER / WITHIN_TOLERANCE + difference |
| Multi-Period Indicator | Boolean + count | `round(payment / expected)`, check within 5% of multiple |
| Multi-Method Indicator | Boolean + fraction | `payment / expected` ≈ 1/N for N in [2,3,4] — split premium across banks |
| Third-Party Indicator | Boolean + relationship | Sender ≠ policyholder — corporate, family, escrow, trust, POA |
| Historical Consistency | Score | Mean/stddev of last 6-12 payments, z-score outlier detection |

### Category 3: Temporal & Pattern

| Signal | Range | Method |
|--------|-------|--------|
| Payment Timing Quality | Enum | Days from due: EXCELLENT (<=7), GOOD (<=14), ACCEPTABLE (<=30), POOR |
| Days Since Last Payment | Integer | Simple date difference |

### Category 4: Risk & Fraud

| Signal | Range | Method |
|--------|-------|--------|
| Risk Flags | Boolean + list | Check fraud_history, suspended_account, chronic_late_payments |
| Account Status | Enum | ACTIVE / INACTIVE / CLOSED / PENDING |
| Outstanding Balance | Cents + status | `total_due - total_applied`, CURRENT or PAST_DUE |
| Payment Method Risk Level | Enum | Low (ACH, Card), Medium (Check, Wire), High (Unknown) |

### Category 5: Duplicate Detection

| Signal | Range | Method |
|--------|-------|--------|
| Duplicate Match | 0% or 100% | 3 exact fields (sender, method, reference) + amount within $2, within 72hr |
| Time Between Payments | Hours | Hours since matching previous payment |
| Balance Justification | Boolean | Does outstanding balance justify a second payment? |
| Duplicate Amount Difference | Cents | Absolute difference between this and suspected duplicate (0 = exact) |

---

## Computation Waves

Signals have dependencies. They must be computed in order:

### Wave 1 — Independent (run in parallel)

These need only the payment data + direct database lookups:

| Signal | What It Computes |
|--------|-----------------|
| Name Similarity | "John A Smith" vs "John Smith" → 92% |
| Amount Variance | $5,000 payment vs $5,000 expected → 0% |
| Timing Quality | Due date 3 days ago → EXCELLENT |
| Duplicate Check | Any matching payment in 72hrs (3 exact + $2 amount tolerance)? → No |
| Payment Method Risk Level | ACH → Low, Check → Medium, Unknown → High |

### Wave 2 — Depends on Wave 1

| Signal | Why It Needs Wave 1 |
|--------|-------------------|
| Policy Match Confidence | Needs parsed policy # (from Ingest) to look up |
| Customer Match Confidence | Uses name similarity score from Wave 1 |
| Over/Underpayment | Uses amount variance from Wave 1 |
| Historical Consistency | Needs confirmed policy match to find payment history |

### Wave 3 — Depends on Wave 2

| Signal | Why It Needs Wave 2 |
|--------|-------------------|
| Risk Flags | Needs confirmed customer ID from Wave 2 |
| Outstanding Balance | Needs confirmed policy ID from Wave 2 |
| Supporting Signals | Aggregates boolean flags from Waves 1 + 2 |
| Multi-Period Indicator | Needs confirmed premium amount from Wave 2 |
| Multi-Method Indicator | Needs confirmed premium amount from Wave 2 |
| Third-Party Indicator | Needs confirmed customer ID from Wave 2 |
| Time Between Payments | Only computed if duplicate detected in Wave 1 |
| Duplicate Amount Difference | Only computed if duplicate detected in Wave 1 |

---

## Hybrid Name Matching

Name matching uses a two-step strategy combining fast deterministic algorithms with LLM intelligence for edge cases.

### Step 1: Traditional Score

Run Jaro-Winkler + Levenshtein + Soundex to produce a `deterministic_score`.

### Step 2: Gray Zone Check

```
If deterministic_score < 70%:
    → Clear mismatch. Use deterministic_score. No LLM call.

If deterministic_score > 92%:
    → Clear match. Use deterministic_score. No LLM call.

If deterministic_score is 70-92% (gray zone):
    → Call Claude Haiku with both names → llm_score
    → Final score = max(deterministic_score, llm_score)
    → Both scores are logged for auditability.
```

### Why Hybrid?

Traditional algorithms are character-level comparisons. They fail on semantic equivalences:

| Case | Traditional | Haiku LLM | Winner |
|------|------------|-----------|--------|
| "Bob Smith" vs "Robert Smith" | ~60% | ~95% | LLM |
| "Smith, John" vs "John Smith" | ~50% | ~99% | LLM |
| "Mohammed" vs "Muhammad" | ~85% | ~98% | LLM |
| "John Smith" vs "John Smith" | 100% | 100% | Same (no LLM call) |
| "John Smith" vs "Jane Doe" | ~30% | ~5% | Same (no LLM call) |

### Cost Optimization

Only gray-zone cases (estimated 15-20% of payments) trigger the LLM call. Clear matches and clear mismatches skip it entirely.

The gray zone boundaries (70% lower, 92% upper) are stored in `configuration_thresholds` and can be tuned at runtime.

---

## Snapshot Rule

After all 3 waves complete, all 19 signals are **persisted to the `payment_signals` table as a snapshot**. This is critical:

- Even if the customer's data changes tomorrow (new risk flag, policy cancelled, etc.), we have a permanent record of what the system saw when it made its decision.
- If an auditor asks "why was PMT-001 auto-applied?", we can show the exact signals that led to that recommendation.
- The snapshot uses the `PaymentSignals` proto with 5 nested sub-messages (MatchingSignals, AmountSignals, TemporalSignals, RiskSignals, DuplicateSignals).
- `MatchingSignals` includes the full algorithm breakdown: `jaro_winkler_score`, `levenshtein_score`, `soundex_match`, `deterministic_score`, `used_llm`, `llm_score`. This gives Damien (Investigator) complete algorithmic provenance when reviewing escalated cases.

An audit log entry is written: `SIGNALS_COMPUTED`.

---

## Thresholds

All threshold values used during computation are read from the `configuration_thresholds` table at runtime. **Never hardcoded.** This includes:

| Threshold | Default | Used For |
|-----------|---------|----------|
| `name_match_auto_apply` | 90% | Determines "clear match" boundary |
| `name_match_hold` | 75% | Determines "hold vs escalate" boundary |
| `name_gray_zone_lower` | 70% | Below this, skip LLM |
| `name_gray_zone_upper` | 92% | Above this, skip LLM |
| `amount_tolerance_auto` | 2% | Auto-approve variance |
| `duplicate_window_hours` | 72 | Duplicate detection time window |
| `duplicate_amount_tolerance_cents` | 200 | $2.00 — max amount difference for duplicate match |
| `multi_period_tolerance` | 5% | Multi-period payment detection |

---

## Backend Modules

| File | Responsibility |
|------|---------------|
| `backend/app/services/signal_engine.py` | Orchestrates the 3 waves in order |
| `backend/app/services/signals/matching.py` | Name similarity (hybrid), policy confidence, customer confidence |
| `backend/app/services/signals/amount.py` | Variance, multi-period, historical consistency |
| `backend/app/services/signals/temporal.py` | Timing quality, days since last payment |
| `backend/app/services/signals/risk.py` | Risk flags, account status, balance check |
| `backend/app/services/signals/duplicate.py` | 72hr duplicate detection |

---

## What Happens Next

All signals are computed and snapshotted. The payment now moves to the AI Agent (Stage 3) where the signals are used to route to a scenario and produce a recommendation.

See: [03_AI_Agent.md](./03_AI_Agent.md)

---

*End of Document*
