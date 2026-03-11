# Scenario 1: Strong Policy Match

# Scenario Description

Payment has a high confidence match with a known policyholder and expected premium amount, with no risk flags. This represents the **ideal case** for automated processing.

**Example**: Customer "John A Smith" pays $5,000 with policy reference "POL-12345" which matches policyholder "John Smith" with expected premium of $5,000.

---

## When Does This Scenario Apply?

- Policy number is provided in payment reference field
- Sender name closely matches policy holder name
- Payment amount is close to expected premium
- No fraud or risk flags present

---

## Configuration Thresholds

| Parameter | Value | Description |
|-----------|-------|-------------|
| **Name Match - Auto Apply** | >90% | Automatic application without approval |
| **Name Match - Hold** | 75-90% | Requires manual approval |
| **Name Match - Escalate** | <75% | Insufficient match - escalate |
| **Amount Tolerance** | ±2% | Acceptable variance from expected premium |

---

## Decision Logic

### **Path 1: Auto-Apply** (No approval needed)
```
IF ALL of the following are true:
  ✓ Name_Similarity_Score > 90%
  ✓ Amount_Variance ≤ 2%
  ✓ Risk_Flags = None
  ✓ Policy_Status = Active

THEN → APPLY automatically
  Confidence: 90-100%
  Human Approval: Not required
```

### **Path 2: Hold for Approval**
```
IF Name_Similarity_Score is 75-90%
  AND Amount_Variance ≤ 2%
  AND Risk_Flags = None

THEN → HOLD (Apply with approval required)
  Confidence: 75-89%
  Human Approval: Required
  Reason: Name match not strong enough for auto-apply

OR

IF Risk_Flags = Present (high risk)
THEN → HOLD regardless of scores
  Human Approval: Required
  Reason: Risk flags detected
```

### **Path 3: Escalate**
```
IF Name_Similarity_Score < 75%

THEN → ESCALATE (route to Scenario 4)
  Confidence: 0%
  Reason: Insufficient name match
```

---

## Required Input Data

**Payment Information:**
- Sender Name (required)
- Payment Amount (required)
- Payment Date (required)
- Payment Method (required)
- Policy Reference in reference fields (required for this scenario)
- Sender Account (optional but helpful)

**System Data:**
- Policy Holder Name
- Expected Premium Amount
- Policy Status (Active/Inactive)
- Policy Number
- Last Payment History

---

## Key Signals to Compute

### 1. Name Similarity Score (0-100%)
- **Algorithm**: Jaro-Winkler or Levenshtein distance
- **Compares**: Payment sender name vs Policy holder name
- **Examples**:
  - "John Smith" vs "John Smith" = 100%
  - "John A Smith" vs "John Smith" = 92%
  - "J Smith" vs "John Smith" = 75%
  - "Jane Doe" vs "John Smith" = 20%

### 2. Amount Variance Percentage
- **Formula**: `|(Payment - Expected) / Expected| × 100`
- **Examples**:
  - $5,000 payment, $5,000 expected = 0% variance ✓
  - $5,100 payment, $5,000 expected = 2% variance ✓
  - $5,800 payment, $5,000 expected = 16% variance ✗ (routes to Scenario 3)

### 3. Policy Match Confidence (0-100%)
- Exact policy number in reference = 100%
- Fuzzy match with typos = 70-95%
- No policy number = 0% (routes to Scenario 2)

### 4. Risk Flags (Boolean)
- Check for: Fraud history, Suspended account, Chronic late payments
- Output: True/False + specific flag types

### 5. Payment Timing Match
- Compare payment date to expected due date
- Days early/late
- Quality: EXCELLENT / GOOD / ACCEPTABLE / POOR

---

## Example Scenarios

### Example 1: Auto-Apply (Perfect Match)

**Input:**
```json
{
  "payment_id": "PMT-001",
  "amount": 5000.00,
  "sender_name": "John Smith",
  "reference_field_1": "POL-12345",
  "payment_date": "2024-02-15"
}
```

