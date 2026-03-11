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
IF Name_Similarity_Score < 100%:
  → Route to Scenario 4 (customer match issue)
  → Do NOT process as Scenario 3

Name must match exactly to proceed with variance analysis
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
          │ Name match = 100%?  │
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
            ┌───────────┐ ┌────────┐ ┌───────────────┐
            │AUTO-APPROVE│ │  HOLD  │ │ Check:        │
            │(Scenario 1)│ │(manual │ │ Multi-period? │
            └───────────┘ │review) │ │ e.g. payment /│
                          └────────┘ │ premium = 2,3x│
                                     └───────┬───────┘
                                             │
                                      ┌─YES──┴──NO──┐
                                      │             │
                                      ▼             ▼
                                ┌───────────┐ ┌───────────┐
                                │ ESCALATE  │ │ ESCALATE  │
                                │ Note:     │ │ Flag:     │
                                │"Possible  │ │"Unexplain-│
                                │ N-period  │ │ ed        │
                                │ prepay"   │ │ variance" │
                                └───────────┘ └───────────┘

  Note: For HOLD and ESCALATE, also check:
  ┌─────────────────────────────────────────┐
  │ Historical Pattern Consistency          │
  │ - Compare to last 6-12 payments         │
  │ - If variance matches historical pattern│
  │   note "consistent with history" in     │
  │   reasoning                             │
  └─────────────────────────────────────────┘
```

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
