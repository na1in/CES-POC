# Final Scenario Definitions - AI Agent PoC
## Payment Exception Resolution - Authoritative Specification

**Document Version**: 1.0 Final
**Date**: February 27, 2026
**Status**: Approved
**Purpose**: Definitive scenario specifications with inputs, signals, decision logic, and expected outputs

---

## Configuration Parameters

All thresholds defined in this document are configurable:

```json
{
  "scenario_1_thresholds": {
    "name_similarity_apply": 95,
    "name_similarity_hold_min": 75,
    "amount_tolerance_percentage": 2
  },
  "scenario_2_thresholds": {
    "customer_exact_match": 100,
    "amount_variance_threshold": 15,
    "supporting_signals_required": 2
  },
  "scenario_3_variance_tiers": {
    "acceptable": 2,
    "minor_variance": 15,
    "moderate_variance": 50,
    "high_variance": 100
  },
  "scenario_4_thresholds": {
    "no_match_threshold": 75
  },
  "scenario_5_thresholds": {
    "duplicate_time_window_hours": 72,
    "exact_match_required": true
  }
}
```

---

## Scenario 1: Strong Policy Match (Auto-Apply Recommendation)

### Description
Payment with high confidence match to known policyholder and expected premium amount, with no risk flags. This represents the ideal case for automated processing.

### Payment Input Data
```json
{
  "payment_id": "PMT-2024-001",
  "amount": 5000.00,
  "currency": "USD",
  "payment_date": "2024-02-15",
  "payment_method": "Bank Transfer",
  "sender_name": "John A Smith",
  "sender_account": "****1234",
  "beneficiary_name": "John Smith",
  "reference_field_1": "POL-12345",
  "reference_field_2": "Premium Payment",
  "bank_reference": "REF-987654"
}
```

### Policy/Customer Data Available
```json
{
  "policy_number": "POL-12345",
  "policy_holder_name": "John Smith",
  "policy_status": "Active",
  "premium_amount": 5000.00,
  "premium_frequency": "Annual",
  "last_payment_date": "2023-02-12",
  "expected_next_payment": "2024-02-15",
  "customer_id": "CUST-5678",
  "policy_type": "Life Insurance"
}
```

### Required Data Fields

**Incoming Payment:**
- `Sender_Name` (required)
- `Payment_Amount` (required)
- `Payment_Date` (required)
- `Payment_Type` (required)
- `Reference_Field_1`, `Reference_Field_2` (optional but valuable)

**System - Policy Database:**
- `Policy_Holder_Name`
- `Expected_Premium_Amount`
- `Policy_Status`
- `Policy_Number`

**System - Payment History:**
- `Last_Payment_Amount`
- `Last_Payment_Method`
- `Last_Payment_Account_Ref`

### Signals to Compute

1. **Name_Similarity_Score**
   - Algorithm: Jaro-Winkler or Levenshtein distance
   - Comparison: `Sender_Name` vs `Policy_Holder_Name`
   - Output: Percentage (0-100)
   - Example: "John A Smith" vs "John Smith" = 92%

2. **Amount_Variance_Percentage**
   - Formula: `((Payment_Amount - Expected_Premium) / Expected_Premium) * 100`
   - Output: Percentage
   - Example: (5000 - 5000) / 5000 * 100 = 0%

3. **Risk_Flag_Present**
   - Check for: Payment fraud history, chronic late payer, account suspension, etc.
   - Output: Boolean + flag types
   - Example: False (no flags)

4. **Policy_Match_Confidence**
   - Direct policy number match in reference fields
   - Output: Percentage (0-100)
   - Example: "POL-12345" in reference_field_1 = 100%

5. **Payment_Timing_Match**
   - Compare payment_date to expected_due_date
   - Output: Days difference + quality rating
   - Example: 0 days difference = EXCELLENT

### Decision Logic

**APPLY Conditions:**
```
IF Name_Similarity_Score > 95%
AND Amount_Variance_Percentage <= 2%
AND Risk_Flag_Present == False
AND Policy_Status == "Active"
THEN APPLY (auto-apply without approval)
```

**HOLD Conditions:**
```
IF Name_Similarity_Score >= 75% AND < 95%
AND Amount_Variance_Percentage <= 2%
AND Risk_Flag_Present == False
THEN HOLD (apply with approval required)

OR

IF Risk_Flag_Present == True (high risk)
THEN HOLD (regardless of other scores)
```

**ESCALATE Conditions:**
```
IF Name_Similarity_Score < 75%
THEN ESCALATE (insufficient match confidence)
```

