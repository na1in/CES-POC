# Stage 3: AI Agent (Decision Engine)

**Purpose:** Route the payment to the correct scenario using deterministic logic, then use Claude API to reason within that scenario and produce a structured recommendation.

---

## Overview

The AI Agent has two distinct sub-parts:

| Part | Method | Purpose |
|------|--------|---------|
| **Scenario Router** | Deterministic Python code (if/else) | Pick which scenario applies |
| **Scenario Reasoning** | Claude API (LLM) | Reason within the scenario, produce recommendation + explanations |

This separation is intentional. The router is your **safety net** — fully testable, auditable, and predictable. The AI adds intelligence **within** the guardrails the router sets.

---

## Part A: Scenario Router

Every payment goes through this exact flow. No LLM involved — pure if/else logic using the computed signals from Stage 2.

```
EVERY payment hits Scenario 5 first (duplicate check)
    │
    ├── Match on all 4 fields (amount within $2, sender/method/reference exact)
    │   within 72 hours?
    │     │
    │     YES + outstanding balance > 0  → HOLD  (may be legitimate catch-up)
    │     YES + outstanding balance = 0  → ESCALATE (likely true duplicate)
    │     │
    │     NO → not a duplicate, continue...
    │
    ├── Does the payment have a policy reference?
    │   AND name similarity >= 75%?
    │     │
    │     YES → Is amount variance <= 2%?
    │     │       YES → SCENARIO 1 (Strong Policy Match)
    │     │       NO  → SCENARIO 3 (High Amount Variance)
    │     │
    │     NO → continue...
    │
    └── Can we find the customer?
        (name similarity >= 90% OR name < 90% + 2 or more supporting signals)
          │
          YES → SCENARIO 2 (Customer Match, No Policy)
          NO  → SCENARIO 4 (No Matching Customer → ESCALATE)
```

### Worked Example

Payment: "John A Smith", POL-12345, $5,000

1. **Scenario 5**: No identical payment in last 72 hours → not a duplicate, continue
2. **Policy reference?** Yes (POL-12345). **Name >= 75%?** Yes (92%) → continue
3. **Variance <= 2%?** Yes (0%) → **Scenario 1**

---

## Part B: Scenario Reasoning (Claude API)

Once the router picks a scenario, Claude API receives the signals and applies that scenario's rules. Each scenario has its own decision paths:

---

### Scenario 1 — Strong Policy Match

**Entry:** Policy reference provided, name >= 75%, variance <= 2%.

