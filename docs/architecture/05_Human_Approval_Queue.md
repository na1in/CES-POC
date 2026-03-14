# Stage 5: Human Approval Queue (Audit & Explainability)

**Purpose:** Frontend dashboard for analysts to review HOLD/ESCALATE payments, approve or reject with full audit visibility.

---

## Overview

This is the Next.js frontend. It serves two audiences:
- **Analysts** — review held payments, approve/reject with context
- **Team leads** — monitor throughput, spot bottlenecks, adjust thresholds

---

## Pages

### Page 1: Dashboard (`/`)

Quick-glance overview for the team lead.

```
┌──────────────────────────────────────────────────────┐
│  DASHBOARD                                            │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────┐ │
│  │ RECEIVED │  │  APPLIED │  │   HELD   │  │ESCAL.│ │
│  │    12    │  │    45    │  │     8    │  │   3  │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────┘ │
│                                                      │
│  By Scenario:                                        │
│  Sc.1 Strong Match ████████████████  32              │
│  Sc.2 Customer Match ████████        16              │
│  Sc.3 High Variance  ██████          12              │
│  Sc.4 No Match        ███             5              │
│  Sc.5 Duplicate       █               3              │
│                                                      │
│  ⚠ 2 payments in PROCESSING_FAILED                  │
└──────────────────────────────────────────────────────┘
```

Shows: payment counts by status, breakdown by scenario, and any failed payments needing attention.

---

### Page 2: Payment List (`/payments`)

Filterable, sortable table of all payments.

```
┌──────────────────────────────────────────────────────────────────┐
│  PAYMENTS                                                        │
│                                                                  │
│  Filters: [Status ▼] [Scenario ▼] [Date Range] [Search...]     │
│                                                                  │
│  ID       │ Sender        │ Amount   │ Scenario │ Status  │ Date │
│  ─────────┼───────────────┼──────────┼──────────┼─────────┼──────│
│  PMT-001  │ John A Smith  │ $5,000   │ Sc.1     │ APPLIED │ 3/12 │
│  PMT-002  │ Sarah Johnson │ $1,250   │ Sc.2     │ HELD    │ 3/12 │
│  PMT-003  │ Unknown Corp  │ $15,000  │ Sc.4     │ ESCALATED│ 3/11│
│  PMT-004  │ Emily Watson  │ $750     │ Sc.5     │ HELD    │ 3/11 │
│                                                                  │
│  Click any row to see full details →                             │
└──────────────────────────────────────────────────────────────────┘
```

Filter by status (HELD, APPLIED, ESCALATED, PROCESSING_FAILED), scenario, date range, or search by sender name.

---

### Page 3: Payment Detail (`/payments/[id]`)

The most important page. Everything the analyst needs to make a decision:

```
┌──────────────────────────────────────────────────────────────────┐
│  PMT-002                                        Status: HELD     │
│                                                                  │
│  PAYMENT INFO                                                    │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ Sender: Sarah Johnson    Amount: $1,250    Method: ACH    │  │
│  │ Reference 1: "auto insurance"                              │  │
│  │ Reference 2: (empty)                                       │  │
│  │ Matched Customer: CUST-0042 Sarah Johnson                  │  │
│  │ Matched Policy: POL-20145 (Auto Insurance, $1,250/mo)     │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  COMPUTED SIGNALS                                                │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ Name Similarity:       100%  ████████████████████  ✓      │  │
│  │ Policy Confidence:       0%  (no policy reference)  ✗     │  │
│  │ Customer Confidence:   100%  ████████████████████  ✓      │  │
│  │ Amount Variance:         0%  ████████████████████  ✓      │  │
│  │ Timing Quality:    EXCELLENT                       ✓      │  │
│  │ Risk Flags:             None                       ✓      │  │
│  │ Duplicate:               No                        ✓      │  │
│  │ Supporting Signals:   2 of 3 (amount ✓ history ✓)         │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  AI REASONING (Scenario 2 — Customer Match, No Policy)           │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ Confidence: 85%                                            │  │
│  │                                                            │  │
│  │ 1. Customer Sarah Johnson matched with 100% confidence     │  │
│  │ 2. No policy reference provided — routed to Scenario 2     │  │
│  │ 3. Customer has 2 active policies:                         │  │
│  │    - POL-20145 Auto Insurance ($1,250/mo)                  │  │
│  │    - POL-20146 Home Insurance ($2,100/mo)                  │  │
│  │ 4. Payment amount $1,250 exactly matches Auto Insurance    │  │
│  │ 5. Recommend: APPLY to POL-20145                           │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  AUDIT TRAIL                                                     │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ 3/12 09:01:23  RECEIVED           actor: system           │  │
│  │ 3/12 09:01:24  SIGNALS_COMPUTED   actor: system           │  │
│  │ 3/12 09:01:25  RECOMMENDATION_MADE actor: system          │  │
│  │                Recommendation: APPLY (needs approval)      │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐                               │
│  │  ✓ APPROVE  │  │  ✗ REJECT   │                               │
│  └─────────────┘  └─────────────┘                               │
│  Notes: [________________________________]                       │
└──────────────────────────────────────────────────────────────────┘
```

Sections:
- **Payment Info** — who sent it, how much, what references, matched customer/policy
- **Computed Signals** — all 15 signals with visual bars and pass/fail indicators
- **AI Reasoning** — ordered explanation list, scenario, confidence score
- **Audit Trail** — timeline of every action on this payment
- **Action Buttons** — Approve (→ APPLIED, ledger updated) or Reject (→ ESCALATED) with optional notes

---

### Page 4: Settings (`/settings`)

Admin page for editing configuration thresholds.

```
┌──────────────────────────────────────────────────────┐
│  CONFIGURATION THRESHOLDS                             │
│                                                      │
│  Name Match Auto-Apply:    [90 ] %                   │
│  Name Match Hold:          [75 ] %                   │
│  Name Gray Zone Lower:     [70 ] %                   │
│  Name Gray Zone Upper:     [92 ] %                   │
│  Amount Tolerance (Auto):  [ 2 ] %                   │
│  Amount Tolerance (Hold):  [15 ] %                   │
│  Duplicate Window:         [72 ] hours               │
│  Confidence Auto-Action:   [80 ] %                   │
│                                                      │
│  [Save Changes]                                      │
│                                                      │
│  Changes take effect for new payments immediately.   │
│  Existing recommendations are not retroactively       │
│  affected (they used the thresholds at decision time).│
└──────────────────────────────────────────────────────┘
```

Changes are effective immediately for new payments. Existing recommendations keep their original thresholds because signals are snapshotted.

---

## Frontend File Structure

```
frontend/src/
├── app/
│   ├── page.tsx                    # Dashboard
│   ├── payments/
│   │   ├── page.tsx                # Payment list with filters
│   │   └── [id]/page.tsx          # Payment detail + approve/reject
│   ├── queue/
│   │   └── page.tsx                # Approval queue (filtered view of HELD payments)
│   └── settings/
│       └── page.tsx                # Threshold configuration
├── components/
│   ├── PaymentCard.tsx             # Payment summary card
│   ├── SignalsPanel.tsx            # Signal bars with visual indicators
│   ├── ReasoningPanel.tsx          # AI reasoning display
│   ├── AuditTimeline.tsx           # Audit trail timeline
│   ├── ApprovalActions.tsx         # Approve/Reject buttons + notes input
│   └── ThresholdEditor.tsx         # Threshold config form
└── lib/
    └── api.ts                      # API client for backend calls
```

---

*End of Document*
