# Scenario 2: Likely Customer Match, No Policy Reference

# Scenario Description

Payment is missing explicit policy reference, but sender matches a known customer. Requires policy disambiguation when customer has multiple active policies.

**Example**: Customer "Sarah Johnson" pays $1,250 but doesn't provide policy number. System finds customer "Sarah M Johnson" with 2 active policies - one for $1,250 (Auto) and one for $850 (Home).

---

## When Does This Scenario Apply?

- Policy number is **missing, empty, or partial** in payment reference
- Sender name matches a known customer (exact or with supporting signals)
- Customer may have one or multiple active policies
- Amount may help identify the correct policy

---

## Configuration Thresholds

| Parameter | Value | Description |
|-----------|-------|-------------|
| **Customer Name Match** | ≥90% | Name similarity threshold to proceed |
| **Supporting Signals Required** | 2+ | When name match is below 90% |
| **Amount Variance Threshold** | 15% | If exceeded, routes to Scenario 3 |

> **Design Note (from sponsor feedback):** The original threshold of 100% exact match is
> unrealistic for existing policies. Name variations are extremely common in insurance:
> - Wedding name changes: "Sarah Miller" → "Sarah Johnson"
> - Middle name/initial: "Sarah Johnson" vs "Sarah M Johnson"
> - Name format: "Johnson Sarah" vs "Sarah Johnson"
> - Typos in historical records
>
> For this reason, the threshold is set to **≥90%** using the hybrid name matching
> approach (traditional algorithms + LLM fallback for gray-zone cases).

---

## Decision Logic

### **Prerequisite Check: Customer Match**

```
Option A: Strong Customer Name Match
  IF Customer_Name_Similarity ≥ 90%
  THEN proceed with scenario

Option B: Weaker Name Match + Supporting Signals
  IF Customer_Name_Similarity < 90%
     BUT ≥2 supporting signals are true:
       - Account_Number_Match = True
       - Amount_Matches_Expected = True
       - Historical_Pattern_Match = True
  THEN proceed with scenario

  ELSE → ESCALATE to Scenario 4
```

### **Step 1: Check Amount Variance**

```
IF Amount_Variance > 15%
THEN → Route to Scenario 3 (variance handling)
ELSE → Continue
```

### **Step 2: Handle Missing Policy Reference**

```
IF Policy_Reference is NULL or EMPTY:

  IF Customer has exactly 1 active policy:
    IF Amount_Variance ≤ 15%:
      THEN → APPLY with approval required
    ELSE:
      THEN → Route to Scenario 3

  IF Customer has >1 active policy:
    IF Amount matches exactly 1 policy (±2%):
      THEN → APPLY with approval required
      Note: "Amount uniquely identifies policy"
    ELSE:
      THEN → HOLD
      Reason: "Multiple policies, manual selection needed"
```

### **Step 3: Handle Partial Policy Reference**

```
IF Policy_Reference is PARTIAL (e.g., last 5 digits):

  Matching_Policies = Filter by partial reference

  IF Exactly 1 policy matches partial reference:
    IF Amount_Variance ≤ 15%:
      THEN → APPLY with approval required
    ELSE:
      THEN → Route to Scenario 3

  IF >1 policy matches partial reference:
    THEN → HOLD
    Reason: "Partial reference not unique"
```

---

## Required Input Data

**Payment Information:**
- Sender Name (required)
- Payment Amount (required)
- Payment Date (required)
- Payment Method (required)
- Policy Reference (may be null, empty, or partial)
- Sender Account (very helpful for supporting signals)

**System Data:**
- Customer database with all active customers
- All active policies for matched customer
- Historical payment patterns per customer
- Expected premium amounts per policy

---

## Key Signals to Compute

### 1. Customer Match Confidence (0-100%)
- Exact name match = 100%
- Strong match (format/initial variations) = 90-99%
- Fuzzy match with larger variations < 90%
- No match = 0%
- **Threshold to proceed: ≥90%** (or <90% with 2+ supporting signals)
- Uses hybrid name matching (traditional + Haiku LLM for gray zone)

### 2. Supporting Signals (Boolean, each)
- **Account Number Match**: Sender account matches historical account
- **Amount Match**: Payment amount matches expected premium for a policy
- **Historical Pattern Match**: Amount and timing match historical pattern

### 3. Active Policy Count (Integer)
- Number of active policies for matched customer
- Critical for disambiguation

### 4. Amount-to-Policy Match (List)
- Which active policies have matching premium amounts
- Identifies if amount uniquely points to one policy

### 5. Amount Variance Percentage
- Variance from expected premium
- >15% routes to Scenario 3

---

## Example Scenarios

### Example 1: Single Policy, Missing Reference

**Input:**
```json
{
  "payment_id": "PMT-201",
  "amount": 1250.00,
  "sender_name": "Sarah Johnson",
  "reference_field_1": "",
  "sender_account": "****5678"
}
```

**Customer Data:**
```json
{
  "customer_id": "CUST-9012",
  "customer_name": "Sarah Johnson",
  "active_policies": [
    {
      "policy_number": "POL-67890",
      "premium_amount": 1250.00,
      "policy_type": "Auto"
    }
  ]
}
```

**Agent Output:**
- **Recommendation**: APPLY with approval
- **Confidence**: 85%
- **Matched Policy**: POL-67890
- **Reasoning**: "Customer 'Sarah Johnson' matched exactly (100%). Customer has 1 active policy. Amount matches expected premium perfectly. Policy number not provided - requires verification."

---

### Example 2: Multiple Policies, Amount Identifies One

