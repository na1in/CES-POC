# Database Design - AI Agent Payment Resolution

## Context

The AI Agent Payment Resolution system processes incoming payments and routes them through 5 scenarios to determine whether to **APPLY**, **HOLD**, or **ESCALATE**. The database needs to store payment inputs, customer/policy reference data, computed signals, recommendations, and audit trails.

This is a **design document only**, database-agnostic. All message and enum definitions live in Protocol Buffer files under `proto/`.

---

## Proto Files

| File | Messages | Description |
|------|----------|-------------|
| `proto/customer.proto` | `Customer`, `RiskFlag` | Customer accounts and risk flags |
| `proto/policy.proto` | `Policy`, `PaymentHistory` | Insurance policies and historical payment records |
| `proto/payment.proto` | `Payment` | Incoming payments to be resolved |
| `proto/signals.proto` | `PaymentSignals`, `MatchingSignals`, `AmountSignals`, `TemporalSignals`, `RiskSignals`, `DuplicateSignals`, `PaymentMethodRiskLevel` | All computed feature signals (1-to-1 with Payment) |
| `proto/recommendation.proto` | `PaymentRecommendation` | Final AI agent decision output (1-to-1 with Payment) |
| `proto/audit.proto` | `AuditLogEntry`, `ConfigurationThreshold` | Audit trail and tunable thresholds |

---

## Relationships

```
Customer (1) ──→ (many) Policy
Customer (1) ──→ (many) RiskFlag
Policy   (1) ──→ (many) PaymentHistory

Payment  (1) ──→ (1) PaymentSignals
Payment  (1) ──→ (1) PaymentRecommendation
Payment  (many) → (1) Customer  (optional — may not be matched)
Payment  (many) → (1) Policy    (optional — may not be matched)

Payment  (1) ──→ (many) AuditLogEntry
```

---

## Key Indexes

When backed by a datastore that supports indexing:

- `Payment(payment_date)` — 72-hour duplicate window searches
- `Payment(sender_name)` — Name similarity lookups
- `Payment(amount)` — Amount correlation searches
- `PaymentHistory(policy_id, payment_date)` — Historical pattern queries
- `Policy(policy_number, status)` — Policy lookups
- `RiskFlag(customer_id, is_active)` — Active risk flag checks

---

## Data Flow

1. Payment ingested → `Payment` (status: RECEIVED)
2. Signals computed → `PaymentSignals` + `AuditLogEntry`
3. Scenario routing + decision → `PaymentRecommendation` + `AuditLogEntry`
4. Human review (if needed) → `AuditLogEntry` (APPROVED action)
5. Final application → `Payment` (status: APPLIED) + `PaymentHistory` + `AuditLogEntry`

---

## Design Notes

- **Monetary amounts** are stored as `int64` in cents (smallest currency unit) to avoid floating-point precision issues.
- **Scores** (0-100) use `double` since exact precision is not required for ML confidence values.
- **JSON fields** from the original design map to `google.protobuf.Struct` (audit details) or `repeated string` (reasoning points).
- **Nullable fields** are represented by proto3 default values (empty string = not set). Where the distinction between "unset" and "default" matters, use wrapper types or optional fields.
- **PaymentSignals** uses nested sub-messages (`MatchingSignals`, `AmountSignals`, etc.) rather than a flat structure to group related signals cleanly.
- **AmountSignals** includes `is_multi_method` (bool), `multi_method_fraction` (double), `is_third_party_payment` (bool), and `third_party_relationship` (string) for detecting split and third-party payments.
- **RiskSignals** includes `payment_method_risk_level` (enum: LOW, MEDIUM, HIGH) derived from payment method.
- **DuplicateSignals** includes `duplicate_amount_difference` (int64, cents) to capture amount differences within the $2 tolerance.