| Path | Conditions | Action | Confidence | Approval? |
|------|-----------|--------|------------|-----------|
| Auto-Apply | Name > 90% + no risk flags + active policy + low risk method | **APPLY** | 90-100% | No |
| Hold (ambiguous name) | Name 75-90% | **HOLD** | 60-85% | Yes |
| Hold (risk) | Any risk flags present (regardless of name) | **HOLD** | 50-70% | Yes |
| Hold (method) | Payment method risk = High (unknown method) | **HOLD** | 50-70% | Yes |
| Reroute | Name < 75% (shouldn't happen — router filters this) | → Scenario 4 | — | — |

**Example output (auto-apply):**
```json
{
  "recommendation": "APPLY",
  "confidence_score": 95,
  "scenario_route": 1,
  "decision_path": "scenario_1_auto_apply",
  "requires_human_approval": false,
  "reasoning": [
    "Policy POL-12345 confirmed active with matching premium of $5,000",
    "Name similarity 92% exceeds auto-apply threshold of 90%",
    "Amount matches expected premium exactly (0% variance)",
    "No risk flags on customer account",
    "Payment timing is EXCELLENT (3 days from due date)"
  ],
  "suggested_action": "Apply to POL-12345"
}
```

---

### Scenario 2 — Customer Match, No Policy

**Entry:** No policy reference (or invalid), but customer match found (name similarity >= 90%, or name < 90% with 2+ supporting signals).

| Path | Conditions | Action | Confidence | Approval? |
|------|-----------|--------|------------|-----------|
| Single Policy | 1 active policy + variance <= 15% | **APPLY** | 80-90% | Yes (always) |
| Amount Disambiguates | Multiple policies, amount matches exactly 1 (within 2%) | **APPLY** | 75-85% | Yes |
| Ambiguous | Multiple policies, cannot disambiguate by amount | **HOLD** | 70-80% | Yes |
| High Variance | Variance > 15% | Reroute → Scenario 3 | — | — |

Note: Scenario 2 **always** requires human approval, even when recommending APPLY. The system couldn't match a policy reference directly, so a human confirms.

---

### Scenario 3 — High Amount Variance

**Entry:** Customer/policy match found but amount deviates beyond 2%.

**Prerequisite:** Name similarity must be >= 90%. If not → reroute to Scenario 4.

| Tier | Variance Range | Action | Approval? |
|------|---------------|--------|-----------|
| 1 | 0-2% | **APPLY** (same as Scenario 1) | No |
| 2 | 2-15% | **HOLD** for manual review | Yes |
| 3 | 15-50% | Check special cases first (see below) | Yes |
| 4 | 50-100% | Check special cases first (see below) | Yes |
| 5 | > 100% | **ESCALATE** (potential fraud) | Yes |

**Special case checks (for variance > 15%):** Before escalating, the system checks:

1. **Multi-period payment** — payment ≈ N x premium (prepayment for multiple periods)
2. **Multi-method payment** — payment ≈ premium / N (customer splitting across methods/banks). Common: $7,500 premium paid as $2,500 x 3 from different banks.
3. **Third-party payment** — sender differs from policyholder (family member, employer payroll, mortgage escrow company)

If any of these are detected and variance ≤ 50%, the payment is **HELD** instead of ESCALATED, with the detected pattern noted in reasoning.

---

### Scenario 4 — No Matching Customer

**Entry:** All matching attempts failed — no valid policy reference, no customer match.

**Before escalating, check for third-party payments:**

| Condition | Action | Confidence |
|-----------|--------|------------|
| Valid policy reference + amount matches (≤15%) + third-party pattern detected | **HOLD** | 40-60% |
| Valid policy reference + amount doesn't match | **ESCALATE** | 0% |
| No valid policy reference | **ESCALATE** | 0% |

Third-party patterns: corporate names (Corp/LLC/Payroll), shared last name with policyholder, mortgage escrow companies, historical third-party payers.

For all ESCALATE outcomes, the system still provides:
- Best fuzzy match found in the customer database (name + similarity %)
- Any policies with matching premium amounts
- Possible explanations (third-party payment, name change, new customer)

---

### Scenario 5 — Duplicate Payment

**Entry:** Runs first on every payment before any other scenario.

| Condition | Action | Approval? |
|-----------|--------|-----------|
| No match in 72hr window | Not a duplicate → route to Scenarios 1-4 | — |
| Match found + outstanding balance > 0 | **HOLD** (may be legitimate catch-up) | Yes |
| Match found + outstanding balance = 0 | **ESCALATE** (likely true duplicate) | Yes |

The duplicate check requires **exact match on 3 fields** (sender name, payment method, policy reference) and **amount within $2 tolerance**. The $2 tolerance accounts for bank processing fees, rounding differences, and small surcharges (e.g., $7,500 vs $7,499 vs $7,501). The amount difference is captured and reported in the reasoning.

---

## What Claude Actually Does

The decision tables above set the **boundaries**. Within those boundaries, the LLM:

1. **Weighs multiple signals together** — a 91% name match with perfect amount and timing is stronger than 91% with late timing and inconsistent history
2. **Calculates a precise confidence score** — not just "high" but a specific number like 87%
3. **Handles edge cases** — multi-period payments, format differences, first-time payers
4. **Produces ordered reasoning** — human-readable explanations that the analyst can review

The structured prompt sent to Claude includes:
- All computed signals (the snapshot from Stage 2)
- Payment details (amount, sender, references)
- Matched customer/policy context (if any)
- The specific scenario's decision criteria and thresholds
- Instructions to produce structured JSON output

---

## Output Format

Every scenario produces the same structured JSON:

```json
{
  "recommendation": "APPLY | HOLD | ESCALATE",
  "confidence_score": 0-100,
  "scenario_route": 1-5,
  "decision_path": "scenario_1_auto_apply",
  "requires_human_approval": true,
  "approval_reason": "Name similarity below auto-apply threshold",
  "reasoning": [
    "Reason 1...",
    "Reason 2...",
    "Reason 3..."
  ],
  "suggested_action": "Apply to POL-12345"
}
```

This fills the `PaymentRecommendation` proto and is passed to Stage 4 (Persist).

---

## Backend Modules

| File | Responsibility |
|------|---------------|
| `backend/app/services/agent/router.py` | Deterministic scenario routing (the decision tree) |
| `backend/app/services/agent/reasoning.py` | Claude API call with structured prompts |
| `backend/app/services/agent/scenarios/sc1_strong_match.py` | Scenario 1 prompt, criteria, output parsing |
| `backend/app/services/agent/scenarios/sc2_customer_match.py` | Scenario 2 prompt, criteria, output parsing |
| `backend/app/services/agent/scenarios/sc3_amount_variance.py` | Scenario 3 prompt, criteria, output parsing |
| `backend/app/services/agent/scenarios/sc4_no_match.py` | Scenario 4 prompt, criteria, output parsing |
| `backend/app/services/agent/scenarios/sc5_duplicate.py` | Scenario 5 prompt, criteria, output parsing |

---

## What Happens Next

The recommendation is produced. Stage 4 (Persist) saves it to the database, updates the payment status, and writes the audit trail.

See: [04_Persist_Layer.md](./04_Persist_Layer.md)

---

*End of Document*
