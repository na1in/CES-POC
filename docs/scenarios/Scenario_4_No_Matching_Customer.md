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

### **Step 1: Third-Party Payment Check (NEW)**

Before escalating, check if this could be a legitimate third-party payment:

```
IF payment has a valid policy reference:
  Look up the policy regardless of sender name

  IF policy exists AND is active:
    IF amount is close to expected premium (variance ≤ 15%):
      → is_third_party_payment = true
      → HOLD (not ESCALATE)
      → Confidence: 40-60%
      → Reason: "Sender does not match policyholder, but payment
        references a valid active policy with matching amount.
        Possible third-party payment."

    IF amount does NOT match (variance > 15%):
      → ESCALATE
      → Note: "Valid policy found but amount does not match.
        Possible third-party payment with incorrect amount."
```

**Common third-party patterns to detect:**

| Sender Pattern | Likely Relationship |
|---------------|-------------------|
| Contains "Corp", "LLC", "Inc", "Payroll" | Employer payroll |
| Contains "Escrow", "Mortgage", "Bank" | Mortgage escrow company |
| Same last name as policyholder | Family member |
| Contains "Trust", "Estate" | Legal entity / estate |
| Contains "POA", "Attorney" | Power of attorney |

### **Step 2: Default — Escalate All Remaining**

```
IF payment reaches Scenario 4 AND no third-party pattern detected:
  THEN → ESCALATE to investigation queue
  Confidence: 0%
  Human Approval: Required
  Reason: "No matching customer or policy identified"
```

Payments without a valid policy reference and no name match are always escalated. The system still provides best fuzzy match and amount correlation data to assist the investigator.

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

### 4. Third-Party Payment Detection (NEW)
- Check if sender name contains corporate/institutional patterns
- Check if a valid policy is referenced despite name mismatch
- Check if sender shares last name with any policyholder
- Check historical third-party payers for referenced policy
- **Output**: Boolean + detected relationship type + referenced policy details

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

### Example 3: Third-Party Payment Caught (NEW)

**Input:**
```json
{
  "payment_id": "PMT-405",
  "amount": 2500.00,
  "sender_name": "Pinnacle Mortgage Services",
  "reference_field_1": "POL-11223",
  "payment_method": "ACH"
}
```

**Search Results:**
```json
{
  "sender_customer_match": 0,
  "policy_lookup": {
    "policy_number": "POL-11223",
    "policy_holder_name": "Robert Chen",
    "premium_amount": 2500.00,
    "status": "Active"
  },
  "third_party_detection": {
    "is_third_party": true,
    "relationship": "escrow",
    "reason": "Sender contains 'Mortgage Services' pattern"
  }
}
```

**Agent Output:**
- **Recommendation**: HOLD (not ESCALATE)
- **Confidence**: 55%
- **Reasoning**:
  - "Sender 'Pinnacle Mortgage Services' does not match policyholder 'Robert Chen'"
  - "However, payment references valid active policy POL-11223"
  - "Amount $2,500 matches expected premium exactly (0% variance)"
  - "Third-party payment detected — sender appears to be mortgage escrow company"
  - "Holding for approval to verify authorized third-party payer"

---

### Example 4: Third-Party — Family Member (NEW)

**Input:**
```json
{
  "payment_id": "PMT-406",
  "amount": 1250.00,
  "sender_name": "David Chen",
  "reference_field_1": "POL-11223"
}
```

**Search Results:**
```json
{
  "sender_customer_match": 0,
  "policy_lookup": {
    "policy_number": "POL-11223",
    "policy_holder_name": "Robert Chen",
    "premium_amount": 1250.00,
    "status": "Active"
  },
  "third_party_detection": {
    "is_third_party": true,
    "relationship": "family",
    "reason": "Sender shares last name 'Chen' with policyholder"
  }
}
```

**Agent Output:**
- **Recommendation**: HOLD (not ESCALATE)
- **Confidence**: 50%
- **Reasoning**:
  - "Sender 'David Chen' does not match policyholder 'Robert Chen'"
  - "Payment references valid active policy POL-11223"
  - "Amount matches expected premium exactly"
  - "Sender shares last name with policyholder — possible family member payment"
  - "Holding for approval to verify relationship"

---

## Flow Diagram

```
        ┌──────────────────────────────┐
        │ Payment could not be matched │
        │ by Scenario 1 or 2           │
        └──────────────┬───────────────┘
                       │
            ┌──────────▼──────────────┐
            │ Does payment reference   │
            │ a valid active policy?   │
            └──────────┬──────────────┘
                       │
             ┌───YES───┴───NO───┐
             │                  │
             ▼                  │
    ┌────────────────────┐      │
    │ Amount matches      │      │
    │ expected premium    │      │
    │ (variance ≤ 15%)?   │      │
    └─────────┬──────────┘      │
              │                 │
     ┌──YES───┴───NO───┐       │
     │                 │       │
     ▼                 │       │
┌──────────────┐       │       │
│ Third-party  │       │       │
│ detected?    │       │       │
│              │       │       │
│ Check:       │       │       │
│ - Corporate  │       │       │
│   patterns   │       │       │
│ - Shared     │       │       │
│   last name  │       │       │
│ - Historical │       │       │
│   3rd-party  │       │       │
└──────┬───────┘       │       │
       │               │       │
  ┌─YES┴──NO──┐        │       │
  │           │        │       │
  ▼           │        │       │
┌────────┐    │        │       │
│  HOLD  │    │        │       │
│"Third- │    │        │       │
│ party  │    │        │       │
│payment"│    │        │       │
│Conf:   │    │        │       │
│40-60%  │    │        │       │
└────────┘    │        │       │
              ▼        ▼       ▼
         ┌─────────────────────────┐
         │       ESCALATE          │
         │                         │
         │ Provide:                │
         │ - Best fuzzy match      │
         │ - Amount correlation    │
         │ - Possible explanations │
         │ Confidence: 0%          │
         └─────────────────────────┘
```

---

## Edge Cases to Consider

### Case 1: Third-Party Payment With Valid Policy Reference
```
Payment from "XYZ Company Payroll"
Reference: "POL-12345"
Policy exists, amount matches premium

→ HOLD (third-party detected via corporate name pattern)
→ Approval: Verify authorized third-party payer
```

### Case 1b: Third-Party Payment Without Policy Reference
```
Payment from "XYZ Company Payroll"
No policy reference, no amount match

→ ESCALATE (cannot verify intent)
→ Investigation: Identify employee, verify payment purpose
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