### Expected Agent Output

```json
{
  "payment_id": "PMT-2024-001",
  "recommendation": "APPLY",
  "confidence_score": 95,
  "matched_policy": "POL-12345",
  "matched_customer": "CUST-5678",
  "requires_human_approval": false,
  "reasoning": [
    "Policy number POL-12345 explicitly provided in reference field (100% match)",
    "Name similarity: 92% (John A Smith vs John Smith - middle initial variation)",
    "Amount exactly matches expected annual premium: $5,000 (0% variance)",
    "Payment received on expected due date (2024-02-15)",
    "No risk flags detected",
    "Policy status: Active"
  ],
  "suggested_action": "Allocate payment to Policy POL-12345",
  "signals_computed": {
    "name_similarity_score": 92,
    "amount_variance_percentage": 0,
    "risk_flag_present": false,
    "policy_match_confidence": 100,
    "payment_timing_match": "EXCELLENT"
  },
  "audit_trail": {
    "timestamp": "2024-02-15T10:30:00Z",
    "processing_time_ms": 145,
    "agent_version": "1.0",
    "decision_path": "scenario_1_auto_apply"
  }
}
```

---

## Scenario 2: Likely Customer Match, No Policy Reference

### Description
Payment missing explicit policy reference but sender matches known customer. Requires disambiguation when multiple policies exist.

### Payment Input Data
```json
{
  "payment_id": "PMT-2024-002",
  "amount": 1250.00,
  "currency": "USD",
  "payment_date": "2024-02-20",
  "payment_method": "Credit Card",
  "sender_name": "Sarah Johnson",
  "sender_account": "****5678",
  "beneficiary_name": "CES Insurance",
  "reference_field_1": "",
  "reference_field_2": "Insurance Payment",
  "bank_reference": "CC-445566"
}
```

### Customer Data Available
```json
{
  "customer_id": "CUST-9012",
  "customer_name": "Sarah M Johnson",
  "active_policies": [
    {
      "policy_number": "POL-67890",
      "policy_type": "Auto Insurance",
      "premium_amount": 1250.00,
      "premium_frequency": "Quarterly",
      "last_payment": "2023-11-18",
      "status": "Active"
    },
    {
      "policy_number": "POL-67891",
      "policy_type": "Home Insurance",
      "premium_amount": 850.00,
      "premium_frequency": "Monthly",
      "status": "Active"
    }
  ],
  "historical_payments": [
    {"date": "2023-11-18", "amount": 1250.00, "policy": "POL-67890"},
    {"date": "2023-08-15", "amount": 1250.00, "policy": "POL-67890"}
  ]
}
```

### Required Data Fields

**Incoming Payment:**
- `Sender_Name` (required)
- `Payment_Amount` (required)
- `Payment_Date` (required)
- `Payment_Type` (required)
- `Policy_Reference` (may be null, empty, or partial)

**System - Customer Database:**
- `Customer_Record` (Name, contact info)
- `Active_Policies` linked to customer
- `Historical_Premium_Amounts`
- `Past_Payment_Habits`

### Signals to Compute

1. **Sender_Customer_Match_Confidence**
   - Exact name match: 100%
   - Fuzzy match: <100%
   - Output: Percentage + match type

2. **Supporting_Signals** (when exact match not available)
   - Account number match: +1 signal
   - Amount matches expected premium: +1 signal
   - Historical payment pattern match: +1 signal
   - Minimum required: 2 supporting signals

3. **Active_Policy_Count**
   - Count of active policies for matched customer
   - Output: Integer

4. **Amount_To_Policy_Match**
   - Which active policies have matching premium amounts
   - Output: List of matching policies

5. **Historical_Amount_Match**
   - Does amount match historical payment pattern
   - Output: Boolean

6. **Amount_Variance_Percentage**
   - Variance from expected premium
   - Output: Percentage

### Decision Logic

**Case 1: 100% Exact Customer Match**

