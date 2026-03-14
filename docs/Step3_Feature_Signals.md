# Step 3: Feature Signals Identification

# Signal Categories

The feature signals are organized into 5 main categories:
1. **Matching & Identification Signals**
2. **Amount & Variance Signals**
3. **Temporal & Pattern Signals**
4. **Risk & Fraud Detection Signals**
5. **Duplicate Detection Signals**

---

## 1. Matching & Identification Signals

### 1.1 Policy Match Confidence
**Description**: Confidence score indicating how well the payment matches to a specific policy.

**Computation Method**:
- Direct policy number match in reference fields: 100%
- Fuzzy match of policy number with typos: 70-95%
- No policy number but strong indirect match: 60-80%
- No match: 0%

**Output**: Numeric score (0-100)

**Used In**: All scenarios

---

### 1.2 Name Similarity Score
**Description**: Detailed name comparison between payment sender and policy holder.

**Computation Method**:
- Use multiple algorithms: Levenshtein, Jaro-Winkler, Soundex
- Handle common variations: middle initials, nicknames, spelling
- Normalize: lowercase, remove special characters, handle prefixes/suffixes

**Output**: Numeric score (0-100)

**Decision Thresholds** (Scenario 1):
- >90%: Auto-apply
- 75-90%: Hold for review
- <75%: Escalate

**Examples**:
```
- "John Smith" vs "John Smith": 100%
- "John A Smith" vs "John Smith": 92%
- "J Smith" vs "John Smith": 75%
- "Smith John" vs "John Smith": 80%
```

**Used In**: Scenarios 1, 2, 3, 4

---

### 1.3 Customer Match Confidence
**Description**: Confidence score for matching payment sender to existing customer records.

**Computation Method**:
- Exact name match: 100%
- Fuzzy name match using Levenshtein distance or similar algorithm
- Can be boosted by supporting signals (see 1.4)

**Output**: Numeric score (0-100)

**Used In**: Scenarios 2, 4

---

### 1.4 Supporting Signals (for Scenario 2)
**Description**: Additional signals used when customer name match is not exact but customer is likely known.

**Signals** (Boolean, each):
- **Account Number Match**: Sender account matches historical account on file
- **Amount Match**: Payment amount matches expected premium for a policy
- **Historical Pattern Match**: Amount and timing match historical payment pattern

**Rule**: If name match < 90%, requires ≥2 supporting signals to proceed with Scenario 2. Otherwise escalates to Scenario 4.

**Used In**: Scenario 2

---

## 2. Amount & Variance Signals

### 2.1 Amount Variance Percentage
**Description**: Percentage difference between payment and expected premium.

**Computation Method**:
```
variance_pct = abs(payment_amount - expected_premium) / expected_premium * 100
```

**Decision Thresholds** (Scenario 3):
- <2%: Auto-approve (same as Scenario 1)
- 2-15%: Hold for manual review
- >15%: Escalate to investigation

**Output**: Numeric percentage + classification

**Used In**: Scenarios 1, 2, 3

---

### 2.2 Overpayment/Underpayment Indicator
**Description**: Flag indicating if payment is above or below expected premium.

**Computation Method**:
```
is_overpayment = payment_amount > (expected_premium * 1.02)
is_underpayment = payment_amount < (expected_premium * 0.98)
difference_amount = payment_amount - expected_premium
```

**Output**: Classification (OVER / UNDER / WITHIN_TOLERANCE) + difference amount

**Used In**: Scenario 3

---

### 2.3 Multi-Period Payment Indicator
**Description**: Detects if payment might represent multiple premium periods.

**Computation Method**:
```
period_multiplier = round(payment_amount / expected_premium)
is_multi_period = (abs(payment_amount - (expected_premium * period_multiplier)) < expected_premium * 0.05) AND period_multiplier > 1
```

**Output**: Boolean + estimated periods

**Used In**: Scenario 3

---

### 2.4 Multi-Method Payment Indicator
**Description**: Detects if payment might be a split payment where the customer is paying one premium across multiple payment methods or banks.

**Computation Method**:
```
fraction = payment_amount / expected_premium
is_multi_method = (fraction ≈ 1/N for N in [2,3,4]) within 5% tolerance
```

**Common Pattern**: $7,500 premium paid as $2,500 × 3 from different banks.

**Output**: Boolean + fraction of premium this payment covers

**Used In**: Scenario 3 (prevents unnecessary escalation of split payments)

---

### 2.5 Third-Party Payment Indicator
**Description**: Detects if the payment sender differs from the policyholder, indicating a third-party payment (family member, employer, mortgage escrow company, etc.).

**Detection Patterns**:
- Corporate names (Corp, LLC, Payroll, Inc.)
- Shared last name with policyholder (family member)
- Mortgage/escrow company names
- Historical third-party payers for this policy

**Output**: Boolean + relationship type (employer, family, escrow, trust, POA, unknown)

**Used In**: Scenarios 3, 4 (prevents unnecessary escalation of legitimate third-party payments)

---

### 2.6 Historical Amount Consistency
**Description**: How consistent the payment amount is with customer's historical payments.

**Computation Method**:
- Calculate mean and std deviation of last 6-12 payments
- Compare current payment to historical pattern
- Z-score calculation for statistical outlier detection

**Output**: Consistency score (0-100) + outlier flag

**Used In**: Scenarios 2, 3

---

## 3. Temporal & Pattern Signals

### 3.1 Payment Timing Match
**Description**: How well payment date aligns with expected due date.

