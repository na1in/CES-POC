# Scenario 5: Duplicate Payment Suspicion

# Scenario Description

Payment closely matches a recent transaction within 72-hour window on all critical fields. Amount matching allows a **$2 tolerance** to account for fees, charges, and rounding differences. Indicates potential accidental duplicate submission.

**Example**: Customer "Emily Watson" paid $750 for POL-99887 on Feb 23 at 10:15 AM. Same customer pays $749.50 again for same policy on Feb 25 at 2:30 PM (52 hours later). Despite the $0.50 difference (bank fee), system flags as potential duplicate.

---

## When Does This Scenario Apply?

- Payment received within **72 hours** of a previous payment
- **Match** on all critical fields:
  - Amount (within **$2 tolerance** — covers fees, charges, rounding)
  - Sender name (exact)
  - Payment method (exact)
  - Policy reference (exact)
- Policy has **no outstanding balance** that would justify duplicate
- Next payment **not yet due**

**This scenario runs FIRST** - before other scenarios are evaluated.

---

## Configuration Thresholds

| Parameter | Value | Description |
|-----------|-------|-------------|
| **Duplicate Time Window** | 72 hours | Check last 72 hours for matching payments |
| **Match Requirement** | Exact on 3 fields + $2 tolerance on amount | Sender, method, reference must be exact; amount within $2 |
| **Duplicate Amount Tolerance** | $2.00 | Covers bank fees, charges, rounding |
| **Outstanding Balance Check** | Yes | If balance exists, may be legitimate |

---

## Decision Logic

```
Step 1: Search Recent Transaction History (Last 72 Hours)

  Query = Search for payments WHERE:
    - Timestamp within last 72 hours
    - Sender_Name = Current_Payment.Sender_Name         (exact)
    - Policy_Reference = Current_Payment.Policy_Reference (exact)
    - Payment_Method = Current_Payment.Payment_Method     (exact)
    - |Amount - Current_Payment.Amount| ≤ $2.00           (tolerance)

  The $2 tolerance accounts for:
    - Bank processing fees (e.g., $7,500 → $7,499)
    - Rounding differences (e.g., $7,500 → $7,499.50)
    - Small surcharges (e.g., $7,500 → $7,501)

Step 2: Evaluate Match

  IF No matching payments found:
    → Not a duplicate, route to Scenario 1, 2, 3, or 4

  IF Match found (3 exact fields + amount within $2):

    IF Policy.Outstanding_Balance > 0:
      THEN → HOLD
      Reason: "Potential duplicate but outstanding balance exists"
      Note: If amounts differ slightly, include: "Amount difference
        of $X.XX likely due to fees/rounding"

    ELSE:
      THEN → ESCALATE
      Reason: "Potential duplicate detected within 72 hours"
      Risk_Flag: "POTENTIAL_DUPLICATE"

  IF Amount difference > $2 but other fields match:
    → Not a duplicate, route to Scenario 1, 2, 3, or 4
    → Note in reasoning: "Similar payment found but amount
      difference of $X.XX exceeds $2 tolerance"
```

---

## Required Input Data

**Payment Information:**
- Payment Amount (required)
- Sender Name (required)
- Payment Timestamp (required, with time)
- Payment Method (required)
- Policy Reference (required)
- Sender Account (helpful for verification)

**System Data:**
- Recent Transaction History (last 72 hours minimum)
- Policy outstanding balance
- Next payment due date
- Payment frequency

---

## Key Signals to Compute

### 1. Duplicate Probability Score (0-100%)
- Check match on critical fields: sender name (exact), payment method (exact), policy reference (exact), amount (within $2 tolerance)
- **Output**: 0% or 100% (binary — either all criteria met or not)
- Amount difference (if any) is captured separately for reporting

### 2. Time Between Payments
- Calculate hours/minutes between current and original payment
- **Output**: Hours + interpretation

### 3. Outstanding Balance Check
- Query current policy balance
- Determine if duplicate payment could be legitimate
- **Output**: Balance amount + boolean (justifies_duplicate)

---

## Example Scenarios

### Example 1: Clear Duplicate (52 hours apart)

**Input:**
```json
{
  "payment_id": "PMT-505",
  "amount": 750.00,
  "sender_name": "Emily Watson",
  "payment_date": "2024-02-25T14:30:00Z",
  "payment_method": "ACH",
  "reference_field_1": "POL-99887"
}
```

**Recent History:**
```json
{
  "recent_payments": [
    {
      "payment_id": "PMT-504",
      "amount": 750.00,
      "sender_name": "Emily Watson",
      "payment_date": "2024-02-23T10:15:00Z",
      "payment_method": "ACH",
      "reference_field_1": "POL-99887",
      "status": "Applied"
    }
  ]
}
```

**Policy Data:**
```json
{
  "policy_number": "POL-99887",
  "outstanding_balance": 0.00,
  "next_due_date": "2024-03-20"
}
```