```
IF Customer_Match_Confidence == 100%:

  IF Policy_Reference is NULL or EMPTY:
    # Missing reference case
    IF Active_Policy_Count == 1:
      IF Amount_Variance_Percentage <= 15%:
        APPLY with approval required
      ELSE:
        ESCALATE to Scenario 3 (high variance)

    ELIF Active_Policy_Count > 1:
      # Check if amount uniquely identifies one policy
      IF Exactly_One_Policy_Matches_Amount:
        IF Amount_Variance_Percentage <= 15%:
          APPLY with approval required
        ELSE:
          HOLD (amount variance too high)
      ELSE:
        HOLD (multiple policies, manual selection needed)

  ELIF Policy_Reference is PARTIAL:
    # Partial reference case (e.g., last 5 digits)
    Matching_Policies = Filter_Policies_By_Partial_Reference(Policy_Reference)

    IF len(Matching_Policies) == 1:
      IF Amount_Variance_Percentage <= 15%:
        APPLY with approval required
      ELSE:
        ESCALATE to Scenario 3 (high variance)
    ELSE:
      HOLD (partial reference matches multiple policies)
```

**Case 2: Multiple Supporting Signals (No 100% Exact Match)**

```
IF Customer_Match_Confidence < 100%:
  Supporting_Signal_Count = 0

  IF Account_Number_Matches_Historical: Supporting_Signal_Count += 1
  IF Amount_Matches_Expected_Premium: Supporting_Signal_Count += 1
  IF Historical_Payment_Pattern_Matches: Supporting_Signal_Count += 1

  IF Supporting_Signal_Count >= 2:
    IF Active_Policy_Count == 1:
      IF Amount_Variance_Percentage <= 15%:
        APPLY with approval required
      ELSE:
        HOLD
    ELSE:
      HOLD (multiple policies, need clarification)
  ELSE:
    ESCALATE (insufficient confidence)
```

### Expected Agent Output

**Example: Single Policy, Missing Reference**
```json
{
  "payment_id": "PMT-2024-002",
  "recommendation": "APPLY",
  "confidence_score": 88,
  "matched_customer": "CUST-9012",
  "matched_policy": "POL-67890",
  "requires_human_approval": true,
  "approval_reason": "Policy number not explicitly provided - requires verification",
  "reasoning": [
    "Customer identified: Sarah M Johnson (100% exact match with Sarah Johnson)",
    "Customer has 2 active policies",
    "Amount $1,250 matches exactly ONE active policy (POL-67890 - Auto Insurance)",
    "Amount variance: 0% (perfect match)",
    "Historical pattern: Customer has paid $1,250 quarterly for this policy",
    "Payment timing consistent with quarterly frequency",
    "No risk flags detected"
  ],
  "suggested_action": "Allocate payment to Policy POL-67890 (Auto Insurance)",
  "alternative_matches": [],
  "signals_computed": {
    "customer_match_confidence": 100,
    "active_policy_count": 2,
    "amount_matching_policies": 1,
    "amount_variance_percentage": 0,
    "historical_amount_match": true
  },
  "audit_trail": {
    "timestamp": "2024-02-20T14:15:00Z",
    "processing_time_ms": 267,
    "decision_path": "scenario_2_single_amount_match"
  }
}
```

---

## Scenario 3: High Amount Variance (Hold Recommendation)

### Description
Payment amount deviates from expected premium by more than acceptable tolerance. Uses multi-tier variance thresholds for appropriate handling.

### Variance Tier Definitions

```
Tier 1: 0-2%      → APPLY (acceptable tolerance)
Tier 2: 2-15%     → APPLY with approval (minor variance)
Tier 3: 15-50%    → HOLD (moderate variance - Scenario 3 primary focus)
Tier 4: 50-100%   → HOLD (high variance - investigation required)
Tier 5: >100%     → ESCALATE (extreme variance - potential fraud/major error)
```

### Payment Input Data
```json
{
  "payment_id": "PMT-2024-003",
  "amount": 3000.00,
  "currency": "USD",
  "payment_date": "2024-02-22",
  "payment_method": "Wire Transfer",
  "sender_name": "Robert Chen",
  "sender_account": "****9999",
  "beneficiary_name": "Robert Chen",
  "reference_field_1": "POL-11223",
  "reference_field_2": "Premium",
  "bank_reference": "WIRE-778899"
}
```

### Policy Data Available
```json
{
  "policy_number": "POL-11223",
  "policy_holder_name": "Robert Chen",
  "policy_status": "Active",
  "premium_amount": 2500.00,
  "premium_frequency": "Annual",
  "last_payment_date": "2023-02-15",
  "last_payment_amount": 2500.00,
  "policy_type": "Life Insurance",
  "historical_payments": [
    {"date": "2023-02-15", "amount": 2500.00},
    {"date": "2022-02-18", "amount": 2500.00},
    {"date": "2021-02-20", "amount": 2400.00}
  ]
}
```

### Required Data Fields

