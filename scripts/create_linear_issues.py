"""
Creates all CES implementation tickets in Linear.

Setup:
  1. Go to Linear → Settings → API → Personal API Keys → Create key
  2. Find your team ID: Settings → General → copy the team identifier
  3. Run:
       LINEAR_API_KEY=lin_api_xxx LINEAR_TEAM_ID=your-team-id python scripts/create_linear_issues.py

Optional env vars:
  LINEAR_PROJECT_NAME   default: "CES — Payment Resolution PoC"
"""

import asyncio
import os
import sys
import httpx

API_URL = "https://api.linear.app/graphql"
API_KEY = os.environ.get("LINEAR_API_KEY", "")
TEAM_ID = os.environ.get("LINEAR_TEAM_ID", "")
PROJECT_NAME = os.environ.get("LINEAR_PROJECT_NAME", "CES — Payment Resolution PoC")


ISSUES = [

    # ═══════════════════════════════════════════════════════════════════════
    # PHASE 0 — Foundation (remaining)
    # ═══════════════════════════════════════════════════════════════════════

    {
        "title": "[Design] Figma — Analyst & Investigator pages (4 pages)",
        "label": "Design", "phase": "Phase 0", "estimate": 3, "priority": 1,
        "assignee_hint": "Designer",
        "description": """\
## Context
Priya (Analyst) and Damien (Investigator) are the primary daily users. Priya reviews the AI queue and approves/rejects/overrides. Damien handles escalated cases, logs outreach, and makes final determinations on unresolved payments.

Reference doc: `docs/architecture/05_Human_Approval_Queue.md` — contains full page specs, column definitions, and all action button states.
Personas: `docs/Personas.pdf`

---

## Pages to design

### 1. Queue Dashboard `/`
- Table of open HELD payments sorted by AI confidence score (lowest first = needs most human attention)
- Columns: Scenario tag, Sender Name, Amount, **Payment Method**, AI Recommendation pill (APPLY/HOLD/ESCALATE), Confidence Band (Low/Medium/High), Age (time since ingest)
- Top filters: Scenario (1–5), Confidence Band, Payment Method
- Alert banner for any PROCESSING_FAILED payments with a Reprocess link
- Clicking a row navigates to Payment Detail

### 2. Investigation Queue `/investigations`
- Damien only — shows only ESCALATED and PENDING_SENDER_RESPONSE payments
- Sorted by risk level (has_risk_flags first, then time since escalation)
- Columns: Sender Name, Amount, Risk Indicator (red dot if risk flags present), Payment Method, Time Since Escalation, SLA status
- SLA breach warning: red badge when `sla_breached = true`

### 3. Payment Detail `/payments/[id]`
This is the most complex page. Sections (top to bottom):
1. **Payment header** — ID, sender, amount, method, date, current status badge
2. **Signal panel** — visual progress bars for: Name Similarity, Policy Match Confidence, Customer Match Confidence. Under Name Similarity, show algorithm breakdown: Jaro-Winkler score, Levenshtein score, Soundex match (yes/no), Deterministic score, LLM used (yes/no), LLM score. Each signal should have a tooltip explaining what it means.
3. **AI Reasoning panel** — scenario route tag, recommendation, confidence score, reasoning bullet list, suggested action text
4. **Audit timeline** — chronological list of all actions (RECEIVED → SIGNALS_COMPUTED → RECOMMENDATION_MADE → etc.) with actor name and timestamp
5. **Annotation panel** — tab or section showing existing annotations; Add Note form (textarea + submit). Role-gated: Priya sees case_note + override_reason; Damien sees contact_record + investigation_note
6. **Document panel** — list of uploaded files (name, type, size, uploader, date); Upload button (file picker, document type selector)
7. **Action buttons** (bottom, role-gated):
   - Priya: `Approve` (green), `Reject` (red), `Override` (yellow — opens modal requiring reason)
   - Damien: `Return to Sender` (red), `Log Contact` (blue — opens structured form)

### 4. Settings `/settings`
- Read-only threshold table for all roles: parameter name, current value, description, last changed date
- For Marcus (admin): each row has an "Propose Change" button that links to `/admin/config`

---

## Acceptance criteria
- [ ] All 4 pages delivered as Figma frames with desktop layout (1280px min)
- [ ] All interactive states designed: default, hover, loading, empty, error
- [ ] Payment Detail action buttons show correct set per role (use role switcher in Figma or notes)
- [ ] Signal panel algorithm breakdown is visible — not hidden behind a toggle
- [ ] SLA breach state shown in Investigation Queue (red badge variant)
- [ ] Designer has reviewed `05_Human_Approval_Queue.md` and resolved any ambiguities with PM before handoff
""",
    },

    {
        "title": "[Design] Figma — Director & Admin pages (6 pages)",
        "label": "Design", "phase": "Phase 0", "estimate": 3, "priority": 1,
        "assignee_hint": "Designer",
        "description": """\
## Context
Lorraine (Director) monitors governance, approves config changes, and reviews compliance reports. Marcus (Admin) manages configuration thresholds, investigates anomalies, and monitors system performance.

Reference doc: `docs/architecture/05_Human_Approval_Queue.md` — Director and Admin sections.

---

## Pages to design

### 1. Governance Dashboard `/governance` — Lorraine
- Date range filter (applies to all cards and charts)
- **6 metric cards**: Auto-Applied by AI, Applied after Human Review, Held Pending Review, Escalated by AI, Escalated by Human, Human Overrides
- **Charts**: Payment method breakdown (bar), Override rate trend over time (line), SLA adherence % (gauge or card), Confidence score histogram (10 buckets: 0–10 … 90–100)
- Navigation links to Export and Exceptions pages

### 2. Compliance Export `/governance/export`
- Date range picker (start/end)
- Export scope: checkboxes for Decisions, Override Log, Config Changes, Full Audit — plus "All" shortcut
- Download button — triggers file download (JSON or CSV)
- Last export timestamp shown

### 3. Exception Dashboard `/governance/exceptions`
Three sections:
1. SLA-breached cases: payment_id, sender, scenario, time since breach, assigned investigator
2. Anomaly flags: metric name, description, flagged date, current status (Open/Investigating/Resolved), resolution notes field
3. Config change requests pending Lorraine's action: parameter, current value, proposed value, rationale, Marcus's projected impact notes — Approve / Reject buttons

### 4. Admin Dashboard `/admin` — Marcus
- Per-scenario analytics (tabs or sections for Scenarios 1–5, plus "All")
- Per scenario: Case volume trend (line), Decision distribution (pie: AI auto / human confirmed / human override), Override rate by confidence band (grouped bar), Confidence histogram

### 5. Override Analysis `/admin/overrides`
- Filter bar: Scenario, Confidence Band (Low/Medium/High), Date Range, Override Reason Category
- Table: Payment ID, Scenario, AI Recommendation, Human Decision, Confidence Score, Reason Category, Override Date, Analyst Name

### 6. Configuration Management `/admin/config`
- Current thresholds table: parameter, value, description, last changed date, changed by
- "Propose Change" button → inline form or modal: parameter (dropdown), current value (auto-filled, read-only), proposed value (input), rationale (textarea), projected impact (textarea)
- Change request list with status chips: PENDING / APPROVED / REJECTED / DEPLOYED / ROLLED_BACK
- Version history drawer/panel per parameter
- Deploy and Rollback buttons (shown only when status = APPROVED / DEPLOYED respectively)

---

## Acceptance criteria
- [ ] All 6 pages delivered as Figma frames, desktop 1280px
- [ ] Governance Dashboard charts are labelled — no unlabelled axes
- [ ] Exception Dashboard anomaly status is colour-coded (Open=red, Investigating=amber, Resolved=green)
- [ ] Config Management change request status chips are colour-coded to match the status lifecycle
- [ ] Deploy button is visually disabled when status ≠ APPROVED
""",
    },

    # ═══════════════════════════════════════════════════════════════════════
    # PHASE 1 — Core Pipeline (Track A: Engineer A)
    # ═══════════════════════════════════════════════════════════════════════

    {
        "title": "[Backend] Ingest endpoint — POST /api/payments/ingest",
        "label": "Backend", "phase": "Phase 1", "estimate": 3, "priority": 2,
        "assignee_hint": "Engineer A",
        "description": """\
## Context
This is the system's entry point. Every payment starts here. The ingest step validates the raw payment data, uses Claude API to extract structured references from free-text fields, saves the payment with status `received`, and writes the first audit log entry.

Reference: `docs/architecture/01_Ingest_Layer.md`

---

## Request body
```json
{
  "amount": 150000,
  "sender_name": "Robert Johnson",
  "sender_account": "ACC-10001",
  "beneficiary_name": "Robert Johnson",
  "payment_method": "ACH",
  "payment_date": "2026-04-18T10:00:00Z",
  "reference_field_1": "for policy POL-00001 April payment",
  "reference_field_2": null
}
```
All fields except `beneficiary_name`, `reference_field_1`, `reference_field_2`, `sender_account` are required.
`amount` is in cents (integer). Never accept floats.

## Claude API call — free-text reference parsing
Call `claude-haiku-4-5` with a structured prompt to extract from `reference_field_1` and `reference_field_2`:
- `extracted_policy_number` — e.g. `"POL-00001"` or `null`
- `payment_intent` — enum: `"premium"`, `"arrears"`, `"partial"`, `"unknown"`
- `period_count` — integer number of periods if multi-period payment, else `1`

Store these in the `payments` row or a separate parsed_reference JSONB column (your call — flag in PR if you go with JSONB).

## Database write
INSERT into `payments`:
- `payment_id`: generate as `PMT-` + zero-padded sequence (e.g. `PMT-001`). Query `MAX(payment_id)` to get next value.
- `status`: `'received'`
- `created_timestamp`: `now()`
All other fields from request body.

## Audit log
INSERT into `audit_log`:
- `action_type`: `'received'`
- `actor`: `'system'`
- `actor_user_id`: `null`
- `payment_id`: the new payment_id
- `details`: `{"amount": 150000, "sender_name": "Robert Johnson", "payment_method": "ACH"}`

## Response (201 Created)
```json
{
  "payment_id": "PMT-001",
  "status": "received",
  "created_timestamp": "2026-04-18T15:00:00Z"
}
```

## Error cases
- 400: missing required field — `{"error": "missing_field", "field": "amount"}`
- 400: amount is not a positive integer — `{"error": "invalid_amount"}`
- 400: payment_method not in allowed list (ACH, Check, Credit Card, Wire) — `{"error": "invalid_payment_method"}`
- 422: Claude API parse fails — log warning, proceed with `extracted_policy_number=null`, do NOT fail the ingest
- 500: DB write fails — return error, do NOT write audit log for failed ingests

## File location
`backend/app/routers/payments.py` (create this file)
`backend/app/services/ingest.py` (create this file — keep Claude call isolated here)

## Acceptance criteria
- [ ] POST with valid body returns 201 with payment_id
- [ ] payment_id format is PMT-XXX (zero-padded, no gaps on retry)
- [ ] Claude parse failure does not fail the request — logs a warning instead
- [ ] Audit log entry written on every successful ingest
- [ ] float amounts are rejected (e.g. 150.00 → 400 error)
- [ ] No raw SQL — use SQLAlchemy ORM or `text()` with bound params only
""",
    },

    {
        "title": "[Backend] Signal Engine — Wave 1 (name matching, amount variance, timing, duplicate)",
        "label": "Backend", "phase": "Phase 1", "estimate": 4, "priority": 2,
        "assignee_hint": "Engineer A",
        "description": """\
## Context
Wave 1 computes the four signals that can run immediately after ingest with no inter-dependencies. These are the most computationally significant signals and include the only LLM call in the signal engine (Haiku for gray-zone name matching).

Reference: `docs/Step3_Feature_Signals.md`, `docs/architecture/02_Compute_Signals.md`

---

## Signal 1 — Hybrid Name Similarity

**File:** `backend/app/services/signals/matching.py`

Three-step process:

**Step 1 — Deterministic score** (always computed):
```python
import jellyfish
jw  = jellyfish.jaro_winkler_similarity(a, b) * 100   # 0–100
lev = (1 - jellyfish.levenshtein_distance(a, b) / max(len(a), len(b))) * 100
sdx = jellyfish.soundex(a) == jellyfish.soundex(b)
deterministic_score = (jw * 0.5 + lev * 0.3 + (10 if sdx else 0)) * (10/9)  # normalise to 100
```
Exact formula is illustrative — tune weights as needed, document your choice.

**Step 2 — Gray zone check** (read thresholds from `configuration_thresholds` table):
- `name_gray_zone_lower` (default 70): below this → clear mismatch, skip LLM
- `name_gray_zone_upper` (default 92): above this → clear match, skip LLM
- Between 70–92: call Claude Haiku

**Step 3 — Claude Haiku call** (only for gray zone):
Prompt asks: "Are these two names likely the same person? Name A: {a}. Name B: {b}. Consider nicknames, middle names, abbreviations. Return JSON: {score: 0-100, reasoning: string}"
`final_score = max(deterministic_score, llm_score)`

**Stored fields** (all go to `payment_signals`):
`jaro_winkler_score`, `levenshtein_score`, `soundex_match`, `deterministic_score`, `used_llm`, `llm_score`, `name_similarity_score` (= final_score)

---

## Signal 2 — Amount Variance

**File:** `backend/app/services/signals/amount.py`

Requires: matched policy's `premium_amount` from `policies` table.
If no policy matched yet: set `amount_variance_pct = null`, skip.

```python
variance_pct = abs(payment.amount - policy.premium_amount) / policy.premium_amount * 100
is_overpayment = payment.amount > policy.premium_amount
is_underpayment = payment.amount < policy.premium_amount
difference_amount = payment.amount - policy.premium_amount  # signed cents
```

---

## Signal 3 — Payment Timing Quality

**File:** `backend/app/services/signals/temporal.py`

Requires: `policies.next_due_date`. If null, set quality = UNSPECIFIED.

```
days_from_due = (payment_date.date() - next_due_date).days  # positive = late

EXCELLENT  → days_from_due in [-7, 0]    (early or on time)
GOOD       → days_from_due in [1, 5]
ACCEPTABLE → days_from_due in [6, 14]
POOR       → days_from_due > 14 or < -30
```

Also compute `days_since_last_payment`: query MAX(payment_date) from `payment_history` for this policy.

---

## Signal 4 — Duplicate Detection

**File:** `backend/app/services/signals/duplicate.py`

Read `duplicate_window_hours` (default 72) and `duplicate_amount_tolerance_cents` (default 200) from `configuration_thresholds`.

Query:
```sql
SELECT payment_id, amount FROM payments
WHERE sender_name = :name
  AND sender_account = :account
  AND payment_method = :method
  AND payment_date >= now() - interval ':hours hours'
  AND payment_id != :current_id
  AND status NOT IN ('returned', 'processing_failed')
```

If match found AND `abs(match.amount - current.amount) <= 200`:
- `is_duplicate_match = true`
- `duplicate_payment_id = match.payment_id`
- `hours_since_duplicate = (current.payment_date - match.payment_date).total_seconds() / 3600`
- `duplicate_amount_difference = abs(current.amount - match.amount)`

---

## Acceptance criteria
- [ ] All 4 signals computed and stored in `payment_signals` (partial — only Wave 1 fields)
- [ ] Haiku called only when deterministic score is 70–92; logged with `used_llm=true`
- [ ] Haiku timeout (>3s) is caught — fall back to deterministic score, log warning, continue
- [ ] Duplicate detection uses bound parameters — no string interpolation in SQL
- [ ] All threshold values read from DB, never hardcoded
- [ ] Unit tests for: name matching (exact match, clear mismatch, gray zone), duplicate detection (exact dup, $2 tolerance, outside window)
""",
    },

    {
        "title": "[Backend] Signal Engine — Wave 2 (policy/customer confidence, historical consistency)",
        "label": "Backend", "phase": "Phase 1", "estimate": 3, "priority": 2,
        "assignee_hint": "Engineer A",
        "description": """\
## Context
Wave 2 runs after Wave 1 and uses the Wave 1 name similarity score as an input. It computes match confidence scores and historical payment consistency.

Reference: `docs/Step3_Feature_Signals.md` — Category 1 (matching) and Category 2 (amount) signals.

**Depends on:** Wave 1 complete and stored in `payment_signals`.

---

## Signal 5 — Policy Match Confidence

**File:** `backend/app/services/signals/matching.py` (extend)

Weighted combination:
```
policy_match_confidence =
  (name_similarity_score * 0.4)
  + (100 if extracted_policy_number matches policy.policy_number else 0) * 0.4
  + (amount_match_signal * 0.2)   # from Wave 1 amount variance
```
Returns 0–100. If no policy candidate found: 0.

---

## Signal 6 — Customer Match Confidence

Similar weighted approach using:
- `name_similarity_score` (from Wave 1)
- `account_match`: does `payment.sender_account` appear in `payment_history.sender_account` for this customer?
- `historical_match`: does the payment pattern (amount, method, timing) match history?

Returns 0–100.

---

## Signal 7 — Historical Consistency Score

**File:** `backend/app/services/signals/amount.py` (extend)

Fetch last 6 `payment_history` records for the matched policy (ordered by payment_date desc).
Compute z-score of current payment amount against historical amounts:
```python
import statistics
amounts = [h.amount for h in history]
if len(amounts) < 2:
    return 100.0   # not enough history — assume consistent
mean = statistics.mean(amounts)
stdev = statistics.stdev(amounts)
z = abs(payment.amount - mean) / stdev if stdev > 0 else 0
historical_consistency_score = max(0, 100 - (z * 20))  # z=0→100, z=5→0
```

---

## Acceptance criteria
- [ ] All three confidence scores stored in `payment_signals`
- [ ] Policy match confidence is 0 if no policy reference and no name match ≥75%
- [ ] Historical consistency is 100 (not null) when fewer than 2 historical payments exist
- [ ] Unit test: z-score edge case (all identical historical amounts → stdev=0 should not divide by zero)
""",
    },

    {
        "title": "[Backend] Signal Engine — Wave 3 (risk, balance, multi-period, third-party indicators)",
        "label": "Backend", "phase": "Phase 1", "estimate": 3, "priority": 2,
        "assignee_hint": "Engineer A",
        "description": """\
## Context
Wave 3 computes the remaining signals that depend on Wave 2 output (mainly the matched customer/policy IDs). These signals inform the scenario routing and the AI reasoning prompt.

Reference: `docs/Step3_Feature_Signals.md` — Categories 3, 4, 5.

**Depends on:** Wave 2 complete.

---

## Signal 8 — Risk Flags

**File:** `backend/app/services/signals/risk.py`

Query `risk_flags` where `customer_id = matched_customer_id AND is_active = true`.
```python
has_risk_flags = len(flags) > 0
risk_flag_types = [f.flag_type for f in flags]   # List[str]: 'fraud_history', etc.
```

---

## Signal 9 — Account Status

Query `customers.status` for the matched customer.
Map: `'active'→ACTIVE`, `'inactive'→INACTIVE`, `'closed'→CLOSED`, `null→UNSPECIFIED`

---

## Signal 10 — Outstanding Balance Snapshot

Query `policies.outstanding_balance` and `policies.next_due_date`:
```python
outstanding_balance_cents = policy.outstanding_balance
outstanding_balance_status = 'past_due' if policy.next_due_date < today else 'current'
```

---

## Signal 11 — Payment Method Risk Level

Pure lookup, no DB query:
```python
LOW    = {"ACH", "Credit Card"}
MEDIUM = {"Check", "Wire"}
# anything else → HIGH
```

---

## Signal 12 — Supporting Signals (3 booleans)
- `account_match`: `payment.sender_account` appears in `payment_history.sender_account` for this policy
- `amount_match`: `amount_variance_pct <= 2.0` (read from DB threshold `amount_tolerance_auto`)
- `historical_match`: `historical_consistency_score >= 70`

---

## Signal 13 — Multi-Period Indicator

Read `multi_period_tolerance` threshold (default 5%) from DB.
Check if `payment.amount` is approximately N × `policy.premium_amount` for N in 2..12:
```python
for n in range(2, 13):
    expected = policy.premium_amount * n
    if abs(payment.amount - expected) / expected * 100 <= multi_period_tolerance:
        return True, n
return False, 0
```

---

## Signal 14 — Multi-Method Indicator

Check if `payment.amount` is a simple fraction of `policy.premium_amount`:
```python
for denom in [2, 3, 4]:
    expected = policy.premium_amount / denom
    if abs(payment.amount - expected) / expected * 100 <= 5:
        return True, round(payment.amount / policy.premium_amount, 3)
return False, 0.0
```

---

## Signal 15 — Third-Party Indicator

Compare `payment.sender_name` vs `customer.name`:
- If name similarity < 50%: sender is clearly different → flag as potential third party
- Check `payment.reference_field_1` for keywords: "employer", "payroll", "escrow", "family", "on behalf"
- `is_third_party_payment = True` if name mismatch AND (keyword match OR `payment.beneficiary_name` != `payment.sender_name`)
- `third_party_relationship`: if keyword matched, use that keyword; else `"unknown"`

---

## Acceptance criteria
- [ ] All Wave 3 signals written to `payment_signals` in the same DB call as Wave 1/2 (one upsert)
- [ ] Risk flag types stored as Postgres array (`risk_flag_type[]`), not a JSON string
- [ ] Multi-period correctly identifies 2× and 3× premium amounts within tolerance
- [ ] Third-party indicator does not flag payments where sender_name ≈ customer.name (similarity ≥ 80%)
""",
    },

    {
        "title": "[Database] Signal snapshot — persist all 19 signals to payment_signals",
        "label": "Database", "phase": "Phase 1", "estimate": 1, "priority": 2,
        "assignee_hint": "Engineer A",
        "description": """\
## Context
After all three waves compute their signals, the signal engine orchestrator persists the full `PaymentSignals` object to the DB in a single upsert and writes the audit log.

**File:** `backend/app/services/signal_engine.py`

**Depends on:** Waves 1, 2, 3 all complete.

---

## DB write

Single `INSERT INTO payment_signals (...) VALUES (...) ON CONFLICT (payment_id) DO UPDATE SET ...`

All 35 columns from the schema. Key ones:
- `computed_at = now()`
- `risk_flag_types` must be cast as `ARRAY[:risk_flag_types]::risk_flag_type[]`

Then UPDATE `payments SET status = 'processing'` while signals are being computed (set to `'processing'` at start of signal engine, update to next status after persist).

Then INSERT into `audit_log`:
```json
{
  "action_type": "signals_computed",
  "actor": "system",
  "payment_id": "PMT-001",
  "details": {
    "name_similarity_score": 95.2,
    "is_duplicate_match": false,
    "has_risk_flags": false,
    "scenario_hint": "scenario_1"
  }
}
```

---

## Acceptance criteria
- [ ] Single DB transaction for upsert + audit log
- [ ] `computed_at` is always set
- [ ] If signal engine crashes mid-way, the payment stays in `processing` status and can be reprocessed
- [ ] Upsert is idempotent — running twice for the same payment_id overwrites cleanly
""",
    },

    # ═══════════════════════════════════════════════════════════════════════
    # PHASE 1 — Frontend Shell (Track B: Engineer B)
    # ═══════════════════════════════════════════════════════════════════════

    {
        "title": "[Frontend] TypeScript types + mock API responses",
        "label": "Frontend", "phase": "Phase 1", "estimate": 2, "priority": 2,
        "assignee_hint": "Engineer B",
        "description": """\
## Context
The frontend must never wait for the backend. All Phase 1 frontend pages are built against mock data whose shape exactly matches the real API contract. This ticket defines that contract in TypeScript and creates realistic mock fixtures.

**File locations:**
- `frontend/src/types/` — one file per domain (payment.ts, signals.ts, recommendation.ts, annotation.ts, document.ts, user.ts)
- `frontend/src/mocks/` — one fixture file per endpoint

---

## TypeScript types to define

### payment.ts
```typescript
export type PaymentStatus =
  | "received" | "processing" | "applied" | "held"
  | "escalated" | "processing_failed" | "pending_sender_response" | "returned"

export type PaymentMethod = "ACH" | "Check" | "Credit Card" | "Wire"

export interface Payment {
  payment_id: string           // "PMT-001"
  amount: number               // cents, integer
  sender_name: string
  sender_account: string | null
  beneficiary_name: string | null
  payment_method: PaymentMethod
  payment_date: string         // ISO 8601
  reference_field_1: string | null
  reference_field_2: string | null
  status: PaymentStatus
  matched_customer_id: string | null
  matched_policy_id: string | null
  investigation_due_date: string | null
  sla_breached: boolean
  created_timestamp: string
}
```

### signals.ts
```typescript
export interface MatchingSignals {
  name_similarity_score: number
  policy_match_confidence: number
  customer_match_confidence: number
  account_match: boolean
  amount_match: boolean
  historical_match: boolean
  // Algorithm breakdown
  jaro_winkler_score: number
  levenshtein_score: number
  soundex_match: boolean
  deterministic_score: number
  used_llm: boolean
  llm_score: number
}
// ... AmountSignals, TemporalSignals, RiskSignals, DuplicateSignals — mirror the proto exactly
```

### recommendation.ts
```typescript
export type Recommendation = "apply" | "hold" | "escalate" | "return"
export type ScenarioRoute = "scenario_1" | "scenario_2" | "scenario_3" | "scenario_4" | "scenario_5"
export type DecisionAttribution = "ai_autonomous" | "human_confirmed" | "human_override"

export interface PaymentRecommendation {
  payment_id: string
  recommendation: Recommendation
  confidence_score: number      // 0–100
  scenario_route: ScenarioRoute
  decision_path: string | null
  requires_human_approval: boolean
  approval_reason: string | null
  reasoning: string[]
  suggested_action: string | null
  processing_time_ms: number | null
  decision_attribution: DecisionAttribution | null
  created_at: string
}
```

Also define types for: `CaseAnnotation`, `CaseDocument`, `AuditLogEntry`, `User`, `ConfigurationThreshold`.

---

## Mock fixtures to create

`frontend/src/mocks/payments.ts` — array of 8–10 varied payments:
- 2× scenario_1 (one auto-apply, one hold)
- 1× scenario_2
- 1× scenario_3 (high variance)
- 1× scenario_4 (no match)
- 1× scenario_5 (duplicate)
- 1× processing_failed
- 1× escalated with sla_breached=true

Each mock payment should have matching mock signals, recommendation, audit log (3–5 entries), and 1–2 annotations.

---

## Acceptance criteria
- [ ] TypeScript types mirror the proto/DB schema exactly (amounts in cents, dates as ISO strings)
- [ ] Mock data covers all 5 scenarios + processing_failed + sla_breached cases
- [ ] No `any` types used
- [ ] Types are importable from `@/types/payment`, `@/types/signals`, etc.
""",
    },

    {
        "title": "[Frontend] Queue Dashboard — /",
        "label": "Frontend", "phase": "Phase 1", "estimate": 2, "priority": 2,
        "assignee_hint": "Engineer B",
        "description": """\
## Context
This is Priya's home screen. She opens it each morning and works through the queue top-to-bottom (lowest confidence first = most uncertain cases first). The design is in Figma (see Design Phase 0 ticket).

**Route:** `frontend/src/app/page.tsx` (or `frontend/src/app/(analyst)/page.tsx` if you add route groups)

**Uses mock data from:** `frontend/src/mocks/payments.ts`

---

## Table columns

| Column | Source field | Format |
|--------|-------------|--------|
| Scenario | `recommendation.scenario_route` | Pill: "Sc1" → "Sc5" in different colours |
| Sender Name | `payment.sender_name` | Plain text |
| Amount | `payment.amount` | Format as USD: `$1,500.00` (divide cents by 100) |
| Payment Method | `payment.payment_method` | Plain text |
| AI Recommendation | `recommendation.recommendation` | Coloured pill: APPLY=green, HOLD=amber, ESCALATE=red |
| Confidence | `recommendation.confidence_score` | Band: <40=Low (red), 40–70=Medium (amber), >70=High (green) |
| Age | `payment.created_timestamp` | Relative: "2h ago", "3d ago" |

Default sort: confidence_score ascending (lowest confidence first).

## Filters
- Scenario: multi-select dropdown (All, Sc1–Sc5)
- Confidence Band: multi-select (Low, Medium, High)
- Payment Method: multi-select (ACH, Check, Credit Card, Wire)

Filters are client-side for now (no API call on change).

## PROCESSING_FAILED alert
If any payments in the mock data have `status = "processing_failed"`, show a dismissible amber banner at the top:
> "1 payment failed to process. [Reprocess all]"
Reprocess button is a no-op for now — wire to real API in Phase 2.

## Click behaviour
Clicking any row navigates to `/payments/[payment_id]`.

## Empty state
If no payments match the current filters: show centred text "No payments match your filters." with a "Clear filters" button.

---

## Acceptance criteria
- [ ] Table renders all mock payments correctly
- [ ] Amounts display as USD (not raw cents)
- [ ] Confidence band colours are correct (Low=red, Medium=amber, High=green)
- [ ] Filter combinations work correctly client-side
- [ ] PROCESSING_FAILED banner appears only when relevant mock data is present
- [ ] Row click navigates to correct payment detail URL
- [ ] Empty state shown when all payments are filtered out
""",
    },

    {
        "title": "[Frontend] Investigation Queue — /investigations",
        "label": "Frontend", "phase": "Phase 1", "estimate": 2, "priority": 2,
        "assignee_hint": "Engineer B",
        "description": """\
## Context
Damien's home screen. He only sees `escalated` and `pending_sender_response` payments. Cases are sorted by risk (flagged cases first) then by time since escalation (oldest first = most urgent).

**Route:** `frontend/src/app/investigations/page.tsx`

---

## Table columns

| Column | Source | Format |
|--------|--------|--------|
| Sender Name | `payment.sender_name` | Text |
| Amount | `payment.amount` | USD format |
| Risk | `signals.risk.has_risk_flags` | Red dot icon if true, grey dot if false |
| Payment Method | `payment.payment_method` | Text |
| Scenario | `recommendation.scenario_route` | Pill |
| Time Since Escalation | Last `escalated` audit log entry timestamp | "2d 4h ago" |
| SLA | `payment.sla_breached` | Red "BREACHED" badge if true, else due date in amber if <24h remaining |

## Sort
1. `has_risk_flags = true` first
2. Then by escalation timestamp ascending (oldest first)

No user-facing sort controls needed for Phase 1 (Damien works straight through the list).

## SLA breach state
Payments with `sla_breached = true` should have a row background tinted red (light red, not harsh).
Badge: red pill reading "SLA BREACHED".

## Empty state
"No escalated cases. " with a link back to the Queue Dashboard.

---

## Acceptance criteria
- [ ] Only escalated/pending_sender_response payments shown (filter mock data)
- [ ] Risk indicator icons render correctly
- [ ] SLA breach rows are visually distinct (background tint + badge)
- [ ] Sort order: risk-flagged first, then oldest escalation first
- [ ] Row click navigates to `/payments/[payment_id]`
""",
    },

    {
        "title": "[Frontend] Payment Detail — /payments/[id]",
        "label": "Frontend", "phase": "Phase 1", "estimate": 4, "priority": 2,
        "assignee_hint": "Engineer B",
        "description": """\
## Context
The most important page in the app. Both Priya and Damien use it. It surfaces all the AI's reasoning, the signal evidence, the full audit trail, and lets the user take action. Designed for investigation — not just approval/rejection.

**Route:** `frontend/src/app/payments/[id]/page.tsx`

---

## Section 1 — Payment Header
Show: Payment ID, Sender Name, Amount (USD), Payment Method, Payment Date, Status badge, Matched Policy (if any), Matched Customer (if any).

## Section 2 — Signal Panel
For each of the key matching signals, render a labelled progress bar (0–100):
- Name Similarity Score
- Policy Match Confidence
- Customer Match Confidence

Colour thresholds for bars: <50=red, 50–75=amber, >75=green.

Under "Name Similarity Score", show the algorithm breakdown in a collapsible sub-section:
| Algorithm | Score | Notes |
|-----------|-------|-------|
| Jaro-Winkler | 87.3 | |
| Levenshtein | 82.1 | |
| Soundex | ✓ Match | |
| Deterministic (combined) | 85.2 | |
| LLM (Claude Haiku) | 91.0 | Called — gray zone |
| **Final Score** | **91.0** | max(deterministic, llm) |

If `used_llm = false`, show "LLM: Not called (outside gray zone)" in muted text.

Also show as chips: Amount Variance %, Payment Timing Quality, Risk Flags (red chips for each flag type), Account Status, Payment Method Risk Level.

## Section 3 — AI Reasoning Panel
- Scenario route tag (e.g. "Scenario 1 — Strong Policy Match")
- Recommendation badge (APPLY / HOLD / ESCALATE)
- Confidence score: `87/100`
- Requires human approval: Yes/No
- Reasoning: bullet list from `recommendation.reasoning[]`
- Suggested action: italic text block
- Decision path: monospace text (internal routing notes)

## Section 4 — Audit Timeline
Chronological list of `audit_log` entries for this payment:
- Icon per action type (received=inbox, approved=check, escalated=arrow-up, etc.)
- Actor name + timestamp
- Details badge (hover/click to expand JSON details)

## Section 5 — Annotation Panel
Tabs: "Case Notes" (Priya) | "Investigation Notes" (Damien) | "Contact Log" (Damien)
Each tab shows existing annotations in reverse-chronological order, plus an "Add Note" form at the bottom.

For now, form submit is a no-op (wired to real API in Phase 2).

Contact Log form fields: contacted party, contact method (phone/email/letter), outcome (reached/no answer/voicemail).

## Section 6 — Document Panel
List of documents with: filename, type chip, size, uploader, upload date, Download link (no-op for now).
Upload button: opens file picker, document type dropdown (Supporting Evidence, Bank Statement, etc.) — no-op for now.

## Action Buttons (bottom of page, role-gated)
Show based on `payment.status` and current user's role (use a mock user with role from `localStorage` or hardcode for Phase 1):

- `status=held` + role=analyst: **Approve** (green), **Reject** (red), **Override** (amber)
- `status=escalated` + role=investigator: **Return to Sender** (red), **Log Contact** (blue)
- Override opens a modal: requires reason text before submit (submit disabled until text entered)

All buttons are no-ops in Phase 1 — show a toast "Action will be wired in Phase 2".

---

## Acceptance criteria
- [ ] All 6 sections render with mock data
- [ ] Signal bars are colour-coded correctly
- [ ] Algorithm breakdown table shows correct scores from mock signals
- [ ] Audit timeline renders in chronological order
- [ ] Action buttons show correct set for analyst vs investigator (toggle via mock role)
- [ ] Override modal blocks submit until reason is entered (>0 chars)
- [ ] Page works for all 5 scenario types (uses different mock payments)
""",
    },

    {
        "title": "[Frontend] Settings — /settings",
        "label": "Frontend", "phase": "Phase 1", "estimate": 1, "priority": 3,
        "assignee_hint": "Engineer B",
        "description": """\
## Context
Read-only threshold viewer for most users. Marcus (admin) gets a link to the full config management page (built in Phase 3).

**Route:** `frontend/src/app/settings/page.tsx`

---

## Content

**Threshold table** — 8 rows from `configuration_thresholds` mock data:

| Parameter | Value | Description | Last Changed |
|-----------|-------|-------------|--------------|
| name_match_auto_apply | 90% | Min name similarity for Scenario 1 auto-apply | — |
| name_match_hold | 75% | Hold vs escalate boundary | — |
| ... | | | |

For non-admin roles: table is read-only. Show a muted notice: "Contact your admin to request threshold changes."

For admin role (Marcus): add a "Propose Change" button on each row that links to `/admin/config` (page built in Phase 3).

---

## Acceptance criteria
- [ ] All 8 thresholds shown with correct values from mock data
- [ ] Propose Change button visible only for admin mock role
- [ ] Page works across all 4 role mocks
""",
    },

    # ═══════════════════════════════════════════════════════════════════════
    # PHASE 2 — AI Agent + Persist + Action APIs (Track A: Engineer A)
    # ═══════════════════════════════════════════════════════════════════════

    {
        "title": "[AI] Scenario Router — deterministic routing in router.py",
        "label": "AI", "phase": "Phase 2", "estimate": 2, "priority": 2,
        "assignee_hint": "Engineer A",
        "description": """\
## Context
The router takes the computed `PaymentSignals` and applies a deterministic if/else tree to decide which scenario (1–5) handles this payment. No LLM calls here — this must be 100% predictable and unit-testable.

**File:** `backend/app/services/agent/router.py`

Reference: `docs/Final_Scenario_Definitions.md`, `docs/Executive_Summary_Scenarios.md`

**Depends on:** Signal snapshot complete.

---

## Routing logic (exact order matters)

```python
def route(signals: PaymentSignals, thresholds: dict) -> ScenarioRoute:
    # Scenario 5 ALWAYS runs first — duplicate check
    if signals.duplicate.is_duplicate_match:
        return ScenarioRoute.SCENARIO_5

    name_hold = float(thresholds["name_match_hold"])          # default 75
    amount_tol = float(thresholds["amount_tolerance_auto"])   # default 2

    has_policy_ref = signals.matching.policy_match_confidence >= 50
    name_ok = signals.matching.name_similarity_score >= name_hold
    variance_ok = abs(signals.amount.amount_variance_pct or 0) <= amount_tol

    if has_policy_ref and name_ok and variance_ok:
        return ScenarioRoute.SCENARIO_1

    if has_policy_ref and name_ok and not variance_ok:
        return ScenarioRoute.SCENARIO_3

    customer_match = signals.matching.customer_match_confidence
    supporting = sum([
        signals.matching.account_match,
        signals.matching.amount_match,
        signals.matching.historical_match,
    ])
    if customer_match >= 90 or (customer_match >= 75 and supporting >= 2):
        return ScenarioRoute.SCENARIO_2

    return ScenarioRoute.SCENARIO_4
```

Read all threshold values from DB — never hardcode the numbers.

---

## Acceptance criteria
- [ ] Scenario 5 fires before all others when `is_duplicate_match = true`
- [ ] Unit tests cover: each scenario route, boundary values (exactly 75% name, exactly 2% variance), edge cases (null variance_pct, zero confidence)
- [ ] Router function has zero side effects — takes signals + thresholds dict, returns ScenarioRoute
""",
    },

    {
        "title": "[AI] Scenario 1 — Strong Policy Match",
        "label": "AI", "phase": "Phase 2", "estimate": 2, "priority": 2,
        "assignee_hint": "Engineer A",
        "description": """\
## Context
Scenario 1 handles cases where the payment has a clear policy reference and name/variance thresholds are met. The AI reasons about whether to auto-apply or hold.

**File:** `backend/app/services/agent/scenarios/scenario_1.py`

Reference: `docs/scenarios/Scenario_1_Strong_Policy_Match.md`

---

## Auto-apply path (no human needed)
ALL of these must be true:
- `name_similarity_score > name_match_auto_apply` (default 90%)
- `has_risk_flags = false`
- `account_status = active`
- `payment_method_risk_level = low` (ACH or Credit Card)

If all met → `recommendation=apply`, `requires_human_approval=false`, `decision_attribution=ai_autonomous`

## Hold path (requires analyst review)
If any of these:
- `name_similarity_score` between 75–90%
- `has_risk_flags = true`
- `payment_method_risk_level = medium` or `high`
- Policy status is not `active`

→ `recommendation=hold`, `requires_human_approval=true`

## Claude API prompt structure
```python
prompt = f\"\"\"
You are a payment resolution AI. Analyse this payment for a strong policy match scenario.

Payment: {payment_amount_usd} from {sender_name} via {payment_method}
Matched Policy: {policy_number} ({policy_type}, premium {premium_amount_usd}/month)
Match Quality:
  - Name similarity: {name_score:.1f}% (threshold for auto-apply: {auto_apply_threshold}%)
  - Amount variance: {variance_pct:.2f}%
  - Risk flags: {risk_flag_list or 'none'}
  - Account status: {account_status}

Based on this evidence, provide:
1. recommendation: "apply" or "hold"
2. confidence_score: 0–100 (your certainty)
3. reasoning: list of 2–4 concise reasons
4. suggested_action: one sentence describing what should happen next
\"\"\"
```
Use `instructor` or manual JSON parsing with `response_format={"type": "json_object"}`.

---

## Output shape
```python
@dataclass
class ScenarioResult:
    recommendation: str           # "apply" or "hold"
    confidence_score: float       # 0–100
    scenario_route: str           # "scenario_1"
    decision_path: str            # "auto_apply" or "hold_name_score" or "hold_risk_flag" etc.
    requires_human_approval: bool
    approval_reason: str | None
    reasoning: list[str]
    suggested_action: str | None
    processing_time_ms: int
```

---

## Acceptance criteria
- [ ] Auto-apply fires only when ALL four conditions are met (not just name score)
- [ ] Hold fires when any single condition fails
- [ ] Confidence score is always between 0–100
- [ ] Processing time is measured and stored in `processing_time_ms`
- [ ] Claude API timeout (>10s) raises `RetryableError` — caught by pipeline orchestrator
""",
    },

    {
        "title": "[AI] Scenario 2 — Customer Match, No Policy Reference",
        "label": "AI", "phase": "Phase 2", "estimate": 2, "priority": 2,
        "assignee_hint": "Engineer A",
        "description": """\
## Context
The payment matches a customer but has no policy reference. Human approval is ALWAYS required. The AI's job is to identify the most likely policy and provide reasoning for the analyst.

**File:** `backend/app/services/agent/scenarios/scenario_2.py`

Reference: `docs/scenarios/Scenario_2_Customer_Match_No_Policy.md`

---

## Routing within Scenario 2

**If variance > 15% on any candidate policy:** re-route to Scenario 3 before calling Claude.

**If single candidate policy:**
- `recommendation = apply`, `requires_human_approval = true`
- Claude explains why this policy is the match

**If amount matches exactly one of N policies:**
- `recommendation = apply`, `requires_human_approval = true`
- Claude identifies the disambiguating policy

**If ambiguous (multiple plausible policies, no clear winner):**
- `recommendation = hold`, `requires_human_approval = true`
- Claude lists the candidate policies with evidence for each

---

## Claude API prompt
Include: customer name match score, list of the customer's active policies (policy_number, type, premium, last payment date), payment amount, payment method.

Ask Claude to: identify the most likely target policy, explain the evidence, and note any ambiguity.

---

## Acceptance criteria
- [ ] `requires_human_approval` is ALWAYS `true` for Scenario 2 — no exceptions
- [ ] Variance >15% triggers reroute to Scenario 3 (not a Claude call)
- [ ] Reasoning includes the candidate policy list even when ambiguous
""",
    },

    {
        "title": "[AI] Scenario 3 — High Amount Variance",
        "label": "AI", "phase": "Phase 2", "estimate": 2, "priority": 2,
        "assignee_hint": "Engineer A",
        "description": """\
## Context
A policy match was found but the payment amount differs significantly from the expected premium. The routing logic tiers the response by how extreme the variance is.

**File:** `backend/app/services/agent/scenarios/scenario_3.py`

Reference: `docs/scenarios/Scenario_3_High_Amount_Variance.md`

---

## Variance tiers (read amount_tolerance_auto from DB for the ≤2% tier)

| Variance | Default action | Notes |
|----------|---------------|-------|
| ≤ 2% | Should not reach Sc3 | Router catches this |
| 2–15% | HOLD | Straightforward |
| 15–50% | Check special cases first | See below |
| 50–100% | ESCALATE | |
| > 100% | ESCALATE immediately | Skip Claude — too extreme |

**Name check:** If `name_similarity_score < 90%` at any tier → re-route to Scenario 4 (not a name match). Do this check before calling Claude.

## Special cases for 15–50% variance
Check these in order — if any match, result is HOLD:
1. `is_multi_period = true` — customer prepaying N months
2. `is_multi_method = true` — split premium payment
3. `is_third_party_payment = true` AND `amount <= policy.premium_amount * 1.15` — employer/escrow payment

If no special case matches in 15–50% range → ESCALATE.

## Claude API prompt
Include: variance %, expected vs actual amount, which special case (if any) was triggered, name similarity score.

Ask Claude to: confirm the interpretation, assess risk, provide reasoning and suggested action.

---

## Acceptance criteria
- [ ] >100% variance skips Claude and immediately returns ESCALATE
- [ ] Name < 90% correctly re-routes to Scenario 4 before calling Claude
- [ ] All 3 special cases for 15–50% range trigger HOLD correctly
- [ ] Decision path string clearly indicates which tier and which special case fired
""",
    },

    {
        "title": "[AI] Scenario 4 — No Matching Customer",
        "label": "AI", "phase": "Phase 2", "estimate": 1, "priority": 2,
        "assignee_hint": "Engineer A",
        "description": """\
## Context
All matching failed — no customer or policy could be identified. The primary question is whether this is a third-party payment (employer, family, escrow) for a known policy, or a truly unknown payment.

**File:** `backend/app/services/agent/scenarios/scenario_4.py`

Reference: `docs/scenarios/Scenario_4_No_Matching_Customer.md`

---

## Logic

**Third-party check first:**
If ALL of:
- A policy was found via reference_field_1 parsing (extracted_policy_number is set)
- `is_third_party_payment = true` (sender clearly differs from policyholder)
- `amount_variance_pct <= 15%`

→ `recommendation = hold`, `requires_human_approval = true`
→ `decision_path = "third_party_hold"`

**Otherwise:**
→ `recommendation = escalate`
→ Include best fuzzy match (highest name_similarity_score candidate) in reasoning

## Claude API prompt
Provide: the raw sender_name, the best fuzzy match candidate (customer name + similarity score), payment method, amount, reference fields (raw text).

Ask Claude to: assess whether this is a legitimate third-party payment or an unknown sender, and provide reasoning for the analyst.

---

## Acceptance criteria
- [ ] Third-party hold only fires when all 3 conditions are met (not just is_third_party_payment)
- [ ] Escalation reasoning includes the best fuzzy match candidate name and score
""",
    },

    {
        "title": "[AI] Scenario 5 — Duplicate Payment Detection",
        "label": "AI", "phase": "Phase 2", "estimate": 1, "priority": 2,
        "assignee_hint": "Engineer A",
        "description": """\
## Context
Runs first on every payment. If a duplicate is detected, the AI explains the situation and the balance determines whether to hold or escalate.

**File:** `backend/app/services/agent/scenarios/scenario_5.py`

Reference: `docs/scenarios/Scenario_5_Duplicate_Payment.md`

---

## Logic (mostly deterministic — Claude adds reasoning only)

Duplicate criteria (already computed in Wave 1 `duplicate.py`):
- `is_duplicate_match = true` (3 exact fields + $2 amount tolerance within 72hr window)

**Balance check:**
- `outstanding_balance_cents > 0` → `recommendation = hold` (balance could explain the second payment)
- `outstanding_balance_cents = 0` → `recommendation = escalate` (no reason for second payment)

## Claude API prompt (short — the logic is already decided)
Provide: original payment ID, time between payments, amount difference, current balance.
Ask Claude to: write a clear explanation for the analyst of why this was flagged as a duplicate.

---

## Output
```python
decision_path = "duplicate_hold_balance_outstanding" | "duplicate_escalate_zero_balance"
```

---

## Acceptance criteria
- [ ] Balance=0 → escalate (not hold), even if sender says it's intentional
- [ ] `duplicate_payment_id` is populated in the recommendation details
- [ ] `hours_since_duplicate` and `duplicate_amount_difference` are included in the reasoning context
""",
    },

    {
        "title": "[Backend] Persist layer — persist.py (single-transaction save)",
        "label": "Backend", "phase": "Phase 2", "estimate": 2, "priority": 2,
        "assignee_hint": "Engineer A",
        "description": """\
## Context
After the AI agent produces a `ScenarioResult`, the persist layer writes everything to the DB in one atomic transaction. If any step fails, the whole transaction rolls back.

**File:** `backend/app/services/persist.py`

Reference: `docs/architecture/04_Persist_Layer.md`

---

## Transaction steps (all or nothing)

```python
async def persist_recommendation(payment_id, result, signals, db):
    async with db.begin():
        # 1. INSERT payment_recommendations
        await db.execute(insert(PaymentRecommendation).values(
            payment_id=payment_id,
            recommendation=result.recommendation,
            confidence_score=result.confidence_score,
            scenario_route=result.scenario_route,
            decision_path=result.decision_path,
            requires_human_approval=result.requires_human_approval,
            reasoning=result.reasoning,
            suggested_action=result.suggested_action,
            processing_time_ms=result.processing_time_ms,
            decision_attribution=None,   # set at case closure
        ))

        # 2. UPDATE payments status + matched IDs
        new_status = map_recommendation_to_status(result)
        # apply → 'applied', hold → 'held', escalate → 'escalated'
        await db.execute(update(Payment).where(...).values(
            status=new_status,
            matched_customer_id=signals.matched_customer_id,
            matched_policy_id=signals.matched_policy_id,
        ))

        # 3. Set investigation_due_date if escalated
        if new_status == "escalated":
            sla_hours = await get_threshold(db, "investigation_sla_hours", default=48)
            due = datetime.utcnow() + timedelta(hours=sla_hours)
            await db.execute(update(Payment).where(...).values(investigation_due_date=due))

        # 4. Auto-apply ledger (only if recommendation = apply AND requires_human_approval = false)
        if result.recommendation == "apply" and not result.requires_human_approval:
            await db.execute(insert(PaymentHistory).values(...))
            await db.execute(update(Policy).where(...).values(
                outstanding_balance=Policy.outstanding_balance - payment.amount
            ))

        # 5. Audit log
        await db.execute(insert(AuditLog).values(
            payment_id=payment_id,
            action_type="recommendation_made",
            actor="system",
            details={"recommendation": result.recommendation, "confidence": result.confidence_score}
        ))
```

---

## Acceptance criteria
- [ ] All 5 steps are inside one `db.begin()` block — partial writes are impossible
- [ ] Auto-apply only fires when `requires_human_approval = false`
- [ ] `decision_attribution` is left as NULL at this point (set later by approve/reject/override)
- [ ] Ledger update uses cents arithmetic only — no float math
- [ ] If `payment.amount > policy.outstanding_balance` on auto-apply, log a warning but still apply (edge case — don't block)
""",
    },

    {
        "title": "[Backend] Pipeline orchestrator — pipeline.py (retry wrapper)",
        "label": "Backend", "phase": "Phase 2", "estimate": 1, "priority": 2,
        "assignee_hint": "Engineer A",
        "description": """\
## Context
Wraps the full signal engine + AI agent + persist sequence with retry logic. The ingest endpoint is always fast and always succeeds. The pipeline runs asynchronously after ingest (could be background task or inline for PoC).

**File:** `backend/app/services/pipeline.py`

---

## Retry policy

```python
RETRYABLE = (asyncpg.TooManyConnectionsError, asyncpg.DeadlockDetectedError,
             anthropic.APITimeoutError, anthropic.RateLimitError)
MAX_ATTEMPTS = 3
BACKOFFS = [1, 3]  # seconds before attempt 2 and 3

async def run_pipeline(payment_id: str, db_session):
    for attempt in range(MAX_ATTEMPTS):
        try:
            await run_signals(payment_id, db_session)
            await run_agent(payment_id, db_session)
            await persist(payment_id, db_session)
            return
        except RETRYABLE as e:
            if attempt < MAX_ATTEMPTS - 1:
                await asyncio.sleep(BACKOFFS[attempt])
                continue
            # exhausted — fall through
        except Exception:
            break   # non-retryable — don't retry

    # Mark as failed
    await db_session.execute(
        update(Payment).where(Payment.payment_id == payment_id)
        .values(status="processing_failed")
    )
    await write_audit_log(payment_id, "pipeline_failed", details={"attempts": attempt + 1})
```

---

## Acceptance criteria
- [ ] Exactly 3 attempts maximum
- [ ] Backoffs are 1s then 3s (not random)
- [ ] DB timeouts and Claude rate limits are retryable; validation errors and constraint violations are not
- [ ] After 3 failures: status = `processing_failed`, audit log written
- [ ] Unit test: mock Claude timeout → verify 3 attempts → verify `processing_failed` status
""",
    },

    {
        "title": "[Backend] Approve endpoint — POST /api/payments/{id}/approve",
        "label": "Backend", "phase": "Phase 2", "estimate": 2, "priority": 2,
        "assignee_hint": "Engineer A",
        "description": """\
## Context
Priya (analyst) approves a HELD payment. This applies the payment, updates the ledger, and records that a human confirmed the AI's recommendation.

**File:** `backend/app/routers/approvals.py`
**Auth:** `require_analyst` dependency

---

## Validations
- `payment.status` must be `held` — else 409: `{"error": "invalid_status", "current_status": "..."}`
- User must have role `analyst` — else 403

## Transaction
```python
async with db.begin():
    # 1. Update payment status
    payment.status = "applied"

    # 2. Insert payment_history (ledger entry)
    INSERT payment_history (policy_id, payment_date, amount, payment_method, sender_account, status='applied')

    # 3. Update policy outstanding balance
    UPDATE policies SET outstanding_balance = outstanding_balance - payment.amount
    WHERE policy_number = payment.matched_policy_id

    # 4. Set decision_attribution
    UPDATE payment_recommendations SET decision_attribution = 'human_confirmed'
    WHERE payment_id = ...

    # 5. Audit log — two entries
    INSERT audit_log (action_type='approved', actor=user.name, actor_user_id=user.user_id, details={"approved_by": user.name})
    INSERT audit_log (action_type='applied', actor='system', details={"ledger_updated": true})
```

## Response (200)
```json
{"payment_id": "PMT-001", "status": "applied", "decision_attribution": "human_confirmed"}
```

---

## Acceptance criteria
- [ ] 409 returned if payment is not in `held` status
- [ ] Ledger update and status update are atomic (same transaction)
- [ ] `decision_attribution` set to `human_confirmed`
- [ ] Two audit log entries: one for the human action (APPROVED), one for the ledger update (APPLIED)
- [ ] Works only for analysts — investigators get 403
""",
    },

    {
        "title": "[Backend] Reject, Override, Return, Reprocess endpoints",
        "label": "Backend", "phase": "Phase 2", "estimate": 3, "priority": 2,
        "assignee_hint": "Engineer A",
        "description": """\
## Context
Four action endpoints that complete the analyst and investigator workflows.

**File:** `backend/app/routers/approvals.py` (extend)

---

## POST /api/payments/{id}/reject
**Auth:** analyst only
**Validates:** status must be `held`

Transaction:
1. `payment.status = 'escalated'`
2. Set `investigation_due_date = now() + sla_hours`
3. Audit log: action_type=`'escalated'`, actor=user.name

Response: `{"payment_id": "...", "status": "escalated", "investigation_due_date": "..."}`

---

## POST /api/payments/{id}/override
**Auth:** analyst OR investigator
**Body:** `{"new_recommendation": "apply"|"hold"|"escalate", "reason": "string (required)"}`
**Validates:** status must be `held` or `escalated`. `reason` must be non-empty.

Transaction:
1. Map new_recommendation → new status
2. If new_status = `applied`: INSERT payment_history + UPDATE policy balance (same as approve)
3. INSERT case_annotations: type=`override_reason`, content=reason, author=user
4. UPDATE payment_recommendations: `decision_attribution = 'human_override'`
5. Audit log: action_type=`'overridden'`, details=`{"from": old_rec, "to": new_recommendation, "reason": reason}`

Response: `{"payment_id": "...", "status": "...", "decision_attribution": "human_override"}`

---

## POST /api/payments/{id}/return
**Auth:** investigator only
**Validates:** status must be `escalated` or `pending_sender_response`

Transaction:
1. `payment.status = 'returned'`
2. Audit log: action_type=`'returned'`, actor=user.name

Response: `{"payment_id": "...", "status": "returned"}`

---

## POST /api/payments/{id}/reprocess
**Auth:** analyst or investigator
**Validates:** status must be `processing_failed`

Steps:
1. `payment.status = 'received'`
2. Kick off pipeline again (same as post-ingest)
3. Audit log: action_type=`'received'`, details=`{"reprocessed": true, "attempt": n}`

Response: `{"payment_id": "...", "status": "processing"}`

---

## Acceptance criteria
- [ ] Override is the only endpoint that accepts a reason field — and it's required
- [ ] Return is investigator-only (analyst gets 403)
- [ ] All 4 endpoints return 409 if called in the wrong status
- [ ] Reprocess triggers the full pipeline (not just persist)
""",
    },

    {
        "title": "[Backend] SLA service — sla.py",
        "label": "Backend", "phase": "Phase 2", "estimate": 1, "priority": 3,
        "assignee_hint": "Engineer A",
        "description": """\
## Context
When a payment is escalated, a deadline is set. A background job monitors for breaches and marks cases accordingly.

**File:** `backend/app/services/sla.py`

---

## SLA deadline computation
Called from the reject endpoint and persist layer (for AI-escalated payments).

```python
async def set_investigation_due_date(payment_id: str, db: AsyncSession):
    sla_hours = await get_threshold(db, "investigation_sla_hours", default=48)
    due = datetime.now(timezone.utc) + timedelta(hours=float(sla_hours))
    await db.execute(
        update(Payment).where(Payment.payment_id == payment_id)
        .values(investigation_due_date=due)
    )
```

## Breach detection (background job)
For PoC: run as a FastAPI startup background task using `asyncio.create_task` (not a proper scheduler — flag this as tech debt for production).

```python
async def check_sla_breaches(interval_seconds=300):
    while True:
        async with AsyncSessionLocal() as db:
            breached = await db.execute(
                select(Payment).where(
                    Payment.status.in_(["escalated", "pending_sender_response"]),
                    Payment.sla_breached == False,
                    Payment.investigation_due_date < datetime.now(timezone.utc)
                )
            )
            for payment in breached.scalars():
                payment.sla_breached = True
                await write_audit_log(db, payment.payment_id, "sla_breached", actor="system")
            await db.commit()
        await asyncio.sleep(interval_seconds)
```

---

## Acceptance criteria
- [ ] `investigation_due_date` is set on every escalation (both AI and human)
- [ ] Breach check runs every 5 minutes in background
- [ ] `sla_breached` is only flipped from false → true (never reversed)
- [ ] Audit log entry written for every breach event
- [ ] `investigation_sla_hours` threshold readable from DB (add to seed data: default 48)
""",
    },

    {
        "title": "[Backend] GET /api/payments (list) + GET /api/payments/{id} (detail)",
        "label": "Backend", "phase": "Phase 2", "estimate": 3, "priority": 2,
        "assignee_hint": "Engineer B",
        "description": """\
## Context
The two most-used read endpoints. Powers the Queue Dashboard (list) and Payment Detail page (detail).

**File:** `backend/app/routers/payments.py`

---

## GET /api/payments

Query params:
- `status`: comma-separated list of statuses (e.g. `held,processing_failed`)
- `scenario`: `scenario_1` … `scenario_5`
- `date_from` / `date_to`: ISO 8601 date strings
- `search`: string — partial match on `sender_name` (ILIKE `%search%`)
- `sort_by`: `confidence_score` (asc) | `payment_date` (desc) | `has_risk_flags` (desc) | `payment_method`
- `limit`: default 50, max 200
- `offset`: default 0

Response:
```json
{
  "total": 142,
  "payments": [
    {
      "payment_id": "PMT-001",
      "sender_name": "Robert Johnson",
      "amount": 150000,
      "payment_method": "ACH",
      "payment_date": "...",
      "status": "held",
      "scenario_route": "scenario_1",
      "recommendation": "hold",
      "confidence_score": 62.5,
      "has_risk_flags": false,
      "sla_breached": false,
      "age_hours": 4.2
    }
  ]
}
```

The list endpoint joins `payments` with `payment_recommendations` (LEFT JOIN — may not exist for processing_failed).

## GET /api/payments/{id}

Full join across 6 tables:
```python
payment         = await get_payment(db, payment_id)
signals         = await get_signals(db, payment_id)       # payment_signals
recommendation  = await get_recommendation(db, payment_id) # payment_recommendations
audit_log       = await get_audit_log(db, payment_id)      # ordered by timestamp asc
annotations     = await get_annotations(db, payment_id)    # ordered by created_at asc
documents       = await get_documents(db, payment_id)      # is_deleted=false only
```

Return all as a single nested JSON object.

---

## Acceptance criteria
- [ ] List endpoint uses SQLAlchemy query builder — no raw SQL string interpolation for filter values
- [ ] `total` reflects unfiltered count (for pagination UI)
- [ ] Detail endpoint returns 404 if payment_id does not exist
- [ ] Documents in detail response exclude soft-deleted files
- [ ] `age_hours` is computed server-side (not stored)
""",
    },

    {
        "title": "[Backend] Annotations + Documents endpoints",
        "label": "Backend", "phase": "Phase 2", "estimate": 3, "priority": 2,
        "assignee_hint": "Engineer B",
        "description": """\
## Context
Analysts and investigators annotate cases and attach supporting documents throughout their workflows.

**Files:**
- `backend/app/routers/annotations.py`
- `backend/app/routers/documents.py`
- `backend/app/services/storage.py` — document storage abstraction

---

## Annotations

### POST /api/payments/{id}/annotations
**Auth:** any authenticated user

Body:
```json
{
  "annotation_type": "case_note",   // case_note | override_reason | contact_record | investigation_note
  "content": "Payment looks legitimate — employer paying on behalf of employee",
  // contact_record only:
  "contact_method": "phone",        // phone | email | letter
  "contact_outcome": "reached",     // reached | no_answer | voicemail | bounced
  "contacted_party": "Robert Johnson"
}
```

Side effect: If `annotation_type = "contact_record"` AND `payment.status = "escalated"`:
→ UPDATE `payment.status = "pending_sender_response"`
→ Write CONTACT_LOGGED audit log entry

Response 201: the created annotation object.

### GET /api/payments/{id}/annotations
Returns all annotations for the payment ordered by `created_at` asc.

---

## Documents

### POST /api/payments/{id}/documents
**Auth:** any authenticated user
Content-Type: `multipart/form-data`

Fields: `file` (binary), `document_type` (enum string), `description` (optional string)

Processing:
1. Validate file size ≤ 10MB, MIME type in allowed list (PDF, PNG, JPG, DOCX)
2. Generate storage path: `payments/{payment_id}/{uuid4}_{filename}`
3. Write via `storage.py` → local filesystem at `backend/uploads/` for PoC
4. INSERT `case_documents` row
5. Write DOCUMENT_UPLOADED audit log entry

Response 201: document metadata (no file bytes).

### GET /api/payments/{id}/documents
Returns list of non-deleted document metadata.

### GET /api/payments/{id}/documents/{doc_id}
Streams the file using `FileResponse` (fastapi) or chunked async generator.

### DELETE /api/payments/{id}/documents/{doc_id}
Soft delete only: `UPDATE case_documents SET is_deleted = true`. Never deletes the file from storage.

---

## storage.py abstraction
```python
class StorageBackend(Protocol):
    async def write(self, path: str, data: bytes) -> None: ...
    async def read(self, path: str) -> bytes: ...

class LocalStorageBackend:
    root = Path("uploads")
    async def write(self, path, data): (self.root / path).parent.mkdir(...); (self.root / path).write_bytes(data)
    async def read(self, path): return (self.root / path).read_bytes()
```

---

## Acceptance criteria
- [ ] CONTACT_RECORD annotation correctly triggers PENDING_SENDER_RESPONSE status transition
- [ ] File upload validates MIME type — `.exe` and other non-document types rejected with 400
- [ ] Download endpoint streams (does not load entire file into memory)
- [ ] Soft delete does not expose deleted documents in the list endpoint
""",
    },

    {
        "title": "[Frontend] Wire analyst/investigator pages to real APIs",
        "label": "Frontend", "phase": "Phase 2", "estimate": 2, "priority": 2,
        "assignee_hint": "Engineer B",
        "description": """\
## Context
Replace all mock data in the 4 analyst/investigator pages with real API calls. The API contract is already defined by the mock types — no structural changes needed.

**Base URL:** read from `NEXT_PUBLIC_API_URL` env var (default `http://localhost:8000`)

---

## Pages to wire

### Queue Dashboard `/`
Replace mock array with:
```typescript
const { data, isLoading, error } = useSWR('/api/payments?status=held,processing_failed&sort_by=confidence_score', fetcher)
```
Use `swr` (install: `npm install swr`) for data fetching with automatic revalidation.

### Investigation Queue `/investigations`
```typescript
useSWR('/api/payments?status=escalated,pending_sender_response&sort_by=has_risk_flags', fetcher)
```

### Payment Detail `/payments/[id]`
```typescript
useSWR(`/api/payments/${id}`, fetcher)
```
Action buttons now call real endpoints. On success: invalidate the SWR cache for this payment_id and show a success toast.

Override modal: `POST /api/payments/{id}/override` with `{new_recommendation, reason}`.

### Settings `/settings`
```typescript
useSWR('/api/settings/thresholds', fetcher)
```

---

## Auth
Add an `Authorization: Bearer <token>` header to all requests.
For PoC: store the JWT in `localStorage` after login. Add a simple login page at `/login` that calls `POST /api/auth/token` (username = user_id, password = anything).

---

## Error handling
- Network error / 500: show red toast "Something went wrong. Try again."
- 401: redirect to `/login`
- 403: show amber toast "You don't have permission to do that."
- 404: show "Payment not found" inline (not a toast)

## Loading states
Use skeleton components (install shadcn `skeleton` component: `npx shadcn add skeleton`) for:
- Table rows in Queue and Investigations
- Signal bars in Payment Detail

---

## Acceptance criteria
- [ ] No mock data imported in production code paths
- [ ] SWR used for all GET requests (not useEffect + useState)
- [ ] All 4 action buttons (approve/reject/override/return) call real endpoints
- [ ] JWT stored and sent correctly
- [ ] Auth error → redirect to login (not a toast)
- [ ] Loading skeletons shown during fetch
""",
    },

    # ═══════════════════════════════════════════════════════════════════════
    # PHASE 3 — Analytics, Governance, Config APIs + Director/Admin Frontend
    # ═══════════════════════════════════════════════════════════════════════

    {
        "title": "[Backend] Analytics endpoints — GET /api/analytics/decisions + overrides",
        "label": "Backend", "phase": "Phase 3", "estimate": 3, "priority": 3,
        "assignee_hint": "Engineer A",
        "description": """\
## Context
Powers Lorraine's Governance Dashboard and Marcus's Admin Dashboard. These are aggregation queries over `payment_recommendations` joined with `payments`.

**File:** `backend/app/routers/analytics.py`

---

## GET /api/analytics/decisions
Query params: `date_from`, `date_to` (ISO dates)

Response shape:
```json
{
  "summary": {
    "auto_applied_by_ai": 412,
    "applied_after_human_review": 88,
    "held_pending_review": 34,
    "escalated_by_ai": 61,
    "escalated_by_human": 22,
    "human_overrides": 15,
    "returned": 8
  },
  "override_rate_pct": 4.2,
  "by_payment_method": [
    {"method": "ACH", "count": 310, "auto_apply_rate_pct": 72.1}
  ],
  "by_scenario": [
    {
      "scenario": "scenario_1",
      "volume": 280,
      "auto_applied": 198,
      "human_confirmed": 55,
      "human_overrides": 12,
      "avg_confidence": 84.2,
      "decision_distribution": {"apply": 253, "hold": 18, "escalate": 9}
    }
  ],
  "confidence_histogram": [
    {"bucket": "0-10", "count": 3},
    {"bucket": "10-20", "count": 7},
    ...
    {"bucket": "90-100", "count": 198}
  ]
}
```

SQL notes: use `GROUP BY scenario_route` and `CASE WHEN decision_attribution = 'ai_autonomous' THEN 1 END` counts. Histogram uses `floor(confidence_score / 10) * 10` bucketing.

## GET /api/analytics/overrides
Query params: `scenario`, `confidence_band` (low/medium/high), `date_from`, `date_to`, `reason_category`

Returns paginated list of override events with: payment_id, scenario, original AI recommendation, human decision, confidence score, override reason (from annotation), override date, analyst name.

---

## Acceptance criteria
- [ ] Date range filter applied to both endpoints
- [ ] Histogram has exactly 10 buckets (0–10 through 90–100), even if count=0
- [ ] `override_rate_pct = human_overrides / (total_closed_payments) * 100`
- [ ] Add DB indexes needed: `payments(status, created_timestamp)`, `payment_recommendations(scenario_route, decision_attribution)` — add in a new Alembic migration
""",
    },

    {
        "title": "[Backend] Governance endpoints — reviews, anomaly flags, export",
        "label": "Backend", "phase": "Phase 3", "estimate": 2, "priority": 3,
        "assignee_hint": "Engineer A",
        "description": """\
## Context
Lorraine uses these to record period reviews, flag anomalies for Marcus, and export compliance reports.

**File:** `backend/app/routers/governance.py`

---

## POST/GET /api/governance/reviews
POST body: `{period_start, period_end, notes, export_generated}`
GET returns: list ordered by review_timestamp desc.

## POST/GET /api/governance/anomalies
POST body: `{metric_name, scenario_type, description, period_start, period_end}` — auto-assigns to Marcus (USR-0004).
GET query params: `status` (open/investigating/resolved)

## PATCH /api/governance/anomalies/{id}
Body: `{status, resolution_notes}` — Marcus updates as he investigates.

## GET /api/governance/export
Query params: `date_from`, `date_to`, `scope` (decisions|overrides|config_changes|all)

Returns a structured JSON report (not a CSV for PoC). Include:
- Period summary (date range, total payments processed)
- Decision attribution breakdown
- Override log (payment_id, original rec, human decision, reason, analyst)
- Config changes deployed in period (parameter, old value, new value, rationale, approver)

Set `Content-Disposition: attachment; filename=ces_export_{date}.json` header.

---

## Acceptance criteria
- [ ] Export includes all three sections when scope=all
- [ ] Anomaly auto-assign to Marcus (hard-coded to USR-0004 for PoC — flag as tech debt)
- [ ] PATCH only updates status + resolution_notes — other fields immutable
""",
    },

    {
        "title": "[Backend] Config change-request workflow (propose → approve → deploy → rollback)",
        "label": "Backend", "phase": "Phase 3", "estimate": 3, "priority": 3,
        "assignee_hint": "Engineer A",
        "description": """\
## Context
Every change to a configuration threshold must go through a formal approval workflow: Marcus proposes → Lorraine approves/rejects → Marcus deploys → emergency rollback if needed.

**File:** `backend/app/routers/config.py`

---

## Endpoints

### POST /api/settings/change-requests
**Auth:** admin only (Marcus)
Body: `{parameter_name, current_value, proposed_value, rationale, projected_impact}`

Validates: `parameter_name` must exist in `configuration_thresholds`.
`current_value` must match the current active value (prevents stale proposals).

INSERT `configuration_change_requests` with `status=pending`. Write CONFIG_CHANGE_PROPOSED audit log.

### GET /api/settings/change-requests
Query params: `status` filter. Returns list ordered by `proposed_at` desc.

### POST /api/settings/change-requests/{id}/approve
**Auth:** director only (Lorraine)
Validates: status must be `pending`.
UPDATE status → `approved`. Write CONFIG_CHANGE_APPROVED audit log.

### POST /api/settings/change-requests/{id}/reject
**Auth:** director only
Body: `{review_comment}` (required)
UPDATE status → `rejected`. Write CONFIG_CHANGE_REJECTED audit log.

### POST /api/settings/change-requests/{id}/deploy
**Auth:** admin only
Validates: status must be `approved`.

Atomic transaction:
1. UPDATE `configuration_thresholds SET parameter_value = proposed_value, effective_date = now()`
2. INSERT `configuration_threshold_history (parameter_name, parameter_value=old_value, effective_to=now(), ...)`
3. INSERT `configuration_threshold_history (parameter_name, parameter_value=new_value, effective_from=now(), effective_to=null, ...)`
4. UPDATE change_request status → `deployed`, `deployed_at = now()`
5. Write CONFIG_CHANGE_DEPLOYED audit log.

### POST /api/settings/change-requests/{id}/rollback
**Auth:** admin — but requires a separate `approved_by` field in body (Lorraine's user_id as confirmation).
Reverses the deploy: swaps the threshold value back to the previous version in history.

### GET /api/settings/thresholds
Returns current active values for all 8 parameters.

### GET /api/settings/thresholds/history
Returns all `configuration_threshold_history` rows ordered by `effective_from` desc.

---

## Acceptance criteria
- [ ] Deploy is atomic — partial failure rolls back all 5 steps
- [ ] Cannot deploy a rejected request (status check)
- [ ] Rollback requires explicit director confirmation (not just admin auth alone)
- [ ] History table always has exactly one row per parameter with `effective_to=null` (the active version)
""",
    },

    {
        "title": "[Frontend] Governance Dashboard — /governance",
        "label": "Frontend", "phase": "Phase 3", "estimate": 3, "priority": 3,
        "assignee_hint": "Engineer B",
        "description": """\
## Context
Lorraine's primary dashboard. She checks this weekly to monitor system health and compliance posture.

**Route:** `frontend/src/app/governance/page.tsx`
**Data:** `GET /api/analytics/decisions?date_from=...&date_to=...`

---

## Layout

**Date range filter** — top of page, applies to all charts and cards. Default: last 30 days.

**Metric cards (6):**
Each card shows: label, current value, and a secondary stat (% of total or vs previous period).
- Auto-Applied by AI → `summary.auto_applied_by_ai`
- Applied after Human Review → `summary.applied_after_human_review`
- Held Pending Review → `summary.held_pending_review`
- Escalated by AI → `summary.escalated_by_ai`
- Escalated by Human → `summary.escalated_by_human`
- Human Overrides → `summary.human_overrides` + `override_rate_pct` as secondary stat

**Charts** (use `recharts` — install: `npm install recharts`):
1. Payment method breakdown — bar chart, x=method, y=count, second bar=auto_apply_rate_pct
2. Override rate trend — will need a time-series endpoint in Phase 3+ (stub with static data for now)
3. SLA adherence — single number card: `% of escalations resolved before sla_breached`
4. Confidence histogram — bar chart from `confidence_histogram` array

---

## Acceptance criteria
- [ ] Date range filter change re-fetches data (not cached from previous range)
- [ ] All 6 metric cards show real values from API
- [ ] Charts render without errors on empty data (date range with no payments)
- [ ] recharts is used (not custom SVG)
""",
    },

    {
        "title": "[Frontend] Compliance Export — /governance/export",
        "label": "Frontend", "phase": "Phase 3", "estimate": 1, "priority": 3,
        "assignee_hint": "Engineer B",
        "description": """\
## Context
Simple page for Lorraine to download a structured export for her compliance records.

**Route:** `frontend/src/app/governance/export/page.tsx`
**API:** `GET /api/governance/export?date_from=...&date_to=...&scope=...`

---

## Layout

1. Date range picker (start, end) — use shadcn `Calendar` or a simple date input for PoC
2. Export scope checkboxes:
   - [ ] Decisions (payment-level decisions + attribution)
   - [ ] Override Log (all human overrides with reasons)
   - [ ] Config Changes (threshold changes deployed in period)
   - Quick select: [Select All]
3. Download button — disabled until at least one scope is selected and both dates are set
4. Last export info: "Last downloaded: April 15, 2026 by Lorraine Chen" (from `governance_reviews` list)

On download: trigger `GET /api/governance/export` with query params, use `Content-Disposition` header to auto-download the file.

---

## Acceptance criteria
- [ ] Download button disabled until form is complete
- [ ] Correct query params sent to API (scope as comma-separated list)
- [ ] File download works (browser prompts save dialog)
""",
    },

    {
        "title": "[Frontend] Exception Dashboard — /governance/exceptions",
        "label": "Frontend", "phase": "Phase 3", "estimate": 2, "priority": 3,
        "assignee_hint": "Engineer B",
        "description": """\
## Context
Lorraine's escalation view. She monitors SLA breaches, active anomaly flags, and config changes awaiting her decision.

**Route:** `frontend/src/app/governance/exceptions/page.tsx`

---

## Section 1 — SLA Breached Cases
Data: `GET /api/payments?sla_breached=true&status=escalated,pending_sender_response`

Table: Payment ID (link to detail), Sender Name, Amount, Scenario, Time Since Breach, Assigned Investigator.
Row background: light red.
If empty: "No SLA breaches. All cases are on track."

## Section 2 — Anomaly Flags
Data: `GET /api/governance/anomalies?status=open,investigating`

Table: Metric Name, Description, Period, Flagged By, Status chip (Open=red/Investigating=amber/Resolved=green), Resolution Notes (truncated).
Each row has "View Details" that expands inline.

## Section 3 — Config Changes Pending Approval
Data: `GET /api/settings/change-requests?status=pending`

For each: Parameter name, Current value, Proposed value, Rationale (truncated), Proposed by Marcus, Proposed date.
Two buttons per row: **Approve** (green) → `POST .../approve`, **Reject** (red) → opens modal requiring `review_comment`.

On approve/reject: refresh the list.

---

## Acceptance criteria
- [ ] Three sections each independently fetch their data
- [ ] Reject modal requires non-empty review_comment before submission
- [ ] Approve/reject actions call real endpoints and refresh the list
- [ ] All three empty states are handled gracefully
""",
    },

    {
        "title": "[Frontend] Admin Dashboard — /admin",
        "label": "Frontend", "phase": "Phase 3", "estimate": 2, "priority": 3,
        "assignee_hint": "Engineer B",
        "description": """\
## Context
Marcus's analytics view. He uses this to spot patterns in AI performance, catch scenarios that are over/under-performing, and decide when to tune thresholds.

**Route:** `frontend/src/app/admin/page.tsx`
**Data:** `GET /api/analytics/decisions`

---

## Layout

**Scenario tabs** — tabs across the top: "All" | "Scenario 1" | "Scenario 2" | "Scenario 3" | "Scenario 4" | "Scenario 5"

Selecting a tab filters all charts to that scenario's data from `by_scenario[]`.

**4 charts per tab** (using recharts):
1. Case volume trend — stub with static weekly data for now (time-series endpoint not built)
2. Decision distribution pie — slices: AI Autonomous, Human Confirmed, Human Override
3. Override rate by confidence band — grouped bar: x=confidence band (Low/Medium/High), y=override_rate_pct
4. Confidence histogram — bar chart from `confidence_histogram`

**Summary numbers** (above charts): Volume, Avg Confidence, Override Count for selected scenario.

---

## Acceptance criteria
- [ ] Tab switching updates all charts simultaneously
- [ ] "All" tab aggregates across all scenarios
- [ ] Charts render correctly when a scenario has 0 payments
""",
    },

    {
        "title": "[Frontend] Override Analysis — /admin/overrides",
        "label": "Frontend", "phase": "Phase 3", "estimate": 1, "priority": 3,
        "assignee_hint": "Engineer B",
        "description": """\
## Context
Marcus uses this to understand why analysts are overriding the AI — the primary feedback loop for threshold tuning.

**Route:** `frontend/src/app/admin/overrides/page.tsx`
**Data:** `GET /api/analytics/overrides`

---

## Filter bar
- Scenario: dropdown (All, Sc1–Sc5)
- Confidence Band: dropdown (All, Low <40, Medium 40–70, High >70)
- Date Range: date inputs
- Override Reason Category: free text search against reason content

Filters trigger API refetch (not client-side filter).

## Table
Columns: Payment ID (link), Scenario, AI Recommendation, Human Decision, Confidence Score, Override Reason (truncated to 80 chars, expand on hover), Override Date, Analyst Name.

## Empty state
"No overrides match your filters."

---

## Acceptance criteria
- [ ] Filters refetch from API (not client-side)
- [ ] Payment ID links go to the correct detail page
- [ ] Override reason truncation + expand works
""",
    },

    {
        "title": "[Frontend] Configuration Management — /admin/config",
        "label": "Frontend", "phase": "Phase 3", "estimate": 3, "priority": 3,
        "assignee_hint": "Engineer B",
        "description": """\
## Context
Marcus's most powerful tool — and the one with the strictest workflow. Any mistake in thresholds could cause systematic mis-routing of payments.

**Route:** `frontend/src/app/admin/config/page.tsx`

---

## Section 1 — Current Thresholds
Table with 8 rows. Columns: Parameter Name, Current Value, Description, Last Changed (from history), Changed By.
Each row: "Propose Change" button → opens the Propose Change form (section 2).

## Section 2 — Propose Change Form
Pre-fills `parameter_name` and `current_value` (read-only) from clicked row.
Fields:
- Proposed Value (input — validated as number)
- Rationale (textarea, required, min 20 chars)
- Projected Impact (textarea, optional)

Submit → `POST /api/settings/change-requests`. On success: scroll to Section 3 and highlight the new request.

## Section 3 — Change Request List
Tabs: Pending | Approved | Deployed | Rejected | All

Each row: Parameter, Current → Proposed, Rationale (truncated), Status chip, Proposed Date.

Status-specific actions:
- PENDING: no actions for Marcus (waiting on Lorraine)
- APPROVED: **Deploy** button (green) → `POST .../deploy` → confirmation dialog ("This will immediately affect all new payments. Deploy?")
- DEPLOYED: **Rollback** button (red) → modal requiring Lorraine's user_id as confirmation (text field: "Enter director's user ID to confirm rollback")

## Section 4 — Version History
Accordion per parameter showing all `configuration_threshold_history` rows: value, changed by, approved by, effective from/to, change request link.

---

## Acceptance criteria
- [ ] Propose form pre-fills parameter name from the clicked row
- [ ] Rationale field enforces minimum 20 characters before submit
- [ ] Deploy shows confirmation dialog before calling API
- [ ] Rollback modal requires director user ID entry (not just a click)
- [ ] After deploy/rollback: current thresholds table auto-refreshes
""",
    },

    # ═══════════════════════════════════════════════════════════════════════
    # PHASE 4 — Integration & Polish
    # ═══════════════════════════════════════════════════════════════════════

    {
        "title": "[QA] E2E tests — all 5 scenarios",
        "label": "QA", "phase": "Phase 4", "estimate": 5, "priority": 2,
        "assignee_hint": "Engineer A",
        "description": """\
## Context
End-to-end tests that exercise the full pipeline — ingest → signals → route → recommend → persist — for every scenario. Use the seeded test data (customers/policies/payment_history in `scripts/seed.py`).

**Test framework:** pytest + pytest-asyncio (already in requirements.txt)
**File:** `backend/tests/e2e/test_scenarios.py`

---

## Scenario 1 — Strong Policy Match
```
Test 1a (auto-apply): POST ingest {sender_name="Robert Johnson", amount=150000, reference="POL-00001", method="ACH"}
  → pipeline runs
  → payment.status = "applied"
  → decision_attribution = "ai_autonomous"
  → payment_history row created

Test 1b (hold — ambiguous name): POST ingest {sender_name="Rob Johnston", amount=150000, reference="POL-00001"}
  → name score in gray zone after Haiku
  → payment.status = "held"
  → requires_human_approval = true

Test 1c (hold — risk flag): POST ingest {sender_name="James Wilson", amount=200000, reference="POL-00004"}
  → CUST-0003 has fraud_history flag
  → payment.status = "held" despite name match >90%
```

## Scenario 2 — Customer Match, No Policy
```
Test 2a: POST ingest {sender_name="Robert Johnson", amount=150000, no reference}
  → two matching policies (POL-00001, POL-00002)
  → recommendation = hold (ambiguous)
  → requires_human_approval = true
```

## Scenario 3 — High Amount Variance
```
Test 3a (2–15% variance): POST ingest {amount=145000 (3.3% under), reference="POL-00001"}
  → recommendation = hold

Test 3b (multi-period 15–50%): POST ingest {amount=450000 (3x premium), reference="POL-00001"}
  → is_multi_period = true
  → recommendation = hold

Test 3c (>100% variance): POST ingest {amount=500000, reference="POL-00001"}
  → recommendation = escalate, no special case
```

## Scenario 4 — No Matching Customer
```
Test 4a: POST ingest {sender_name="Unknown Person XYZ", amount=99999, no reference}
  → no match found
  → recommendation = escalate

Test 4b (third-party): POST ingest {sender_name="ACME Corp Payroll", beneficiary_name="Robert Johnson", amount=150000, reference="POL-00001"}
  → is_third_party_payment = true
  → recommendation = hold
```

## Scenario 5 — Duplicate
```
Test 5a: POST ingest payment A, then POST ingest identical payment B within 5 minutes
  → payment B: is_duplicate_match = true, scenario_route = scenario_5
  → outstanding_balance > 0 → recommendation = hold

Test 5b: Same but balance = 0 → recommendation = escalate

Test 5c: Same sender but 80 hours later → NOT a duplicate
```

---

## Acceptance criteria
- [ ] All 10 test cases pass
- [ ] Tests run against a real Postgres instance (no mocking DB)
- [ ] Each test cleans up its payments after running (or uses a separate test DB)
- [ ] Tests complete in under 60 seconds total (Haiku calls are the bottleneck — mock in unit tests, allow in e2e)
""",
    },

    {
        "title": "[QA] E2E tests — analyst and investigator action flows",
        "label": "QA", "phase": "Phase 4", "estimate": 3, "priority": 2,
        "assignee_hint": "Engineer A",
        "description": """\
## Context
Tests that verify the human action endpoints work correctly and set the right `decision_attribution` values.

**File:** `backend/tests/e2e/test_actions.py`

---

## Test cases

### Approve flow
```
1. Ingest a payment → pipeline produces HELD recommendation
2. POST /api/payments/{id}/approve (as USR-0001 Priya)
3. Assert: payment.status = "applied"
4. Assert: decision_attribution = "human_confirmed"
5. Assert: payment_history row created with correct amount
6. Assert: policy.outstanding_balance decreased by payment amount
7. Assert: audit_log has APPROVED + APPLIED entries in order
```

### Reject flow
```
1. Ingest → HELD
2. POST /api/payments/{id}/reject (as Priya)
3. Assert: payment.status = "escalated"
4. Assert: investigation_due_date is set (approximately 48h from now)
5. Assert: decision_attribution remains null (not set until final closure)
```

### Override flow (apply)
```
1. Ingest → HELD with recommendation=hold
2. POST /api/payments/{id}/override {new_recommendation: "apply", reason: "Verified with customer directly"} (as Priya)
3. Assert: payment.status = "applied"
4. Assert: decision_attribution = "human_override"
5. Assert: case_annotation created with type=override_reason and correct content
6. Assert: ledger updated
```

### Override flow (escalate)
```
1. Ingest → HELD
2. POST /api/payments/{id}/override {new_recommendation: "escalate", reason: "Looks fraudulent"}
3. Assert: payment.status = "escalated"
4. Assert: decision_attribution = "human_override"
```

### Return flow (Damien)
```
1. Ingest → ESCALATED
2. POST /api/payments/{id}/return (as USR-0002 Damien)
3. Assert: payment.status = "returned"
4. Assert: 403 if attempted by analyst (Priya)
```

### Reprocess flow
```
1. Manually set a payment to processing_failed
2. POST /api/payments/{id}/reprocess
3. Assert: payment eventually reaches a terminal status (held/applied/escalated) — not processing_failed
```

---

## Acceptance criteria
- [ ] All 6 flows pass
- [ ] Role enforcement tested: Priya cannot return, Damien cannot approve
- [ ] `decision_attribution` correct for each path
""",
    },

    {
        "title": "[QA] E2E tests — config workflow and retry/failure behaviour",
        "label": "QA", "phase": "Phase 4", "estimate": 2, "priority": 2,
        "assignee_hint": "Engineer A",
        "description": """\
## Context
Tests the config change workflow end-to-end, and verifies the retry/failure behaviour under simulated errors.

**File:** `backend/tests/e2e/test_config_and_retry.py`

---

## Config workflow test
```
1. GET /api/settings/thresholds → record current name_match_hold value (75)
2. POST /api/settings/change-requests (as Marcus): propose name_match_hold → 80
3. Assert: status = pending
4. POST .../reject (as Lorraine): review_comment = "Not justified at this time"
5. Assert: status = rejected; GET thresholds → still 75

6. POST new change-request: propose 80 again
7. POST .../approve (as Lorraine)
8. Assert: status = approved
9. POST .../deploy (as Marcus)
10. Assert: status = deployed
11. GET /api/settings/thresholds → name_match_hold = 80
12. POST /api/settings/change-requests/{id}/rollback (as Marcus, with Lorraine's user_id)
13. GET thresholds → name_match_hold = 75 again
14. GET /api/settings/thresholds/history → shows 3 versions (75 → 80 → 75)
```

## Retry / failure test
```
1. Monkey-patch the Claude client to raise anthropic.APITimeoutError for the first 2 calls, succeed on the 3rd
2. POST ingest
3. Assert: pipeline completes successfully on 3rd attempt
4. Assert: audit_log shows no pipeline_failed entry

5. Monkey-patch Claude to always raise APITimeoutError
6. POST ingest
7. Assert: payment.status = "processing_failed" after 3 attempts
8. Assert: audit_log shows pipeline_failed entry with attempts=3
```

---

## Acceptance criteria
- [ ] Config deploy is reflected immediately in threshold GET
- [ ] Rollback requires Lorraine's user_id — rejected without it (403)
- [ ] Retry test shows exactly 3 attempts in logs/audit
- [ ] Constraint violation (e.g. duplicate payment_id) is NOT retried
""",
    },

    {
        "title": "[QA] Frontend integration testing — all 10 pages with real APIs",
        "label": "QA", "phase": "Phase 4", "estimate": 2, "priority": 2,
        "assignee_hint": "Engineer B",
        "description": """\
## Context
Manual integration testing across all 10 pages with the backend running. Focus on role-gating, edge cases, and states that mock data couldn't cover.

**Prerequisite:** Backend running at :8000, DB seeded, at least 10 test payments in various states.

---

## Test checklist

### Queue Dashboard
- [ ] HELD payments displayed, sorted by confidence ascending
- [ ] Filters work: scenario, confidence band, payment method
- [ ] PROCESSING_FAILED alert appears when relevant
- [ ] Clicking a row navigates to correct payment detail

### Investigation Queue
- [ ] Only escalated/pending_sender_response shown (not held)
- [ ] SLA breached row visually distinct
- [ ] Sorted by risk flag first, then age

### Payment Detail
- [ ] All 6 sections render with real data
- [ ] Approve button works: payment moves to applied
- [ ] Reject button works: payment moves to escalated
- [ ] Override modal blocks submit on empty reason
- [ ] Override with reason works: decision_attribution becomes human_override
- [ ] Add annotation works: appears in list immediately (optimistic update or re-fetch)
- [ ] Document upload works: file appears in document list
- [ ] Return button only visible to investigator (USR-0002) — not to Priya (USR-0001)

### Settings
- [ ] All 8 thresholds shown with real values
- [ ] Propose Change link visible only for Marcus (USR-0004)

### Governance Dashboard (Lorraine)
- [ ] Metric cards show real counts
- [ ] Date range filter changes chart data
- [ ] All 4 charts render

### Compliance Export
- [ ] Download produces a file
- [ ] Scope filter affects export content

### Exception Dashboard
- [ ] SLA-breached cases shown (if any)
- [ ] Approve/reject on pending config changes works

### Admin Dashboard (Marcus)
- [ ] Scenario tabs switch chart data
- [ ] Confidence histogram correct bucket counts

### Override Analysis
- [ ] Filters refetch from API
- [ ] Payment ID link works

### Configuration Management
- [ ] Full propose → approve → deploy cycle works end-to-end in browser
- [ ] Deploy confirmation dialog appears
- [ ] After deploy: thresholds table shows new value

### Role gating
- [ ] Log in as each of the 4 users and verify correct pages are accessible
- [ ] Priya cannot see /admin or /governance pages (if route protection implemented)
- [ ] API-level: POST /api/payments/{id}/return with Priya's token → 403

---

## Acceptance criteria
- [ ] All 50+ checklist items pass with no console errors
- [ ] Auth token expiry is handled (redirect to login, not a broken page)
""",
    },

    {
        "title": "[Design] UI polish — responsive layout, empty states, accessibility",
        "label": "Design", "phase": "Phase 4", "estimate": 3, "priority": 3,
        "assignee_hint": "Designer + Engineer B",
        "description": """\
## Context
Final polish pass before the PoC is presented to stakeholders. Focus on the cases that are hard to design upfront: empty states, error conditions, edge cases.

---

## Responsive layout
- All pages must be usable at 1280px (primary) and 1440px
- Tables must not overflow on 1280px — horizontal scroll is acceptable for wide tables
- No layout breaking at ≤1024px (some elements can restack vertically)

## Empty states to design and implement
| Page | Empty condition |
|------|----------------|
| Queue Dashboard | No HELD payments |
| Queue Dashboard | All payments filtered out |
| Investigation Queue | No escalated cases |
| Payment Detail — Annotations | No annotations yet |
| Payment Detail — Documents | No documents uploaded |
| Override Analysis | No overrides match filters |
| Exception Dashboard — each section | No SLA breaches / no anomalies / no pending configs |

Each empty state should: have an icon, a short message, and (where relevant) a call-to-action.

## Error toasts
Standardise the toast component across all pages:
- Network error: "Connection failed. Check your network and try again."
- 403: "You don't have permission for this action."
- 500: "Something went wrong on our end. Try again in a moment."
- Success: green toast for approve/reject/override/deploy

## Accessibility audit (engineer implements, designer reviews)
- All interactive elements reachable by keyboard (Tab, Enter, Space)
- All form inputs have associated `<label>` or `aria-label`
- Colour contrast ≥ 4.5:1 for all text
- Status badges have `aria-label` (not just colour)
- Modals trap focus correctly

---

## Acceptance criteria
- [ ] All empty states implemented (not just blank space)
- [ ] Error toasts use consistent component across all pages
- [ ] Keyboard navigation works on: table rows, filters, modals, action buttons
- [ ] No colour-only status indicators (always paired with text or icon)
""",
    },
]


