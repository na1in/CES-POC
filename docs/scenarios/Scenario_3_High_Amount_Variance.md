# Scenario 3: High Amount Variance

# Scenario Description

Payment amount deviates from expected premium by more than acceptable tolerance. Customer and policy match correctly, but the amount requires investigation.

**Example**: Customer "Robert Chen" with policy POL-11223 pays $3,000, but expected annual premium is $2,500 (20% variance). System escalates for investigation.

---

## When Does This Scenario Apply?

- **Prerequisite**: Name and policy match correctly (otherwise routes to Scenario 1 or 4)
- Payment amount variance exceeds 2% tolerance
- No clear explanation for the variance
- Historical payments show different pattern

---

## Configuration Thresholds

| Parameter | Value | Action | Description |
|-----------|-------|--------|-------------|
| **Variance** | <2% | **AUTO-APPROVE** | Same as Scenario 1 |
| **Variance** | 2-15% | **HOLD** | Requires manual review |
| **Variance** | >15% | **ESCALATE** | Route to investigation |

---

## Decision Logic

### **Prerequisite Check**

```
IF Name_Similarity_Score < 90%:
  → Route to Scenario 4 (customer match issue)
  → Do NOT process as Scenario 3

Name must match at ≥90% to proceed with variance analysis.
(Relaxed from 100% — name variations like middle initials,
 format differences, and post-wedding name changes are common.)
```

### **Variance-Based Decision Logic**

```
# Calculate variance
Variance = |Payment_Amount - Expected_Premium| / Expected_Premium × 100

# Auto-Approve (<2%)
IF Variance < 2%:
  THEN → APPLY (no approval needed)
  Note: Treated same as Scenario 1

# Hold (2-15%)
IF Variance ≥ 2% AND Variance ≤ 15%:
  THEN → HOLD for manual review
  Reason: "Amount variance requires verification"
  Human Approval: Required

# Escalate (>15%)
IF Variance > 15%:
  FIRST check for multi-method or third-party payment:

  IF is_multi_method = true:
    THEN → HOLD (not ESCALATE)
    Reason: "Appears to be a split/multi-method payment"
    Human Approval: Required

  ELSE IF is_third_party_payment = true AND Variance ≤ 50%:
    THEN → HOLD (not ESCALATE)
    Reason: "Third-party payment detected"
    Human Approval: Required

  ELSE:
    THEN → ESCALATE to investigation queue
    Reason: "Significant amount variance - requires investigation"
    Priority: Based on variance magnitude
```

---

## Required Input Data

**Payment Information:**
- Payment Amount (required)
- Sender Name (required)
- Payment Date (required)
- Payment Method (required)
- Policy Reference (required)

**System Data:**
- Expected Premium Amount for policy
- Historical Payment Average (last 6-12 payments)
- Policy Modification History
- Premium Frequency (monthly/quarterly/annual)

---

## Key Signals to Compute

### 1. Amount Variance Percentage
- **Formula**: `|(Payment - Expected) / Expected| × 100`
- **Output**: Percentage
- **Classification**: Auto-Approve / Hold / Escalate

### 2. Historical Pattern Consistency
- Compare current payment to last 6-12 payments
- Calculate mean and standard deviation
- Detect statistical outliers
- **Output**: Consistency score (0-100) + outlier flag

### 3. Multi-Period Payment Indicator
- Check if amount represents multiple premium periods
- **Formula**: `round(Payment_Amount / Expected_Premium)`
- **Example**: $7,500 payment / $2,500 premium = 3 periods
- **Output**: Boolean + estimated periods

### 4. Overpayment/Underpayment Classification
- **Overpayment**: Payment > Expected
- **Underpayment**: Payment < Expected
- **Output**: Classification + amount difference

### 5. Multi-Method Payment Indicator (NEW)

Customers frequently split a single premium across multiple payments made via different methods or from different banks. This is **normal and common** in insurance.

**Examples:**
- Premium is $7,500. Customer pays $2,500 x 3 (from 3 different banks)
- Premium is $5,000. Customer pays $5,000 x 1 + $2,500 x 1 (different methods)

**Detection Logic:**
```
IF payment amount < expected premium:
  Check: Does payment ≈ expected / N  (where N = 2, 3, 4)?

  IF payment is within 5% of (expected / N):
    → is_multi_method = true
    → multi_method_fraction = payment / expected  (e.g., 0.333)
    → Check recent payments for same policy in last 30 days
    → Sum them up: do they approach the full premium?

  Also check:
    → Is the payment method different from historical?
    → Is the sender account different from historical?
    → Both suggest a split/multi-method payment
```