**Policy Data:**
```json
{
  "policy_number": "POL-12345",
  "policy_holder_name": "John Smith",
  "premium_amount": 5000.00,
  "policy_status": "Active"
}
```

**Agent Output:**
- **Recommendation**: APPLY
- **Confidence**: 98%
- **Approval Required**: No
- **Reasoning**: "Perfect name match (100%), exact amount match (0% variance), policy explicitly provided, no risk flags"

---

### Example 3: Hold (Risk Flag Present)

**Input:**
```json
{
  "payment_id": "PMT-003",
  "amount": 5000.00,
  "sender_name": "John Smith",
  "reference_field_1": "POL-12345"
}
```

**Policy Data:**
```json
{
  "policy_number": "POL-12345",
  "policy_holder_name": "John Smith",
  "premium_amount": 5000.00,
  "risk_flags": ["FRAUD_HISTORY"]
}
```

**Agent Output:**
- **Recommendation**: HOLD
- **Confidence**: 70%
- **Approval Required**: Yes
- **Reasoning**: "Perfect name and amount match, BUT fraud history flag detected. Manual review required before applying payment."

---

### Example 4: Escalate (Poor Name Match)

**Input:**
```json
{
  "payment_id": "PMT-004",
  "amount": 5000.00,
  "sender_name": "Jane Doe",
  "reference_field_1": "POL-12345"
}
```

**Policy Data:**
```json
{
  "policy_number": "POL-12345",
  "policy_holder_name": "John Smith",
  "premium_amount": 5000.00
}
```

**Agent Output:**
- **Recommendation**: ESCALATE
- **Confidence**: 0%
- **Approval Required**: Yes
- **Reasoning**: "Policy number provided but sender name 'Jane Doe' does not match policy holder 'John Smith' (15% similarity). Route to Scenario 4 for investigation."

---

## Flow Diagram

```
        ┌─────────────────────────┐
        │ Payment with policy ref │
        │ Name match ≥75%         │
        │ Amount variance ≤2%     │
        └────────────┬────────────┘
                     │
          ┌──────────▼──────────┐
          │  Risk Flags Present? │
          └──────────┬──────────┘
                     │
           ┌───YES───┴───NO───┐
           │                  │
           ▼                  ▼
    ┌─────────────┐  ┌────────────────┐
    │    HOLD     │  │ Policy Status  │
    │  (approval  │  │ Active?        │
    │  required)  │  └───────┬────────┘
    └─────────────┘          │
                    ┌──YES───┴───NO───┐
                    │                 │
                    ▼                 ▼
           ┌────────────────┐  ┌─────────────┐
           │ Name Similarity │  │    HOLD     │
           │ Score?          │  │  "Inactive  │
           └───────┬────────┘  │   policy"   │
                   │           └─────────────┘
        ┌──────────┼──────────┐
        │          │          │
    >90%│    75-90%│      <75%│
        ▼          ▼          ▼
  ┌──────────┐ ┌────────┐ ┌───────────┐
  │  APPLY   │ │  HOLD  │ │ ESCALATE  │
  │  (auto)  │ │(review)│ │(Scenario 4│
  │No approve│ │approval│ │  routing) │
  └──────────┘ └────────┘ └───────────┘
```

---

## Edge Cases to Consider

### Case 1: Minor Amount Variance (Within 2%)
```
Payment: $5,100
Expected: $5,000
Variance: 2%
→ If name >90%: APPLY
→ If name 75-90%: HOLD
```

### Case 2: Name with Different Format
```
Sender: "Smith, John"
Policy Holder: "John Smith"
→ Name matching algorithm should handle format differences
→ Should still achieve >90% match
```

### Case 3: Inactive Policy
```
All matches perfect BUT Policy_Status = "Inactive"
→ HOLD for manual review
→ Reason: "Policy is inactive - verify if reactivation intended"
```

### Case 4: Amount Slightly Over Tolerance
```
Payment: $5,150
Expected: $5,000
Variance: 3%
→ Route to Scenario 3 (variance handling)
→ NOT Scenario 1 anymore
```


