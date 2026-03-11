# AI Agent PoC - Payment Resolution Scenarios
## Executive Summary

**Document Version**: 1.0
**Date**: February 27, 2026
**Status**: Approved

---

## Overview

This document defines the decision logic for the AI Agent to handle unidentified/miscellaneous payments in insurance operations. The agent classifies payments and recommends one of three actions:

- **APPLY**: Allocate payment to identified policy
- **HOLD**: Keep in suspense for manual review
- **ESCALATE**: Route to investigation queue

---

## Configuration Thresholds

| Parameter | Value | Purpose |
|-----------|-------|---------|
| **Name Match - Auto Apply** | >90% | Minimum similarity for automated application |
| **Name Match - Hold/Review** | 75-90% | Range requiring manual approval |
| **Name Match - Escalate** | <75% | Below this = no match found |
| **Amount Tolerance** | ±2% | Acceptable variance - auto-approve |
| **Amount Variance - Hold** | 2-15% | Requires manual review |
| **Amount Variance - Escalate** | >15% | Route to investigation |
| **Duplicate Detection Window** | 72 hours | Time window for duplicate checking |

---

## Scenario 1: Strong Policy Match

**Trigger**: Policy number provided in reference field, name matches policyholder

### Decision Logic
```
IF Name_Similarity > 90%
   AND Amount_Variance ≤ 2%
   AND Risk_Flags = None
   AND Policy_Status = Active
THEN → APPLY (no approval needed)

IF Name_Similarity 75-90%
   AND Amount_Variance ≤ 2%
   AND Risk_Flags = None
THEN → HOLD (apply with approval)

IF Risk_Flags = Present
THEN → HOLD regardless of scores

IF Name_Similarity < 75%
THEN → ESCALATE
```

**Key Signals**: Name similarity, Amount variance, Policy match, Risk flags

**Output**: APPLY with 90-100% confidence or HOLD with 75-89% confidence

---

## Scenario 2: Likely Customer Match (No Policy Reference)

**Trigger**: Policy number missing or partial, but customer name matches

### Decision Logic
```
Step 1: Verify Customer Match
  IF Customer_Match = 100% exact
  OR (Customer_Match ≥ 80% AND 2+ supporting signals*)
  THEN continue
  ELSE → ESCALATE

Step 2: Check Amount Variance
  IF Amount_Variance > 15%
  THEN → Route to Scenario 3 (variance handling)

Step 3: Identify Policy
  CASE: Missing Policy Reference
    IF Exactly 1 active policy
    THEN → APPLY with approval

    IF >1 active policy AND amount matches exactly 1 policy
    THEN → APPLY with approval

    IF >1 active policy AND amount doesn't uniquely match
    THEN → HOLD (manual policy selection needed)

  CASE: Partial Policy Reference
    IF Partial reference matches exactly 1 policy
    THEN → APPLY with approval

    IF Partial reference matches multiple policies
    THEN → HOLD (manual selection needed)
```

**Supporting signals**: Account number match, Amount match, Historical pattern match

**Key Requirement**: Even with customer match, amount variance >15% triggers Scenario 3

**Output**: APPLY with approval (75-89% confidence) or HOLD

---

## Scenario 3: High Amount Variance

**Trigger**: Payment amount deviates from expected premium by >2%

### Decision Logic
```
Prerequisite: Name_Similarity = 100%
(If name doesn't match, route to Scenario 4)

Calculate: Variance = |Payment_Amount - Expected_Premium| / Expected_Premium × 100

IF Variance < 2%
THEN → AUTO-APPROVE (same as Scenario 1)

IF Variance 2-15%
THEN → HOLD (requires manual review)

IF Variance > 15%
THEN → ESCALATE (route to investigation)
```

**Key Signals**: Amount variance, Historical pattern consistency, Multi-period payment indicator

---

## Scenario 4: No Matching Customer

**Trigger**: No customer in database matches payment sender

### Decision Logic
```
IF payment reaches Scenario 4:
THEN → ESCALATE to investigation queue

All payments here are escalated. Partial match cases (75%+)
are already handled by Scenarios 1 and 2 before reaching here.
```

**Output**: ESCALATE with 0% confidence, provide best fuzzy match and amount correlation for investigator

---

## Scenario 5: Duplicate Payment Suspicion

**Trigger**: Payment matches recent transaction within 72 hours

### Decision Logic
```
Step 1: Search last 72 hours for matching payments
  Match on ALL fields:
    - Amount (exact)
    - Sender name (exact)
    - Payment method (exact)
    - Policy reference (exact)

Step 2: Evaluate match
  IF 100% exact match found within 72 hours
     AND Outstanding_Balance = 0
     AND Next_Payment_Not_Due
  THEN → ESCALATE (potential duplicate)

  IF 100% exact match found
     AND Outstanding_Balance > 0
  THEN → HOLD (might be legitimate catch-up payment)

  IF No exact match found
  THEN → Route to appropriate scenario (1, 2, or 3)
```

**Investigation Required**:
- Contact customer to confirm duplicate or intentional
- Verify ACH/payment setup for errors
- Confirm if advance payment or mistake
- Check bank for duplicate submission