**Impact on Decision:**
- Multi-method detected + partial payments sum to premium → **HOLD** (not ESCALATE)
- Reasoning notes: "Appears to be a split payment — $2,500 is 1/3 of $7,500 premium"
- Reduces the effective variance for decision-making (the "real" variance may be 0%)

### 6. Third-Party Payment Indicator (NEW)

It is common for someone other than the policyholder to make a payment on their behalf:

| Third-Party Type | Example |
|-----------------|---------|
| Family member | Spouse, parent, or child pays from their account |
| Employer payroll | Company makes payment via payroll deduction |
| Mortgage escrow | Mortgage company pays homeowner's insurance |
| Power of attorney | Legal representative pays on behalf |

**Detection Logic:**
```
IF sender_name does NOT match policyholder name (similarity < 75%):
  BUT payment references a valid policy
  AND amount is close to expected premium (variance ≤ 15%)

  THEN → is_third_party_payment = true

  Check sender against:
    → Known family members (if available)
    → Historical third-party payers for this policy
    → Common corporate/escrow patterns in sender name
    → Classify relationship: "family", "employer", "escrow", "unknown"
```

**Impact on Decision:**
- Third-party detected + amount matches → **HOLD** with approval (not ESCALATE)
- Third-party detected + amount off → normal variance rules apply
- Reasoning notes: "Third-party payment detected — sender appears to be employer/family/escrow"
- This prevents legitimate third-party payments from being escalated to Scenario 4 just because the sender name doesn't match

---

## Example Scenarios

### Example 1: Hold - Minor Variance (8%)

**Input:**
```json
{
  "payment_id": "PMT-301",
  "amount": 2700.00,
  "sender_name": "Robert Chen",
  "reference_field_1": "POL-11223"
}
```

**Policy Data:**
```json
{
  "policy_number": "POL-11223",
  "policy_holder_name": "Robert Chen",
  "premium_amount": 2500.00
}
```

**Calculation:**
- Variance = (2700 - 2500) / 2500 × 100 = **8%**

**Agent Output:**
- **Recommendation**: HOLD
- **Confidence**: 80%
- **Approval Required**: Yes
- **Reasoning**: "Name and policy match perfectly. Payment $2,700 is 8% higher than expected $2,500. Variance within 2-15% range - holding for manual review."

---

### Example 2: Escalate - High Variance (20%)

**Input:**
```json
{
  "payment_id": "PMT-302",
  "amount": 3000.00,
  "sender_name": "Robert Chen",
  "reference_field_1": "POL-11223"
}
```

**Policy Data:**
```json
{
  "premium_amount": 2500.00,
  "historical_payments": [2500, 2500, 2500, 2400]
}
```

**Calculation:**
- Variance = (3000 - 2500) / 2500 × 100 = **20%**

**Agent Output:**
- **Recommendation**: ESCALATE
- **Confidence**: 40%
- **Reasoning**: "Name and policy match perfectly. Payment $3,000 is 20% higher than expected $2,500. Variance exceeds 15% - escalating for investigation."
- **Investigation Required**:
  - "Verify customer intended to pay $3,000"
  - "Check for policy modifications or coverage increases"
  - "Determine if overpayment, partial prepayment, or error"

---

## Flow Diagram

