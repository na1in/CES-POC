# Scenario 4: No Matching Customer

# Scenario Description

Payment sender does not match any known policyholder in the system. This scenario is reached only after Scenarios 1 and 2 have failed to match the payment. All payments reaching this scenario are escalated for manual investigation.

**Example**: Payment from "Alexandra Martinez" for $3,500, but no customer matches this name. Best fuzzy match is "Alexander Martinez" at 72% similarity (inactive since 2022). System escalates for investigation.

---

## When Does This Scenario Apply?

- Scenario 1 could not match (no valid policy reference or name match <75%)
- Scenario 2 could not match (name not exact and insufficient supporting signals)
- Unable to identify customer intent from available data

**This is the "last resort" scenario** - when all other matching attempts fail.

---

## Decision Logic

```
IF payment reaches Scenario 4:
  THEN → ESCALATE to investigation queue
  Confidence: 0%
  Human Approval: Required
  Reason: "No matching customer or policy identified"
```

All payments in this scenario are escalated. Partial match cases (75%+) are already handled by Scenarios 1 and 2 before reaching here.

---

## Required Input Data

**Payment Information:**
- Sender Name (required)
- Beneficiary Name (optional but helpful)
- Payment Amount (required)
- Payment Date (required)
- Payment Method (required)
- Any reference fields (helpful for investigation)

**System Data:**
- Global customer database (all active and inactive customers)
- Recent policy applications/quotes
- Pending customer records

---

## Key Signals to Compute

### 1. Max Database Similarity
- Highest similarity score found across entire customer database
- Include customer details for that match
- **Output**: Score + customer record (for investigator context)

### 2. Policy Reference Match
- Search for any policy number in reference fields
- Check if policy exists but under different name
- **Output**: Boolean + policy details if found

### 3. Amount Correlation
- Search for active policies with matching premium amounts
- May help investigator identify intended policy
- **Output**: List of policies with similar amounts

---

## Example Scenarios

### Example 1: No Match Found

**Input:**
```json
{
  "payment_id": "PMT-401",
  "amount": 3500.00,
  "sender_name": "Alexandra Martinez",
  "reference_field_1": "Insurance",
  "payment_method": "Check"
}
```

**Search Results:**
```json
{
  "exact_matches": 0,
  "best_fuzzy_match": {
    "customer_name": "Alexander Martinez",
    "similarity_score": 72,
    "customer_id": "CUST-7788",
    "status": "Inactive since 2022"
  }
}
```

**Agent Output:**
- **Recommendation**: ESCALATE
- **Confidence**: 0%
- **Reasoning**:
  - "No matching customer found for 'Alexandra Martinez'"
  - "Best fuzzy match: Alexander Martinez (72%) - INACTIVE since 2022"
  - "Unable to determine customer intent"
- **Investigation Required**:
  - "Contact sender to clarify intent"
  - "Search for pending policy applications"
  - "Check for recent name changes"

---

### Example 2: Misdirected Payment

**Input:**
```json
{
  "payment_id": "PMT-404",
  "amount": 5000.00,
  "sender_name": "Acme Corporation LLC",
  "beneficiary_name": "CES Insurance",
  "reference_field_1": "Invoice #12345"
}
```

**Search Results:**
```json
{
  "exact_matches": 0,
  "best_fuzzy_match": {
    "similarity_score": 15
  }
}
```

**Agent Output:**
- **Recommendation**: ESCALATE
- **Confidence**: 0%
- **Reasoning**:
  - "No matching customer found (max similarity 15%)"
  - "Sender appears to be a business entity, not individual"
  - "Reference mentions 'Invoice' suggesting possible misdirected payment"
- **Investigation Required**:
  - "Contact Acme Corporation to clarify payment purpose"
  - "Verify if CES Insurance is correct recipient"
  - "Review invoice #12345 if exists in system"

---

## Flow Diagram

```
        ┌──────────────────────────────┐
        │ Payment could not be matched │
        │ by Scenario 1 or 2           │
        └──────────────┬───────────────┘
                       │
            ┌──────────▼──────────┐
            │ Search entire       │
            │ customer database   │
            │ (active + inactive) │
            └──────────┬──────────┘
                       │
                       ▼
              ┌────────────────┐
              │    ESCALATE    │
              │                │
              │ Provide best   │
              │ fuzzy match +  │
              │ amount         │
              │ correlation    │
              │ for investigator│
              └────────────────┘
```

---

## Edge Cases to Consider

### Case 1: Third-Party Payment
```
Payment from "XYZ Company Payroll"
On behalf of employee who is policyholder

→ ESCALATE
→ Investigation: Identify employee, verify authorized third-party payment
```

### Case 2: Name Change Not Updated
```
Payment from "Sarah Johnson"
Customer in system as "Sarah Williams" (married name change)

→ ESCALATE
→ Investigator should check for name changes
```

### Case 3: New Policy Application
```
Payment from "Maria Garcia"
Reference: "New Policy Deposit"
Pending application found in system

→ ESCALATE
→ Note pending application in reasoning for investigator
```