**Incoming Payment:**
- `Payment_Amount` (required)
- `Sender_Name` (required)
- `Payment_Date` (required)
- `Payment_Type` (required)
- `Policy_Reference` (required)

**System - Policy Database:**
- `Expected_Premium_Amount`
- `Historical_Payment_Average`
- `Policy_Modification_History`

**System - Payment History:**
- Last 6-12 payments for pattern analysis

### Signals to Compute

1. **Name_Similarity_Score**
   - Must be 100% for Scenario 3 (otherwise escalate to Scenario 4)
   - Output: Percentage

2. **Amount_Variance_Percentage**
   - Formula: `((Payment_Amount - Expected_Premium) / Expected_Premium) * 100`
   - Output: Percentage
   - Example: ((3000 - 2500) / 2500) * 100 = 20%

3. **Variance_Tier**
   - Classify variance into tiers
   - Output: Tier number (1-5)

4. **Historical_Pattern_Consistency**
   - Compare to historical payment amounts
   - Calculate mean and standard deviation
   - Output: Consistency score + outlier flag

5. **Multi_Period_Payment_Indicator**
   - Check if amount represents multiple premium periods
   - Formula: `round(Payment_Amount / Expected_Premium)`
   - Output: Boolean + estimated periods

6. **Policy_Modification_Check**
   - Check for recent policy changes that might explain variance
   - Output: Boolean + modification details

### Decision Logic

```python
# First verify name/policy match
IF Name_Similarity_Score < 100%:
  ESCALATE to Scenario 4 (customer match issue)

# Calculate variance
Amount_Variance_Percentage = ((Payment_Amount - Expected_Premium) / Expected_Premium) * 100
Absolute_Variance = abs(Amount_Variance_Percentage)

# Tier-based decision
IF Absolute_Variance <= 2%:
  # Tier 1: Acceptable
  APPLY (no approval needed)

ELIF Absolute_Variance > 2% AND Absolute_Variance <= 15%:
  # Tier 2: Minor variance
  APPLY with approval required
  Reason = "Minor amount variance requires verification"

ELIF Absolute_Variance > 15% AND Absolute_Variance <= 50%:
  # Tier 3: Moderate variance - PRIMARY SCENARIO 3 FOCUS
  HOLD for manual review
  Reason = "Moderate variance - verify customer intent and policy status"

  # Check if multi-period payment
  Period_Multiplier = round(Payment_Amount / Expected_Premium)
  IF abs(Payment_Amount - (Expected_Premium * Period_Multiplier)) < (Expected_Premium * 0.05):
    Note = "May be multi-period payment (approximately {Period_Multiplier}x premium)"

ELIF Absolute_Variance > 50% AND Absolute_Variance <= 100%:
  # Tier 4: High variance
  HOLD for investigation
  Reason = "High variance - verify policy modifications and customer intent"
  Risk_Flag = "HIGH_AMOUNT_VARIANCE"

ELIF Absolute_Variance > 100%:
  # Tier 5: Extreme variance
  ESCALATE to investigation queue
  Reason = "Extreme variance - potential fraud, major error, or significant policy change"
  Risk_Flag = "EXTREME_VARIANCE"
```

### Expected Agent Output

**Example: Tier 3 (20% variance - Moderate)**
```json
{
  "payment_id": "PMT-2024-003",
  "recommendation": "HOLD",
  "confidence_score": 70,
  "matched_policy": "POL-11223",
  "matched_customer": "CUST-3344",
  "requires_human_approval": true,
  "approval_reason": "Amount variance (20%) exceeds acceptable threshold (15%)",
  "reasoning": [
    "Policy number POL-11223 and name Robert Chen match correctly (100%)",
    "ALERT: Payment amount $3,000 is 20% higher than expected premium $2,500",
    "Variance tier: MODERATE (15-50% range)",
    "Historical pattern shows consistent annual payments of ~$2,500",
    "No policy modification records found to explain increase",
    "Possible scenarios: Partial overpayment, Premium adjustment not yet recorded, Customer intent to prepay"
  ],
  "suggested_action": "Hold in suspense account for manual review",
  "investigation_required": [
    "Verify customer intent - did they mean to pay $3,000?",
    "Check for recent policy modifications or upgrades not yet in system",
    "Confirm if customer wants to apply $2,500 and refund $500",
    "Validate no data entry error in payment amount"
  ],
  "signals_computed": {
    "name_similarity_score": 100,
    "amount_variance_percentage": 20,
    "variance_tier": 3,
    "variance_classification": "MODERATE_VARIANCE",
    "historical_pattern_consistency": 98,
    "multi_period_indicator": false,
    "policy_modification_found": false
  },
  "risk_flags": ["MODERATE_AMOUNT_VARIANCE"],
  "audit_trail": {
    "timestamp": "2024-02-22T09:45:00Z",
    "processing_time_ms": 189,
    "decision_path": "scenario_3_tier_3_moderate_variance"
  }
}
```