**Computation Method**:
```
days_difference = abs(payment_date - expected_due_date)
if days_difference <= 7: EXCELLENT
elif days_difference <= 14: GOOD
elif days_difference <= 30: ACCEPTABLE
else: POOR
```

**Output**: Match quality + days difference

**Used In**: Scenarios 1, 2

---

### 3.2 Days Since Last Payment
**Description**: Number of days between current payment and last recorded payment.

**Computation Method**:
```
days_since_last = current_payment_date - last_payment_date
```

**Output**: Integer (days)

**Used In**: Scenarios 2, 5

---

## 4. Risk & Fraud Detection Signals

### 4.1 Risk Flags
**Description**: Boolean check for known risk indicators on the policy or customer.

**Checks**:
- Fraud history
- Suspended account
- Chronic late payments

**Output**: Boolean (present/not present) + list of specific flags

**Impact**: If any risk flag is present, Scenario 1 forces a HOLD regardless of match scores.

**Used In**: Scenario 1

---

### 4.2 Account Status Flag
**Description**: Status of the associated policy/customer account.

**Statuses**:
- ACTIVE: Normal processing
- INACTIVE: Escalate (unexpected payment)
- CLOSED: Escalate (policy terminated)
- PENDING: Hold for activation

**Output**: Status code + action recommendation

**Used In**: All scenarios

---

### 4.3 Payment Method Risk Level
**Description**: Risk classification derived from the payment method used.

**Classification**:
- **Low**: ACH, Credit Card (established electronic channels)
- **Medium**: Check, Wire Transfer (less traceable)
- **High**: Unknown or unrecognized payment method

**Output**: Enum (LOW / MEDIUM / HIGH)

**Impact**: In Scenario 1, auto-apply (Path 1) requires `Payment_Method_Risk_Level = Low`. High-risk methods force a HOLD regardless of other scores.

**Used In**: Scenario 1

---

### 4.4 Outstanding Balance Check
**Description**: Current balance owed on the policy.

**Computation Method**:
```
outstanding_balance = total_premium_due - total_payments_applied
```

**Output**: Balance amount + status (CURRENT / PAST_DUE)

**Used In**: Scenarios 1, 2, 5

---

## 5. Duplicate Detection Signals

### 5.1 Duplicate Match (3 Exact + $2 Amount Tolerance)
**Description**: Checks if payment matches a recent transaction within 72 hours on 3 exact fields plus amount within $2 tolerance.

**Computation Method**:
```
Search last 72 hours for payments matching ALL of:
  - Sender_Name (exact)
  - Policy_Reference (exact)
  - Payment_Method (exact)
  - Amount (within $2 tolerance — covers fees, rounding, surcharges)

IF 3 exact fields match AND |amount_diff| <= $2: Duplicate = TRUE (100%)
ELSE: Duplicate = FALSE (0%)
```

This is a binary check — either all criteria are met or it's not a duplicate. The $2 amount tolerance accounts for bank processing fees (e.g., $7,500 → $7,499), rounding differences, and small surcharges.

**Output**: Boolean (duplicate detected / not detected)

**Used In**: Scenario 5

---

### 5.2 Time Between Payments
**Description**: Time gap between current payment and the matching previous payment.

**Computation Method**:
```
hours_between = current_payment_timestamp - previous_payment_timestamp
```

**Output**: Hours between payments

**Used In**: Scenario 5

---

### 5.3 Outstanding Balance Justification
**Description**: Determines if a duplicate payment could be legitimate based on outstanding balance.

**Logic**:
- If outstanding balance > 0: May be a legitimate catch-up payment → HOLD
- If outstanding balance = 0 and next payment not due: Likely true duplicate → ESCALATE

**Output**: Boolean (justifies_duplicate) + balance details

**Used In**: Scenario 5

---

### 5.4 Duplicate Amount Difference
**Description**: The absolute difference in cents between the current payment and the suspected duplicate payment.

**Computation Method**:
```
duplicate_amount_difference = abs(current_payment_amount - duplicate_payment_amount)
```

**Output**: Integer (cents). 0 = exact match, up to 200 cents ($2) within tolerance.

**Purpose**: Captured for reporting/audit. If amounts differ slightly, reasoning includes: "Amount difference of $X.XX likely due to fees/rounding."

**Used In**: Scenario 5

---

## Signal Dependency Map

```
Level 1 (Independent - compute first):
├─ Name Similarity Score
├─ Amount Variance Percentage
├─ Payment Timing Match
└─ Duplicate Match (3 exact + $2 tolerance)

Level 2 (Depends on Level 1):
├─ Customer Match Confidence (uses Name Similarity)
├─ Policy Match Confidence (uses reference fields)
├─ Overpayment/Underpayment Indicator (uses Amount Variance)
├─ Historical Amount Consistency
└─ Duplicate Amount Difference (if duplicate detected in Level 1)

Level 3 (Depends on Level 2):
├─ Risk Flags + Account Status
├─ Payment Method Risk Level (derived from payment method)
├─ Outstanding Balance Check
├─ Supporting Signals (Scenario 2)
├─ Multi-Period Indicator (needs confirmed premium amount)
├─ Multi-Method Payment Indicator (needs confirmed premium amount)
├─ Third-Party Payment Indicator (needs confirmed customer ID)
└─ Time Between Payments (if duplicate detected in Level 1)

Level 4 (Final Decision):
└─ Recommendation Engine (uses all signals → routes to correct scenario)
```
