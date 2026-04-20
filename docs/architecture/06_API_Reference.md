# API Reference

**Base URL:** `/api`

---

## Endpoint Index

### Payments

| Method | Endpoint | Description |
|--------|---------|-------------|
| POST | `/api/payments/ingest` | Submit new payment and run full pipeline |
| GET | `/api/payments` | List with filters + pagination |
| GET | `/api/payments/{id}` | Full detail (payment + signals + recommendation + audit + annotations + documents) |
| POST | `/api/payments/{id}/approve` | Analyst approves HELD → APPLIED + ledger update |
| POST | `/api/payments/{id}/reject` | Analyst rejects HELD → ESCALATED |
| POST | `/api/payments/{id}/override` | Override AI recommendation (mandatory reason) |
| POST | `/api/payments/{id}/return` | Damien marks payment returned to sender |
| POST | `/api/payments/{id}/reprocess` | Re-run pipeline for PROCESSING_FAILED |

### Annotations

| Method | Endpoint | Description |
|--------|---------|-------------|
| POST | `/api/payments/{id}/annotations` | Add case note, override reason, or investigation note |
| GET | `/api/payments/{id}/annotations` | List all annotations for a case |

### Documents

| Method | Endpoint | Description |
|--------|---------|-------------|
| POST | `/api/payments/{id}/documents` | Upload supporting document (multipart) |
| GET | `/api/payments/{id}/documents` | List document metadata for a case |
| GET | `/api/payments/{id}/documents/{doc_id}` | Download/stream document |
| DELETE | `/api/payments/{id}/documents/{doc_id}` | Soft delete (audit-safe) |

### Settings / Configuration

| Method | Endpoint | Description |
|--------|---------|-------------|
| GET | `/api/settings/thresholds` | Read current active thresholds |
| POST | `/api/settings/change-requests` | Marcus submits a threshold change proposal |
| GET | `/api/settings/change-requests` | List change requests (filterable by status) |
| POST | `/api/settings/change-requests/{id}/approve` | Lorraine approves |
| POST | `/api/settings/change-requests/{id}/reject` | Lorraine rejects (mandatory comment) |
| POST | `/api/settings/change-requests/{id}/deploy` | Marcus deploys approved change |
| POST | `/api/settings/change-requests/{id}/rollback` | Emergency rollback (requires Lorraine approval) |
| GET | `/api/settings/thresholds/history` | Full version history for all parameters |

### Analytics

| Method | Endpoint | Description |
|--------|---------|-------------|
| GET | `/api/analytics/decisions` | Decision attribution breakdown (AI vs human, by payment method, by scenario) |
| GET | `/api/analytics/overrides` | Override analysis (filterable by scenario, confidence band, date, reason) |

### Governance

| Method | Endpoint | Description |
|--------|---------|-------------|
| POST | `/api/governance/reviews` | Lorraine records a period review |
| GET | `/api/governance/reviews` | List governance reviews |
| POST | `/api/governance/anomalies` | Lorraine flags a metric anomaly for Marcus |
| GET | `/api/governance/anomalies` | List anomaly flags (filterable by status) |
| PATCH | `/api/governance/anomalies/{id}` | Marcus updates investigation status + resolution notes |
| GET | `/api/governance/export` | Export audit-ready report (date range + scope) |

### System

| Method | Endpoint | Description |
|--------|---------|-------------|
| GET | `/api/health` | Health check |

---

## Detailed Endpoint Specs

### POST `/api/payments/ingest`

Ingest a new payment. Saves as RECEIVED then runs the full pipeline asynchronously (validate → signals → route → reason → persist).