**Input:**
```json
{
  "payment_id": "PMT-202",
  "amount": 1250.00,
  "sender_name": "Sarah M Johnson",
  "reference_field_1": ""
}
```

**Customer Data:**
```json
{
  "customer_id": "CUST-9012",
  "customer_name": "Sarah Johnson",
  "active_policies": [
    {
      "policy_number": "POL-67890",
      "premium_amount": 1250.00,
      "policy_type": "Auto"
    },
    {
      "policy_number": "POL-67891",
      "premium_amount": 850.00,
      "policy_type": "Home"
    }
  ]
}
```

**Agent Output:**
- **Recommendation**: APPLY with approval
- **Confidence**: 82%
- **Matched Policy**: POL-67890
- **Reasoning**: "Customer 'Sarah M Johnson' matched to 'Sarah Johnson' with 95% similarity (middle initial variation). Customer has 2 active policies. Amount $1,250 matches exactly ONE policy (POL-67890 - Auto). Requires approval for policy verification."

---

### Example 3: Multiple Policies, Cannot Disambiguate

**Input:**
```json
{
  "payment_id": "PMT-203",
  "amount": 1000.00,
  "sender_name": "Michael Chen"
}
```

**Customer Data:**
```json
{
  "customer_id": "CUST-4455",
  "customer_name": "Michael Chen",
  "active_policies": [
    {
      "policy_number": "POL-11111",
      "premium_amount": 1000.00,
      "policy_type": "Life"
    },
    {
      "policy_number": "POL-22222",
      "premium_amount": 1000.00,
      "policy_type": "Auto"
    }
  ]
}
```

**Agent Output:**
- **Recommendation**: HOLD
- **Confidence**: 75%
- **Matched Policy**: null (ambiguous)
- **Reasoning**: "Customer matched exactly (100%). Customer has 2 active policies with SAME premium amount ($1,000). Cannot determine which policy to apply payment to. Manual selection required."

---

## Flow Diagram

```
             ┌────────────────────────────┐
             │ Payment with missing/      │
             │ partial policy reference   │
             └─────────────┬──────────────┘
                           │
                ┌──────────▼──────────┐
                │ Customer Name       │
                │ Match ≥ 90%?        │
                └──────────┬──────────┘
                           │
                 ┌───YES───┴───NO────┐
                 │                   │
                 │                   ▼
                 │        ┌─────────────────────┐
                 │        │ Check Supporting     │
                 │        │ Signals (need ≥2):   │
                 │        │                     │
                 │        │ ☐ Account Number    │
                 │        │   matches historical│
                 │        │ ☐ Amount matches    │
                 │        │   expected premium  │
                 │        │ ☐ Historical pattern│
                 │        │   matches (timing + │
                 │        │   amount)           │
                 │        └──────────┬──────────┘
                 │                   │
                 │          ┌───≥2───┴───<2───┐
                 │          │                 │
                 │          │                 ▼
                 │          │           ┌───────────┐
                 │          │           │ ESCALATE  │
                 │          │           │(Scenario 4)│
                 │          │           └───────────┘
                 │          │
                 └────┬─────┘
                      │
              Customer Matched
                      │
           ┌──────────▼──────────┐
           │ Amount Variance     │
           │ >15%?               │
           └──────────┬──────────┘
                      │
            ┌───YES───┴───NO───┐
            │                  │
            ▼                  ▼
     ┌─────────────┐  ┌───────────────┐
     │ Route to    │  │ Policy ref    │
     │ Scenario 3  │  │ status?       │
     └─────────────┘  └───────┬───────┘
                              │
                ┌─────────────┼──────────────┐
                │             │              │
            NULL/EMPTY    PARTIAL        FULL (N/A)
                │             │
                ▼             ▼
      ┌─────────────┐  ┌──────────────────┐
      │ How many    │  │ How many policies│
      │ active      │  │ match partial    │
      │ policies?   │  │ reference?       │
      └──────┬──────┘  └───────┬──────────┘
             │                 │
      ┌──────┴──────┐   ┌─────┴──────┐
      │             │   │            │
    1 policy    >1 policy  Exactly 1   >1
      │             │       │          │
      ▼             ▼       ▼          ▼
  ┌────────┐  ┌──────────────┐    ┌────────┐
  │ APPLY  │  │ Amount match │    │  HOLD  │
  │  with  │  │ exactly 1    │    │"Partial│
  │approval│  │ policy (±2%)?│    │ref not │
  └────────┘  └──────┬───────┘    │unique" │
                     │            └────────┘
              ┌─YES──┴──NO──┐
              │             │
              ▼             ▼
        ┌────────┐    ┌────────┐
        │ APPLY  │    │  HOLD  │
        │  with  │    │"Manual │
        │approval│    │select" │
        └────────┘    └────────┘
```

---

## Edge Cases to Consider

### Case 1: Amount Variance Exceeds 15%
```
Customer: 100% match
Active Policies: 1
Amount: $1,500
Expected: $1,250
Variance: 20%

→ Route to Scenario 3 (variance handling)
→ NOT Scenario 2 anymore
```

### Case 2: Multiple Policies, Amount Close to Multiple
```
Customer: 100% match
Policy 1: $1,250 premium
Policy 2: $1,200 premium
Payment: $1,225

→ HOLD - Cannot determine which policy
→ Manual review needed
```

### Case 3: New Customer (First Payment)
```
Customer: 100% match
Active Policies: 1
Historical Payments: 0

→ APPLY with approval
→ Note: "First payment for this customer - verify setup"
```