**Example: Tier 5 (>100% variance - Extreme)**
```json
{
  "payment_id": "PMT-2024-003B",
  "recommendation": "ESCALATE",
  "confidence_score": 40,
  "matched_policy": "POL-11223",
  "matched_customer": "CUST-3344",
  "requires_human_approval": true,
  "approval_reason": "Extreme amount variance (>100%) - potential fraud or major error",
  "reasoning": [
    "Policy number POL-11223 and name Robert Chen match correctly (100%)",
    "CRITICAL ALERT: Payment amount $15,000 is 500% higher than expected premium $2,500",
    "Variance tier: EXTREME (>100% range)",
    "Historical pattern shows consistent annual payments of ~$2,500",
    "This could indicate: Major fraud attempt, Significant data error, Large multi-year prepayment, Policy upgrade not recorded"
  ],
  "suggested_action": "Escalate to investigation queue immediately",
  "investigation_required": [
    "PRIORITY: Verify payment authenticity",
    "Contact customer immediately to confirm intent",
    "Check for policy modifications or new policy applications",
    "Review for potential fraud indicators",
    "Validate payment source and method"
  ],
  "signals_computed": {
    "name_similarity_score": 100,
    "amount_variance_percentage": 500,
    "variance_tier": 5,
    "variance_classification": "EXTREME_VARIANCE"
  },
  "risk_flags": ["EXTREME_VARIANCE", "POTENTIAL_FRAUD"],
  "audit_trail": {
    "timestamp": "2024-02-22T09:45:00Z",
    "processing_time_ms": 189,
    "decision_path": "scenario_3_tier_5_extreme_variance"
  }
}
```

---

## Scenario 4: No Matching Customer (Escalate)

### Description
Payment sender and beneficiary do not match any known policyholder in the system. Maximum similarity score across entire database falls below acceptable threshold.

### Payment Input Data
```json
{
  "payment_id": "PMT-2024-004",
  "amount": 3500.00,
  "currency": "USD",
  "payment_date": "2024-02-23",
  "payment_method": "Check",
  "sender_name": "Alexandra Martinez",
  "sender_account": "",
  "beneficiary_name": "CES Insurance Co",
  "reference_field_1": "Insurance",
  "reference_field_2": "",
  "bank_reference": "CHK-112233"
}
```

### Search Results
```json
{
  "customer_search": {
    "exact_matches": 0,
    "fuzzy_matches": [
      {
        "customer_name": "Alexander Martinez",
        "similarity_score": 72,
        "customer_id": "CUST-7788",
        "status": "Inactive since 2022"
      },
      {
        "customer_name": "Alejandra Martin",
        "similarity_score": 65,
        "customer_id": "CUST-9900",
        "status": "Active"
      }
    ],
    "max_similarity_score": 72
  },
  "policy_search": {
    "reference_matches": 0,
    "amount_matches": []
  }
}
```

### Required Data Fields

**Incoming Payment:**
- `Sender_Name` (required)
- `Beneficiary_Name` (optional)
- `Payment_Amount` (required)
- `Payment_Date` (required)
- `Payment_Type` (required)

**System - Customer Database:**
- `Global_Policyholder_Database` (all active and inactive customers)

### Signals to Compute

1. **Name_Similarity_Score**
   - Run fuzzy matching across entire customer database
   - Use multiple algorithms: Levenshtein, Jaro-Winkler, Soundex
   - Output: Best match score (0-100)

2. **Max_Database_Similarity**
   - Highest similarity score found across all customers
   - Output: Percentage + matched customer details

3. **Policy_Reference_Match**
   - Search for any policy number in reference fields
   - Output: Boolean + matched policies

4. **Amount_Correlation**
   - Search for active policies with matching premium amounts
   - Output: List of policies with similar amounts

### Decision Logic