**Request Body:**
```json
{
  "amount": 500000,
  "sender_name": "John A Smith",
  "sender_account": "ACC-9876",
  "beneficiary_name": "John Smith",
  "payment_method": "ACH",
  "payment_date": "2026-03-12T09:00:00Z",
  "reference_1": "For policy POL-12345 Jan premium",
  "reference_2": "Auto insurance payment"
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| amount | integer | Yes | In cents (500000 = $5,000) |
| sender_name | string | Yes | |
| sender_account | string | No | |
| beneficiary_name | string | No | |
| payment_method | string | Yes | ACH, CHECK, WIRE, CREDIT_CARD |
| payment_date | ISO 8601 | Yes | |
| reference_1 | string | No | Free text — parsed by Claude at ingest |
| reference_2 | string | No | Free text |

**Response (201):**
```json
{
  "payment_id": "PMT-001",
  "status": "APPLIED",
  "recommendation": {
    "recommendation": "APPLY",
    "confidence_score": 95,
    "scenario_route": 1,
    "decision_path": "scenario_1_auto_apply",
    "requires_human_approval": false,
    "reasoning": [
      "Policy POL-12345 confirmed active...",
      "Name similarity 92% exceeds threshold..."
    ],
    "suggested_action": "Apply to POL-12345",
    "decision_attribution": "AI_AUTONOMOUS"
  }
}
```

**Error (400):** Validation failure — `{ "detail": "amount must be a positive integer" }`

---

### GET `/api/payments`

List payments with optional filters and pagination.

**Query Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| status | string | RECEIVED, PROCESSING, APPLIED, HELD, ESCALATED, PROCESSING_FAILED, PENDING_SENDER_RESPONSE, RETURNED |
| scenario | integer | 1-5 |
| from_date | ISO 8601 | |
| to_date | ISO 8601 | |
| search | string | Sender name |
| sort_by | string | confidence_score, has_risk_flags, payment_method, payment_date |
| page | integer | Default: 1 |
| page_size | integer | Default: 20 |

**Response (200):**
```json
{
  "payments": [
    {
      "payment_id": "PMT-001",
      "sender_name": "John A Smith",
      "amount_cents": 500000,
      "payment_method": "ACH",
      "status": "APPLIED",
      "scenario_route": 1,
      "confidence_score": 95,
      "has_risk_flags": false,
      "payment_date": "2026-03-12T09:00:00Z",
      "created_timestamp": "2026-03-12T09:01:23Z"
    }
  ],
  "total": 68,
  "page": 1,
  "page_size": 20
}
```

---

### GET `/api/payments/{id}`

Full payment detail — used by the Payment Detail page.

**Response (200):**
```json
{
  "payment": {
    "payment_id": "PMT-002",
    "amount_cents": 125000,
    "sender_name": "Sarah Johnson",
    "payment_method": "ACH",
    "status": "HELD",
    "matched_customer_id": "CUST-0042",
    "matched_policy_id": "POL-20145",
    "investigation_due_date": null,
    "sla_breached": false
  },
  "signals": {
    "matching": {
      "name_similarity_score": 100,
      "policy_match_confidence": 0,
      "customer_match_confidence": 100,
      "account_match": false,
      "amount_match": true,
      "historical_match": true,
      "jaro_winkler_score": 100,
      "levenshtein_score": 100,
      "soundex_match": true,
      "deterministic_score": 100,
      "used_llm": false,
      "llm_score": 0
    },
    "amount": {
      "amount_variance_pct": 0,
      "is_overpayment": false,
      "is_underpayment": false,
      "difference_amount": 0,
      "is_multi_period": false,
      "estimated_periods": 0,
      "historical_consistency_score": 95,
      "is_multi_method": false,
      "multi_method_fraction": 0,
      "is_third_party_payment": false,
      "third_party_relationship": ""
    },
    "temporal": {
      "payment_timing_quality": "EXCELLENT",
      "days_from_due_date": -3,
      "days_since_last_payment": 30
    },
    "risk": {
      "has_risk_flags": false,
      "risk_flag_types": [],
      "account_status": "ACTIVE",
      "payment_method_risk_level": "LOW",
      "outstanding_balance_cents": 125000,
      "outstanding_balance_status": "current"
    },
    "duplicate": {
      "is_duplicate_match": false,
      "duplicate_payment_id": "",
      "hours_since_duplicate": 0,
      "outstanding_balance_justifies": false,
      "duplicate_amount_difference": 0
    }
  },
  "recommendation": {
    "recommendation": "APPLY",
    "confidence_score": 85,
    "scenario_route": 2,
    "decision_path": "scenario_2_amount_disambiguates",
    "requires_human_approval": true,
    "approval_reason": "Scenario 2 always requires human confirmation",
    "reasoning": ["Customer matched with 100% confidence", "Amount matches Auto policy exactly"],
    "suggested_action": "Apply to POL-20145",
    "decision_attribution": "UNSPECIFIED"
  },
  "audit_trail": [
    { "action_type": "RECEIVED", "actor": "system", "timestamp": "2026-03-12T09:01:23Z", "details": {} },
    { "action_type": "SIGNALS_COMPUTED", "actor": "system", "timestamp": "2026-03-12T09:01:24Z", "details": {} },
    { "action_type": "RECOMMENDATION_MADE", "actor": "system", "timestamp": "2026-03-12T09:01:25Z", "details": { "recommendation": "APPLY", "confidence": 85 } }
  ],
  "annotations": [],
  "documents": []
}
```

---

### POST `/api/payments/{id}/approve`

Priya approves a HELD payment → APPLIED. Triggers ledger update. Sets `decision_attribution = HUMAN_CONFIRMED`.

**Request Body:**
```json
{ "notes": "Confirmed with customer records" }
```

**Response (200):**
```json
{ "payment_id": "PMT-002", "status": "APPLIED", "decision_attribution": "HUMAN_CONFIRMED" }
```

**Error (409):** Payment not in HELD status.

---

### POST `/api/payments/{id}/reject`

Priya rejects a HELD payment → ESCALATED. Sets `investigation_due_date` (SLA deadline for Damien).

**Request Body:**
```json
{ "notes": "Customer name does not match — needs investigation" }
```

**Response (200):**
```json
{
  "payment_id": "PMT-002",
  "status": "ESCALATED",
  "investigation_due_date": "2026-03-14T10:15:00Z"
}
```

---

### POST `/api/payments/{id}/override`

Priya or Damien overrides the AI recommendation. Reason is mandatory. Sets `decision_attribution = HUMAN_OVERRIDE`.

**Request Body:**
```json
{
  "override_action": "APPLY",
  "reason": "Confirmed third-party employer payment via phone"
}
```

**Response (200):**
```json
{ "payment_id": "PMT-009", "status": "APPLIED", "decision_attribution": "HUMAN_OVERRIDE" }
```

---

### POST `/api/payments/{id}/return`

Damien marks a payment as returned to sender after investigation.

**Request Body:**
```json
{ "notes": "Sender confirmed duplicate — wire reversed 2026-03-15" }
```

**Response (200):**
```json
{ "payment_id": "PMT-011", "status": "RETURNED" }
```

---

### POST `/api/payments/{id}/reprocess`

Re-run the full pipeline for a PROCESSING_FAILED payment. Signals recomputed fresh from current DB state.

**Response (200):** Same shape as ingest response.

**Error (409):** Payment not in PROCESSING_FAILED status.

---

### POST `/api/payments/{id}/annotations`

**Request Body:**
```json
{
  "annotation_type": "CASE_NOTE",
  "content": "Spoke with Sarah — she confirmed the payment",
  "contact_method": "",
  "contact_outcome": "",
  "contacted_party": ""
}
```

`annotation_type`: `CASE_NOTE`, `OVERRIDE_REASON`, `CONTACT_RECORD`, `INVESTIGATION_NOTE`

For `CONTACT_RECORD`, populate `contact_method` (phone/email/letter), `contact_outcome` (reached/no_answer/voicemail/bounced), `contacted_party`.

**Response (201):** Created annotation object.

---

### GET `/api/payments/{id}/annotations`

**Response (200):**
```json
{
  "annotations": [
    {
      "annotation_id": 1,
      "payment_id": "PMT-002",
      "author_user_id": "USR-0001",
      "annotation_type": "CASE_NOTE",
      "content": "Spoke with Sarah — she confirmed the payment",
      "created_at": "2026-03-12T10:10:00Z"
    }
  ]
}
```

---

### POST `/api/payments/{id}/documents`

Multipart upload. `document_type`: `SUPPORTING_EVIDENCE`, `SENDER_CORRESPONDENCE`, `BANK_STATEMENT`, `FRAUD_REPORT`, `POLICY_DOCUMENT`, `OTHER`.

**Response (201):** Created `CaseDocument` metadata object.

---

### GET `/api/payments/{id}/documents`

**Response (200):**
```json
{
  "documents": [
    {
      "document_id": 1,
      "payment_id": "PMT-002",
      "uploaded_by": "USR-0002",
      "file_name": "bank_confirmation.pdf",
      "file_type": "application/pdf",
      "file_size_bytes": 204800,
      "document_type": "BANK_STATEMENT",
      "description": "Wire confirmation from Chase",
      "uploaded_at": "2026-03-12T11:00:00Z",
      "is_deleted": false
    }
  ]
}
```

---

### GET `/api/payments/{id}/documents/{doc_id}`

Stream/download the document file.

---

### DELETE `/api/payments/{id}/documents/{doc_id}`

Soft delete only — `is_deleted` set to true. Document is never hard-deleted for audit compliance.

---

### GET `/api/settings/thresholds`

**Response (200):**
```json
{
  "thresholds": [
    {
      "parameter_name": "name_match_auto_apply",
      "parameter_value": "90",
      "description": "Name similarity % required for auto-apply in Scenario 1",
      "effective_date": "2026-03-01T00:00:00Z"
    }
  ]
}
```

---

### POST `/api/settings/change-requests`

Marcus submits a threshold change proposal.

**Request Body:**
```json
{
  "parameter_name": "name_match_auto_apply",
  "current_value": "90",
  "proposed_value": "88",
  "rationale": "Override rate analysis shows 90% is too conservative — 8% of valid payments are being held unnecessarily",
  "projected_impact": "Back-test shows 15% reduction in hold queue with <0.5% false positive increase"
}
```

**Response (201):** Created `ConfigurationChangeRequest` object with `status: PENDING`.

---

### POST `/api/settings/change-requests/{id}/approve`

Lorraine approves. Optionally includes a comment.

**Request Body:** `{ "review_comment": "Approved — review in 30 days" }`

**Response (200):** Updated change request with `status: APPROVED`.

---

### POST `/api/settings/change-requests/{id}/reject`

Lorraine rejects. Comment is mandatory.

**Request Body:** `{ "review_comment": "Need more data on false positive rate before approving" }`

**Response (200):** Updated change request with `status: REJECTED`.

---

### POST `/api/settings/change-requests/{id}/deploy`

Marcus deploys an APPROVED change to production. Creates a new `ConfigurationThresholdVersion` entry.

**Response (200):** Updated change request with `status: DEPLOYED` + new effective threshold.

---

### POST `/api/settings/change-requests/{id}/rollback`

Emergency rollback. Requires prior Lorraine approval (tracked via a linked review). Reverts to previous `ConfigurationThresholdVersion`.

**Response (200):** Updated change request with `status: ROLLED_BACK` + restored threshold.

---

### GET `/api/settings/thresholds/history`

Full append-only version history for all threshold parameters.

**Response (200):**
```json
{
  "history": [
    {
      "version_id": 1,
      "parameter_name": "name_match_auto_apply",
      "parameter_value": "88",
      "changed_by": "USR-0004",
      "approved_by": "USR-0003",
      "rationale": "Override rate analysis...",
      "change_request_id": 7,
      "effective_from": "2026-04-01T00:00:00Z",
      "effective_to": null
    }
  ]
}
```

---

### GET `/api/analytics/decisions`

Powers Lorraine's Governance Dashboard and Marcus's Admin Dashboard.

**Query Parameters:** `from_date`, `to_date`

**Response (200):** `AnalyticsDecisionsResponse` — see `proto/analytics.proto`. Includes:
- Summary counts (auto-applied, human review, held, escalated by AI, escalated by human, overrides, returned)
- Override rate %
- `by_payment_method` breakdown (ACH, Check, Wire, Credit Card with attribution counts)
- `by_scenario` breakdown (Scenarios 1-5 with attribution, avg confidence, override count, decision distribution)
- `confidence_histogram` (10 buckets: 0-10%, 10-20%, ..., 90-100%)

---

### GET `/api/analytics/overrides`

Override analysis for Marcus's Override Analysis page.

**Query Parameters:** `scenario` (1-5), `confidence_band` (e.g. `70-80`), `from_date`, `to_date`, `reason_category`

**Response (200):**
```json
{
  "overrides": [
    {
      "payment_id": "PMT-009",
      "original_recommendation": "ESCALATE",
      "override_action": "APPLY",
      "scenario_route": 4,
      "confidence_score": 61,
      "reason": "Confirmed third-party employer payment via phone",
      "overridden_by": "USR-0001",
      "overridden_at": "2026-03-12T14:30:00Z"
    }
  ],
  "total": 5
}
```

---

### POST `/api/governance/reviews`

Lorraine records a formal period review.

**Request Body:** `{ "period_start": "2026-03-01", "period_end": "2026-03-31", "notes": "..." }`

---

### POST `/api/governance/anomalies`

Lorraine flags a metric anomaly for Marcus to investigate.

**Request Body:**
```json
{
  "metric_name": "override_rate",
  "scenario_type": "scenario_3",
  "description": "Override rate for Scenario 3 jumped from 4% to 11% in last 7 days",
  "period_start": "2026-04-01",
  "period_end": "2026-04-07"
}
```

---

### PATCH `/api/governance/anomalies/{id}`

Marcus updates investigation status and adds resolution notes.

**Request Body:** `{ "status": "resolved", "resolution_notes": "Traced to a batch of Wire payments from new employer — not a threshold issue" }`

---

### GET `/api/governance/export`

**Query Parameters:** `from_date`, `to_date`, `scope` (decisions / overrides / config_changes / all)

Returns a structured audit-ready report as JSON or downloadable file.

---

*End of Document*