LABEL_COLORS = {
    "Backend":  "#0ea5e9",
    "Frontend": "#8b5cf6",
    "AI":       "#f59e0b",
    "Database": "#10b981",
    "Design":   "#ec4899",
    "QA":       "#ef4444",
}

PHASE_COLORS = {
    "Phase 0": "#6b7280",
    "Phase 1": "#3b82f6",
    "Phase 2": "#8b5cf6",
    "Phase 3": "#f59e0b",
    "Phase 4": "#ef4444",
}


async def gql(client: httpx.AsyncClient, query: str, variables: dict = None) -> dict:
    resp = await client.post(API_URL, json={"query": query, "variables": variables or {}})
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise RuntimeError(f"GraphQL error: {data['errors']}")
    return data["data"]


async def get_or_create_label(client: httpx.AsyncClient, team_id: str, name: str, color: str) -> str:
    result = await gql(client, f"""
        query {{
          issueLabels(filter: {{ team: {{ id: {{ eq: "{team_id}" }} }} }}) {{
            nodes {{ id name }}
          }}
        }}
    """)
    for label in result["issueLabels"]["nodes"]:
        if label["name"] == name:
            return label["id"]
    result = await gql(client, """
        mutation LabelCreate($name: String!, $color: String!, $teamId: String!) {
          issueLabelCreate(input: { teamId: $teamId, name: $name, color: $color }) {
            issueLabel { id }
          }
        }
    """, {"teamId": team_id, "name": name, "color": color})
    return result["issueLabelCreate"]["issueLabel"]["id"]