```python
# Search entire database for best match
Max_Similarity_Score = max([
    calculate_similarity(Payment.Sender_Name, Customer.Name)
    for Customer in All_Customers
])

IF Max_Similarity_Score < 75%:
  # Truly unknown customer
  ESCALATE to investigation queue
  Reason = "No matching customer found in database (Max similarity: {Max_Similarity_Score}%)"

ELIF Max_Similarity_Score >= 75% AND Max_Similarity_Score < 100%:
  # Potential match exists but not exact
  HOLD for manual review
  Reason = "Potential customer match found but not exact (Similarity: {Max_Similarity_Score}%)"
  # Provide potential matches for manual verification

ELSE:  # Max_Similarity_Score == 100%
  # This would route to Scenario 1 or 2
  # Should not reach this point in Scenario 4
```

### Expected Agent Output

```json
{
  "payment_id": "PMT-2024-004",
  "recommendation": "ESCALATE",
  "confidence_score": 0,
  "matched_customer": null,
  "matched_policy": null,
  "requires_human_approval": true,
  "approval_reason": "No matching customer or policy identified",
  "reasoning": [
    "No exact customer match found for 'Alexandra Martinez'",
    "Best fuzzy match: Alexander Martinez (72% similarity) - INACTIVE since 2022",
    "Maximum similarity score (72%) below acceptable threshold (75%)",
    "No policy reference provided in payment details",
    "Amount $3,500 does not match any active policy premium exactly",
    "Unable to determine customer intent with available information"
  ],
  "suggested_action": "Route to investigation queue for manual research",
  "investigation_required": [
    "Contact sender Alexandra Martinez to clarify intent",
    "Search for pending policy applications or quotes",
    "Verify if payment intended for CES Insurance or different company",
    "Check if customer recently changed name (marriage, legal change, etc.)",
    "Review if this is deposit for new policy application",
    "Search external systems or recent correspondence"
  ],
  "possible_scenarios": [
    "New policy application - premium deposit",
    "Misdirected payment to wrong insurance company",
    "Customer name change not yet updated in system",
    "Payment on behalf of another policyholder (third-party payment)",
    "Data entry error in sender name by bank",
    "Customer from recent acquisition not yet in system"
  ],
  "potential_matches": [
    {
      "customer_name": "Alexander Martinez",
      "similarity_score": 72,
      "customer_id": "CUST-7788",
      "status": "Inactive since 2022",
      "note": "Below threshold but closest match - verify if reactivation"
    },
    {
      "customer_name": "Alejandra Martin",
      "similarity_score": 65,
      "customer_id": "CUST-9900",
      "status": "Active",
      "note": "Second closest match - verify if name variation"
    }
  ],
  "signals_computed": {
    "max_database_similarity": 72,
    "exact_match_found": false,
    "policy_reference_match": false,
    "amount_correlation_found": false
  },
  "risk_flags": ["NO_CUSTOMER_MATCH", "NO_POLICY_REFERENCE"],
  "audit_trail": {
    "timestamp": "2024-02-23T11:20:00Z",
    "processing_time_ms": 312,
    "database_records_searched": 45823,
    "decision_path": "scenario_4_no_match"
  }
}
```

---

## Scenario 5: Duplicate Payment Suspicion

### Description
Payment precisely matches a recent transaction within 72-hour window, with 100% exact match on critical fields. Indicates potential accidental duplicate submission.

### Payment Input Data
```json
{
  "payment_id": "PMT-2024-005",
  "amount": 750.00,
  "currency": "USD",
  "payment_date": "2024-02-25T14:30:00Z",
  "payment_method": "ACH",
  "sender_name": "Emily Watson",
  "sender_account": "****4455",
  "beneficiary_name": "Emily Watson",
  "reference_field_1": "POL-99887",
  "reference_field_2": "Monthly Premium",
  "bank_reference": "ACH-556677"
}
```

### Recent Transaction History
```json
{
  "recent_payments": [
    {
      "payment_id": "PMT-2024-004A",
      "amount": 750.00,
      "payment_date": "2024-02-23T10:15:00Z",
      "sender_name": "Emily Watson",
      "sender_account": "****4455",
      "policy": "POL-99887",
      "status": "Applied",
      "payment_method": "ACH",
      "reference_field_1": "POL-99887",
      "reference_field_2": "Monthly Premium"
    }
  ]
}
```

### Policy Data
```json
{
  "policy_number": "POL-99887",
  "policy_holder_name": "Emily Watson",
  "policy_status": "Active",
  "premium_amount": 750.00,
  "premium_frequency": "Monthly",
  "next_due_date": "2024-03-20",
  "last_payment_applied": "2024-02-23",
  "outstanding_balance": 0.00
}
```

### Required Data Fields

**Incoming Payment:**
- `Payment_Amount` (required)
- `Sender_Name` (required)
- `Payment_Timestamp` (required)
- `Payment_Type` (required)
- `Policy_Reference` (required)
- `Sender_Account` (if available)