**Resolution Options**:
- Refund if confirmed duplicate
- Apply to next period if confirmed advance payment
- Keep in suspense until customer confirms

**Output**: ESCALATE with duplicate alert, provide original payment details

---

## Master Routing Flow

```
                    ┌─────────────────────┐
                    │   Payment Received   │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  SCENARIO 5 CHECK   │
                    │  (Runs FIRST)       │
                    │  Exact match within │
                    │  72 hours?          │
                    └──────────┬──────────┘
                               │
                  ┌────YES─────┴─────NO────┐
                  │                        │
                  ▼                        ▼
          ┌──────────────┐     ┌──────────────────┐
          │ Scenario 5   │     │ Policy reference │
          │ Duplicate    │     │ provided?        │
          └──────────────┘     └────────┬─────────┘
                                        │
                           ┌────YES─────┴─────NO────┐
                           │                        │
                           ▼                        ▼
                  ┌──────────────┐       ┌──────────────────┐
                  │ Name match   │       │ Customer match?  │
                  │ ≥75%?        │       │ (exact or 2+     │
                  └──────┬───────┘       │  supporting      │
                         │               │  signals)        │
                    YES  │  NO           └────────┬─────────┘
                    ┌────┴────┐                   │
                    │         │          ┌──YES───┴───NO──┐
                    ▼         │          │                │
           ┌─────────────┐   │          ▼                ▼
           │ Amount      │   │   ┌─────────────┐  ┌───────────┐
           │ variance    │   │   │ Scenario 2  │  │Scenario 4 │
           │ ≤2%?        │   │   │ Customer    │  │No Match   │
           └──────┬──────┘   │   │ Match       │  │ESCALATE   │
                  │          │   └─────────────┘  └───────────┘
             YES  │  NO      │
             ┌────┴────┐     │
             │         │     │
             ▼         ▼     ▼
      ┌───────────┐ ┌───────────┐
      │Scenario 1 │ │Scenario 3 │
      │Strong     │ │Amount     │
      │Match      │ │Variance   │
      └───────────┘ └───────────┘
```

---

## Summary Decision Matrix

| Scenario | Key Condition | Action | Human Approval |
|----------|--------------|--------|----------------|
| **1 - Auto Apply** | Name >90%, Amount ±2%, No risk flags | **APPLY** | No |
| **1 - Hold** | Name 75-90%, Amount ±2% | **HOLD** | Required |
| **1 - Hold** | Risk flags present (any score) | **HOLD** | Required |
| **1 - Escalate** | Name <75% | **ESCALATE** | Required |
| **2 - Apply** | Customer matched, 1 policy or amount identifies 1 | **APPLY** | Required |
| **2 - Hold** | Customer matched, cannot disambiguate policy | **HOLD** | Required |
| **3 - Auto Approve** | Variance <2% | **APPLY** | No |
| **3 - Hold** | Variance 2-15% | **HOLD** | Required |
| **3 - Escalate** | Variance >15% | **ESCALATE** | Required |
| **4 - No Match** | All matching attempts failed | **ESCALATE** | Required |
| **5 - Duplicate** | 100% exact match within 72 hours, no balance | **ESCALATE** | Required |
| **5 - Hold** | 100% exact match within 72 hours, balance exists | **HOLD** | Required |

---

## Standard Output Format

Every recommendation must include:

```json
{
  "payment_id": "PMT-2024-XXX",
  "recommendation": "APPLY | HOLD | ESCALATE",
  "confidence_score": 0-100,
  "matched_policy": "POL-XXXXX or null",
  "matched_customer": "CUST-XXXXX or null",
  "requires_human_approval": true/false,
  "approval_reason": "explanation",
  "reasoning": [
    "Clear explanation point 1",
    "Clear explanation point 2",
    "Clear explanation point 3"
  ],
  "suggested_action": "specific action description",
  "signals_computed": {
    "key_signal_1": value,
    "key_signal_2": value
  },
  "audit_trail": {
    "timestamp": "ISO 8601",
    "processing_time_ms": integer,
    "decision_path": "scenario_identifier"
  }
}
```

---

## Key Design Principles

1. **Deterministic**: Same inputs always produce same outputs
2. **Explainable**: Every decision has clear reasoning
3. **Auditable**: Complete trail of signals and logic
4. **Configurable**: All thresholds can be adjusted
5. **Human-in-the-loop**: Approval required for ambiguous cases
6. **Safe**: Conservative thresholds to prevent errors

---

## Next Steps

1. **For Implementation Team**: Reference detailed specification in `Final_Scenario_Definitions.md`
2. **For Business Review**: Use this executive summary for approval and discussion
3. **For Configuration**: Adjust thresholds in configuration parameters section
4. **For Testing**: Create test cases covering all scenarios and edge cases

---

**Related Documents**:
- `Final_Scenario_Definitions.md` - Detailed technical specification
- `Step3_Feature_Signals.md` - Complete signal definitions and computation methods
- `AI_Agent_Payment_PoC_One_Pager.pdf` - Original project scope

---

**End of Executive Summary**
