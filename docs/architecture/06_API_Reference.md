# API Reference

**Base URL:** `/api`

---

## Endpoints

### Payments

| Method | Endpoint | Description |
|--------|---------|-------------|
| POST | `/api/payments/ingest` | Ingest a new payment and run full pipeline |
| GET | `/api/payments` | List payments with filters |
| GET | `/api/payments/{id}` | Get payment detail with signals, recommendation, audit |
| POST | `/api/payments/{id}/approve` | Approve a held payment (analyst action) |
| POST | `/api/payments/{id}/reject` | Reject a held payment → escalate (analyst action) |
| POST | `/api/payments/{id}/reprocess` | Re-run pipeline for a PROCESSING_FAILED payment |

### Dashboard

| Method | Endpoint | Description |
|--------|---------|-------------|
| GET | `/api/dashboard/stats` | Counts by status, by scenario, failed count |
| GET | `/api/queue` | Pending approval queue (HELD items, sorted by urgency) |

### Configuration

| Method | Endpoint | Description |
|--------|---------|-------------|
| GET | `/api/thresholds` | List all configuration thresholds |
| PUT | `/api/thresholds/{name}` | Update a threshold value |

### System

| Method | Endpoint | Description |
|--------|---------|-------------|
| GET | `/api/health` | Health check |

---

## Detailed Endpoint Specs

### POST `/api/payments/ingest`

Ingest a new payment. Runs the full pipeline (validate → signals → route → reason → persist).

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
| payment_method | string | Yes | ACH, CHECK, WIRE, EFT |
| payment_date | ISO 8601 | Yes | |
| reference_1 | string | No | Free text |
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
    "suggested_action": "Apply to POL-12345"
  }
}
```

**Error (400):** Validation failure
```json
{
  "detail": "amount must be a positive integer"
}
```

---

### GET `/api/payments`

List payments with optional filters.

**Query Parameters:**

| Param | Type | Description |
|-------|------|-------------|
| status | string | Filter by status: RECEIVED, APPLIED, HELD, ESCALATED, PROCESSING_FAILED |
| scenario | integer | Filter by scenario: 1-5 |
| from_date | ISO 8601 | Filter payments after this date |
| to_date | ISO 8601 | Filter payments before this date |
| search | string | Search by sender name |
| page | integer | Page number (default: 1) |
| page_size | integer | Items per page (default: 20) |

**Response (200):**
```json
{
  "payments": [
    {
      "payment_id": "PMT-001",
      "sender_name": "John A Smith",
      "amount_cents": 500000,
      "status": "APPLIED",
      "scenario_route": 1,
      "confidence_score": 95,
      "payment_date": "2026-03-12T09:00:00Z",
      "ingested_at": "2026-03-12T09:01:23Z"
    }
  ],
  "total": 68,
  "page": 1,
  "page_size": 20
}
```

---

### GET `/api/payments/{id}`

Full payment detail including signals, recommendation, and audit trail.

**Response (200):**
```json
{
  "payment": {
    "payment_id": "PMT-002",
    "amount_cents": 125000,
    "sender_name": "Sarah Johnson",
    "status": "HELD",
    "matched_customer_id": "CUST-0042",
    "matched_policy_id": "POL-20145"
  },
  "signals": {
    "matching": {
      "name_similarity_score": 100,
      "policy_match_confidence": 0,
      "customer_match_confidence": 100,
      "account_match": false,
      "amount_match": true,
      "historical_match": true
    },
    "amount": {
      "amount_variance_pct": 0,
      "is_overpayment": false,
      "is_underpayment": false,
      "is_multi_period": false,
      "is_multi_method": false,
      "multi_method_fraction": 0,
      "is_third_party_payment": false,
      "third_party_relationship": ""
    },
    "temporal": {
      "payment_timing_quality": "EXCELLENT",
      "days_from_due_date": -3
    },
    "risk": {
      "has_risk_flags": false,
      "account_status": "ACTIVE",
      "payment_method_risk_level": "LOW"
    },
    "duplicate": {
      "is_duplicate_match": false,
      "duplicate_amount_difference": 0
    }
  },
  "recommendation": {
    "recommendation": "APPLY",
    "confidence_score": 85,
    "scenario_route": 2,
    "decision_path": "scenario_2_amount_disambiguates",
    "requires_human_approval": true,
    "reasoning": ["..."]
  },
  "audit_trail": [
    {
      "action_type": "RECEIVED",
      "actor": "system",
      "timestamp": "2026-03-12T09:01:23Z"
    },
    {
      "action_type": "SIGNALS_COMPUTED",
      "actor": "system",
      "timestamp": "2026-03-12T09:01:24Z"
    },
    {
      "action_type": "RECOMMENDATION_MADE",
      "actor": "system",
      "timestamp": "2026-03-12T09:01:25Z"
    }
  ]
}
```

---

### POST `/api/payments/{id}/approve`

Approve a HELD payment. Updates status to APPLIED, updates ledger.

**Request Body:**
```json
{
  "analyst_id": "analyst-jane-doe",
  "notes": "Confirmed with customer records"
}
```

**Response (200):**
```json
{
  "payment_id": "PMT-002",
  "status": "APPLIED",
  "approved_by": "analyst-jane-doe",
  "approved_at": "2026-03-12T10:15:00Z"
}
```

**Error (409):** Payment not in HELD status

---

### POST `/api/payments/{id}/reject`

Reject a HELD payment. Updates status to ESCALATED.

**Request Body:**
```json
{
  "analyst_id": "analyst-jane-doe",
  "notes": "Customer name does not match — needs investigation"
}
```

**Response (200):**
```json
{
  "payment_id": "PMT-002",
  "status": "ESCALATED",
  "rejected_by": "analyst-jane-doe",
  "rejected_at": "2026-03-12T10:15:00Z"
}
```

---

### POST `/api/payments/{id}/reprocess`

Re-run the processing pipeline for a PROCESSING_FAILED payment.

**Response (200):** Same as ingest response (includes new recommendation).

**Error (409):** Payment not in PROCESSING_FAILED status.

---

### GET `/api/dashboard/stats`

**Response (200):**
```json
{
  "by_status": {
    "RECEIVED": 2,
    "APPLIED": 45,
    "HELD": 8,
    "ESCALATED": 3,
    "PROCESSING_FAILED": 1
  },
  "by_scenario": {
    "1": 32,
    "2": 16,
    "3": 12,
    "4": 5,
    "5": 3
  },
  "today_count": 12,
  "pending_approval": 8
}
```

---

### GET `/api/queue`

Pending approval queue — HELD payments sorted by urgency.

**Response (200):**
```json
{
  "queue": [
    {
      "payment_id": "PMT-004",
      "sender_name": "Emily Watson",
      "amount_cents": 75000,
      "scenario_route": 5,
      "confidence_score": 60,
      "held_since": "2026-03-11T14:30:00Z",
      "hours_in_queue": 19.5
    }
  ],
  "total": 8
}
```

---

### GET `/api/thresholds`

**Response (200):**
```json
{
  "thresholds": [
    {
      "parameter_name": "name_match_auto_apply",
      "parameter_value": "90",
      "description": "Name similarity % for auto-apply in Scenario 1",
      "effective_date": "2026-03-01T00:00:00Z"
    }
  ]
}
```

---

### PUT `/api/thresholds/{name}`

**Request Body:**
```json
{
  "parameter_value": "85",
  "description": "Lowered from 90% for testing"
}
```

**Response (200):** Updated threshold object.

---

*End of Document*