**System - Transaction History:**
- `Recent_Transaction_History` (last 72 hours)
- Query parameters: Same sender, same amount, same policy

### Signals to Compute

1. **Duplicate_Probability_Score**
   - Check 100% exact match on critical fields
   - Fields to match:
     - Amount (exact)
     - Sender name (exact)
     - Payment type/method (exact)
     - Policy reference (exact)
   - Output: Percentage (0 or 100 for exact match)

2. **Time_Between_Payments**
   - Calculate hours/days between current and previous payment
   - Output: Hours + interpretation

3. **Outstanding_Balance_Check**
   - Verify if policy has outstanding balance that justifies duplicate
   - Output: Balance amount + boolean

4. **Payment_Frequency_Analysis**
   - Compare time gap to expected payment frequency
   - Output: Expected vs actual days

5. **Account_Match**
   - Check if same sender account used
   - Output: Boolean

### Decision Logic

```python
# Search for matching payments in last 72 hours
Recent_Matching_Payments = search_payments(
    time_window_hours=72,
    filters={
        "sender_name": Payment.Sender_Name,
        "amount": Payment.Amount,
        "policy_reference": Payment.Policy_Reference,
        "payment_method": Payment.Payment_Method
    }
)

IF len(Recent_Matching_Payments) > 0:
  # Potential duplicate found
  Original_Payment = Recent_Matching_Payments[0]

  # Calculate exact match percentage
  Exact_Match_Fields = 0
  Total_Fields = 4

  IF Payment.Amount == Original_Payment.Amount: Exact_Match_Fields += 1
  IF Payment.Sender_Name == Original_Payment.Sender_Name: Exact_Match_Fields += 1
  IF Payment.Payment_Method == Original_Payment.Payment_Method: Exact_Match_Fields += 1
  IF Payment.Policy_Reference == Original_Payment.Policy_Reference: Exact_Match_Fields += 1

  Match_Percentage = (Exact_Match_Fields / Total_Fields) * 100

  IF Match_Percentage == 100:
    # 100% exact duplicate
    Hours_Between = (Payment.Timestamp - Original_Payment.Timestamp).total_hours()

    IF Hours_Between <= 72:
      # Check if there's a justifiable reason
      IF Policy.Outstanding_Balance > 0:
        # There's a balance, might be legitimate
        HOLD with note "Potential duplicate but outstanding balance exists"
      ELSE:
        # No outstanding balance, likely duplicate
        ESCALATE
        Reason = "Potential duplicate detected - 100% match within 72 hours"
        Risk_Flag = "POTENTIAL_DUPLICATE"
  ELSE:
    # Not exact match, continue normal processing
    Route to appropriate scenario (1, 2, or 3)
```

### Expected Agent Output

```json
{
  "payment_id": "PMT-2024-005",
  "recommendation": "ESCALATE",
  "confidence_score": 0,
  "matched_policy": "POL-99887",
  "matched_customer": "CUST-5566",
  "requires_human_approval": true,
  "approval_reason": "Potential duplicate payment detected",
  "reasoning": [
    "DUPLICATE ALERT: Matching payment detected",
    "Original payment: PMT-2024-004A for $750 on 2024-02-23 10:15 AM",
    "Current payment: PMT-2024-005 for $750 on 2024-02-25 02:30 PM",
    "Time between payments: 52 hours (within 72-hour duplicate window)",
    "100% exact match on all critical fields:",
    "  - Amount: $750 (exact match)",
    "  - Sender: Emily Watson (exact match)",
    "  - Payment method: ACH (exact match)",
    "  - Policy reference: POL-99887 (exact match)",
    "  - Account: ****4455 (exact match)",
    "Policy POL-99887 has $0 outstanding balance",
    "Next payment not due until 2024-03-20 (23 days away)",
    "Duplicate probability: 100%"
  ],
  "suggested_action": "Flag as potential duplicate and escalate for customer verification",
  "investigation_required": [
    "Contact Emily Watson immediately to confirm if duplicate or intentional",
    "Verify if customer changed payment authorization settings by mistake",
    "Check if first payment (PMT-2024-004A) processed correctly or needs reversal",
    "Confirm if customer wants to prepay next month (March)",
    "Review ACH payment setup for automatic deduction errors",
    "Check bank for duplicate transaction submission"
  ],
  "possible_scenarios": [
    "Accidental duplicate submission (customer clicked submit twice)",
    "Intentional advance payment for next month (early payment)",
    "Payment method error causing double debit",
    "Customer forgot they already paid",
    "System or bank processing error",
    "ACH automatic payment + manual payment overlap"
  ],
  "recommended_resolution_options": [
    "Hold second payment in suspense and contact customer for clarification",
    "Apply to next month (March 2024) if customer confirms intentional advance payment",
    "Refund second payment if customer confirms duplicate",
    "Keep in suspense until customer responds to inquiry"
  ],
  "duplicate_details": {
    "original_payment_id": "PMT-2024-004A",
    "original_payment_date": "2024-02-23T10:15:00Z",
    "hours_between_payments": 52,
    "expected_frequency_days": 30,
    "match_details": {
      "amount_match": "exact",
      "sender_match": "exact",
      "payment_method_match": "exact",
      "policy_reference_match": "exact",
      "account_match": true
    },
    "exact_match_percentage": 100
  },
  "signals_computed": {
    "duplicate_probability_score": 100,
    "time_between_payments_hours": 52,
    "outstanding_balance": 0,
    "payment_frequency_expected_days": 30,
    "account_match": true
  },
  "risk_flags": ["POTENTIAL_DUPLICATE", "TIMING_ANOMALY"],
  "audit_trail": {
    "timestamp": "2024-02-25T14:30:00Z",
    "processing_time_ms": 201,
    "decision_path": "scenario_5_duplicate_detected"
  }
}
```