async def get_or_create_project(client: httpx.AsyncClient, team_id: str, name: str) -> str:
    result = await gql(client, f"""
        query {{
          projects(filter: {{ accessibleTeams: {{ id: {{ eq: "{team_id}" }} }} }}) {{
            nodes {{ id name }}
          }}
        }}
    """)
    for p in result["projects"]["nodes"]:
        if p["name"] == name:
            print(f"  Using existing project: {name}")
            return p["id"]
    result = await gql(client, """
        mutation ProjectCreate($name: String!, $teamId: String!) {
          projectCreate(input: { teamIds: [$teamId], name: $name }) {
            project { id }
          }
        }
    """, {"teamId": team_id, "name": name})
    print(f"  Created project: {name}")
    return result["projectCreate"]["project"]["id"]


async def main() -> None:
    if not API_KEY or not TEAM_ID:
        print("Error: set LINEAR_API_KEY and LINEAR_TEAM_ID environment variables.")
        print()
        print("  LINEAR_API_KEY=lin_api_xxx LINEAR_TEAM_ID=your-team-id python scripts/create_linear_issues.py")
        sys.exit(1)

    headers = {"Authorization": API_KEY, "Content-Type": "application/json"}
    all_label_colors = {**LABEL_COLORS, **PHASE_COLORS}

    async with httpx.AsyncClient(headers=headers, timeout=30) as client:
        print(f"Setting up project: {PROJECT_NAME}")
        project_id = await get_or_create_project(client, TEAM_ID, PROJECT_NAME)

        print("Syncing labels...")
        label_ids: dict[str, str] = {}
        for name, color in all_label_colors.items():
            label_ids[name] = await get_or_create_label(client, TEAM_ID, name, color)

        print(f"\nCreating {len(ISSUES)} issues...")
        created = 0
        for issue in ISSUES:
            ids = []
            if issue["label"] in label_ids:
                ids.append(label_ids[issue["label"]])
            if issue["phase"] in label_ids:
                ids.append(label_ids[issue["phase"]])

            result = await gql(client, """
                mutation IssueCreate($input: IssueCreateInput!) {
                  issueCreate(input: $input) {
                    issue { id identifier title }
                  }
                }
            """, {"input": {
                "teamId": TEAM_ID,
                "projectId": project_id,
                "title": issue["title"],
                "description": issue.get("description", ""),
                "priority": issue.get("priority", 3),
                "estimate": issue.get("estimate"),
                "labelIds": ids,
            }})
            identifier = result["issueCreate"]["issue"]["identifier"]
            print(f"  {identifier}  {issue['title'][:72]}")
            created += 1

    print(f"\nDone — {created} issues created in '{PROJECT_NAME}'.")
    print(f"Assignee hints (assign manually in Linear or add LINEAR_TEAM_MEMBER_IDs to script):")
    hints = {}
    for issue in ISSUES:
        h = issue.get("assignee_hint", "")
        hints.setdefault(h, 0)
        hints[h] += 1
    for role, count in sorted(hints.items()):
        print(f"  {role}: {count} issues")


if __name__ == "__main__":
    asyncio.run(main())