**Agent Output:**
- **Recommendation**: ESCALATE
- **Duplicate Probability**: 100%
- **Reasoning**:
  - "DUPLICATE ALERT: Matching payment detected"
  - "Original: PMT-504 for $750 on 2024-02-23 10:15 AM"
  - "Time between: 52 hours (within 72-hour window)"
  - "100% exact match: Amount, Sender, Method, Policy"
  - "Policy has $0 balance, next payment not due until March 20"
- **Investigation Required**:
  - "Contact Emily Watson to confirm duplicate or intentional"
  - "Check ACH payment setup for errors"

---

### Example 2: Duplicate with Outstanding Balance

**Input:**
```json
{
  "payment_id": "PMT-506",
  "amount": 1500.00,
  "sender_name": "Michael Brown",
  "payment_date": "2024-02-26T09:00:00Z",
  "payment_method": "Credit Card",
  "reference_field_1": "POL-11111"
}
```

**Recent History:**
```json
{
  "recent_payments": [
    {
      "payment_id": "PMT-505A",
      "amount": 1500.00,
      "sender_name": "Michael Brown",
      "payment_date": "2024-02-24T15:30:00Z",
      "payment_method": "Credit Card",
      "reference_field_1": "POL-11111",
      "status": "Applied"
    }
  ]
}
```

**Policy Data:**
```json
{
  "policy_number": "POL-11111",
  "outstanding_balance": 1500.00,
  "past_due_amount": 1500.00
}
```

**Agent Output:**
- **Recommendation**: HOLD
- **Confidence**: 60%
- **Reasoning**:
  - "Potential duplicate detected (100% match within 41 hours)"
  - "HOWEVER: Policy has $1,500 outstanding balance (past due)"
  - "May be legitimate catch-up payment for missed premium"
- **Investigation Required**:
  - "Contact Michael Brown to confirm intent"
  - "Verify if catch-up payment for past due amount"

---

## Flow Diagram

```
         ┌─────────────────────────┐
         │   Payment Received      │
         │   (checked FIRST)       │
         └────────────┬────────────┘
                      │
          ┌───────────▼───────────┐
          │ Search last 72 hours  │
          │ for match on:         │
          │  - Sender Name (exact)│
          │  - Payment Method     │
          │    (exact)            │
          │  - Policy Reference   │
          │    (exact)            │
          │  - Amount (within $2) │
          │    e.g. $7499-$7501   │
          └───────────┬───────────┘
                      │
           ┌──────────┴──────────┐
           │                     │
         Match               No Match
     (within $2)                 │
           │                     ▼
           │            ┌───────────────┐
           │            │ Not duplicate │
           │            │ Route to      │
           │            │ Scenario      │
           │            │ 1, 2, 3, or 4 │
           │            └───────────────┘
           ▼
   ┌───────────────┐
   │ Outstanding   │
   │ balance on    │
   │ policy?       │
   └───────┬───────┘
           │
    ┌─YES──┴──NO──┐
    │             │
    ▼             ▼
┌────────┐  ┌───────────┐
│  HOLD  │  │ ESCALATE  │
│"May be │  │"Potential │
│catch-up│  │ duplicate │
│payment"│  │ detected" │
│        │  │           │
│If amt  │  │If amt     │
│differs:│  │differs:   │
│note fee│  │note fee   │
│/rounding│ │/rounding  │
└────────┘  └───────────┘
```

---

## Edge Cases to Consider

### Case 1: Duplicate at 72-Hour Boundary
```
First payment: Feb 20 10:00 AM
Second payment: Feb 23 10:01 AM
Time difference: 72 hours 1 minute

→ Outside 72-hour window
→ Process normally
```

### Case 2: Same Amount, Different Policy
```
Payment 1: $1,000 for POL-11111
Payment 2: $1,000 for POL-22222
Same customer, same amount, within 72 hours

→ NOT a duplicate (different policies)
→ Process normally
```

### Case 3: Amount Within $2 Tolerance (Fees/Rounding)
```
Payment 1: $7,500.00 for POL-33333 (via ACH)
Payment 2: $7,499.00 for POL-33333 (via ACH, 48 hours later)
Amount difference: $1.00 (within $2 tolerance)

→ DUPLICATE detected (not exact, but within tolerance)
→ Reasoning includes: "Amount differs by $1.00, likely due to
   bank processing fees"
→ Same HOLD/ESCALATE logic applies based on outstanding balance
```

### Case 3b: Amount Outside $2 Tolerance
```
Payment 1: $7,500.00 for POL-33333
Payment 2: $7,495.00 for POL-33333 (48 hours later)
Amount difference: $5.00 (exceeds $2 tolerance)

→ NOT flagged as duplicate
→ Process normally through Scenarios 1-4
→ Note in reasoning: "Similar payment found 48 hours ago but
   amount difference of $5.00 exceeds duplicate tolerance"
```

### Case 4: Failed Original Payment
```
Payment 1: Feb 23 (failed, bounced)
Payment 2: Feb 25 (current)

→ NOT a duplicate if first failed
→ Verify first payment status before flagging
```