---

## Cross-Scenario Decision Flow

```
Payment Received
    ↓
[Check for duplicate in last 72 hours]
    ↓
    YES → Scenario 5 (Duplicate Detection)
    NO → Continue
    ↓
[Search for customer match]
    ↓
    Max similarity < 75% → Scenario 4 (No Match - Escalate)
    ↓
    Max similarity >= 75%
    ↓
[Check name similarity score]
    ↓
    < 75% → Scenario 4 (Escalate)
    75-95% → Continue with Hold flag
    > 95% → Continue with Apply flag
    ↓
[Check amount variance]
    ↓
    0-2% → Apply (or Hold if name 75-95%)
    2-15% → Apply with approval
    15-50% → Scenario 3 Tier 3 (Hold)
    50-100% → Scenario 3 Tier 4 (Hold)
    > 100% → Scenario 3 Tier 5 (Escalate)
    ↓
[Check policy reference]
    ↓
    Policy# provided → Scenario 1 (Strong Match)
    Policy# missing/partial → Scenario 2 (Customer Match)
```

---

## Summary Decision Matrix

| Scenario | Primary Condition | Confidence | Action | Approval Required |
|----------|------------------|------------|--------|-------------------|
| 1 | Name ≥95%, Amount ≤2% variance, Policy# provided | 90-100% | APPLY | No |
| 1 (Hold) | Name 75-95%, Amount ≤2% variance | 75-89% | HOLD/APPLY | Yes |
| 2 | 100% customer match, No policy# OR supporting signals | 75-89% | APPLY | Yes |
| 2 (Hold) | 100% customer match, Multiple policies | 70-85% | HOLD | Yes |
| 3 (Tier 2) | Perfect match, 2-15% variance | 85-90% | APPLY | Yes |
| 3 (Tier 3) | Perfect match, 15-50% variance | 60-75% | HOLD | Yes |
| 3 (Tier 4) | Perfect match, 50-100% variance | 40-60% | HOLD | Yes |
| 3 (Tier 5) | Perfect match, >100% variance | 0-40% | ESCALATE | Yes |
| 4 | Name similarity <75% | 0% | ESCALATE | Yes |
| 5 | 100% duplicate match, <72 hours | 0% | ESCALATE | Yes |

---

## Standard Output Format

All scenarios must return output in this format:

```json
{
  "payment_id": "string",
  "recommendation": "APPLY | HOLD | ESCALATE",
  "confidence_score": 0-100,
  "matched_policy": "string or null",
  "matched_customer": "string or null",
  "requires_human_approval": boolean,
  "approval_reason": "string or null",
  "reasoning": ["array", "of", "explanation", "strings"],
  "suggested_action": "string",
  "investigation_required": ["optional", "array"],
  "possible_scenarios": ["optional", "array"],
  "signals_computed": {
    "signal_name": "value"
  },
  "risk_flags": ["optional", "array"],
  "audit_trail": {
    "timestamp": "ISO 8601",
    "processing_time_ms": integer,
    "decision_path": "string"
  }
}
```

---

**End of Document**