```
        ┌─────────────────────────┐
        │ Payment with policy ref │
        │ Amount variance >2%     │
        └────────────┬────────────┘
                     │
          ┌──────────▼──────────┐
          │ Name match ≥ 90%?   │
          └──────────┬──────────┘
                     │
           ┌───NO────┴───YES───┐
           │                   │
           ▼                   ▼
    ┌─────────────┐   ┌────────────────┐
    │ Route to    │   │ Calculate      │
    │ Scenario 4  │   │ Variance %     │
    └─────────────┘   └───────┬────────┘
                              │
                   ┌──────────┼──────────┐
                   │          │          │
               <2% │     2-15%│      >15%│
                   │          │          │
                   ▼          ▼          ▼
            ┌───────────┐ ┌────────┐ ┌──────────────────────┐
            │AUTO-APPROVE│ │  HOLD  │ │ Check special cases: │
            │(Scenario 1)│ │(manual │ │                      │
            └───────────┘ │review) │ │ 1. Multi-period?     │
                          └────────┘ │    (payment = N x    │
                                     │     premium)         │
                                     │ 2. Multi-method?     │
                                     │    (payment = 1/N of │
                                     │     premium)         │
                                     │ 3. Third-party?      │
                                     │    (sender ≠ holder) │
                                     └──────────┬───────────┘
                                                │
                              ┌─────────────────┼────────────────┐
                              │                 │                │
                        Multi-period      Multi-method      Third-party
                        or multi-method   or third-party     (≤50% var)
                         detected          detected               │
                              │                 │                │
                              ▼                 ▼                ▼
                        ┌───────────┐    ┌───────────┐    ┌───────────┐
                        │   HOLD    │    │   HOLD    │    │   HOLD    │
                        │ "Possible │    │ "Split    │    │ "Third-   │
                        │  N-period │    │  payment  │    │  party    │
                        │  prepay"  │    │  across   │    │  payment" │
                        └───────────┘    │  methods" │    └───────────┘
                                         └───────────┘
                                                          None detected
                                                                │
                                                                ▼
                                                         ┌───────────┐
                                                         │ ESCALATE  │
                                                         │"Unexplain-│
                                                         │ ed        │
                                                         │ variance" │
                                                         └───────────┘

  Note: For all outcomes, also check:
  ┌─────────────────────────────────────────┐
  │ Historical Pattern Consistency          │
  │ - Compare to last 6-12 payments         │
  │ - If variance matches historical pattern│
  │   note "consistent with history" in     │
  │   reasoning                             │
  └─────────────────────────────────────────┘
```

---

### Example 3: Multi-Method Split Payment

**Input:**
```json
{
  "payment_id": "PMT-303",
  "amount": 2500.00,
  "sender_name": "Robert Chen",
  "reference_field_1": "POL-11223",
  "payment_method": "CHECK"
}
```

**Policy Data:**
```json
{
  "premium_amount": 7500.00,
  "recent_payments_last_30_days": [
    {"amount": 2500.00, "method": "ACH", "date": "2026-03-01"},
    {"amount": 2500.00, "method": "WIRE", "date": "2026-03-05"}
  ]
}
```

**Calculation:**
- Variance = (2500 - 7500) / 7500 × 100 = **-66.7%** (underpayment)
- But: $2,500 = $7,500 / 3 → multi_method_fraction = 0.333
- Recent payments: $2,500 + $2,500 + $2,500 (this) = $7,500 = full premium

**Agent Output:**
- **Recommendation**: HOLD (not ESCALATE)
- **Confidence**: 75%
- **Reasoning**: "Payment $2,500 appears to be 1/3 of $7,500 premium. Two prior payments of $2,500 found in last 30 days via different methods (ACH, Wire). This payment via Check completes the full premium. Multi-method split payment pattern detected."

---

### Example 4: Third-Party Payment (Employer)

**Input:**
```json
{
  "payment_id": "PMT-304",
  "amount": 2500.00,
  "sender_name": "Acme Corp Payroll",
  "reference_field_1": "POL-11223"
}
```

**Policy Data:**
```json
{
  "policy_holder_name": "Robert Chen",
  "premium_amount": 2500.00
}
```

**Calculation:**
- Name similarity: "Acme Corp Payroll" vs "Robert Chen" = ~10% (very low)
- But: amount matches premium exactly (0% variance)
- Policy reference is valid
- Sender name contains "Corp" + "Payroll" → likely employer payment

**Agent Output:**
- **Recommendation**: HOLD
- **Confidence**: 70%
- **Reasoning**: "Sender 'Acme Corp Payroll' does not match policyholder 'Robert Chen'. However, amount matches expected premium exactly and policy reference is valid. Third-party payment detected — sender appears to be employer (payroll pattern). Requires approval to verify authorized third-party payer."

---

## Edge Cases to Consider

### Case 1: Underpayment Variance
```
Payment: $2,000
Expected: $2,500
Variance: -20% (underpayment)

→ ESCALATE (>15%)
→ Investigate: Partial payment? Financial hardship? Error?
```

### Case 2: Variance at Boundary
```
Payment: $2,875
Expected: $2,500
Variance: 15.0% exactly

→ Still within HOLD range (2-15%)
→ Test boundary conditions carefully
```

### Case 3: Historical Pattern Shows Variance is Normal
```
Payment: $3,000
Expected: $2,500
Historical: [3000, 2900, 3100, 2950]

→ Variance is 20% so ESCALATE
→ But note "consistent with historical pattern" in reasoning
```
