# Stage 5: Human Approval Queue (Frontend)

**Purpose:** Role-based Next.js frontend serving four personas — Analyst (Priya), Investigator (Damien), Director (Lorraine), and Admin (Marcus). Each role sees a tailored home screen with appropriate data scope and decision authority.

---

## Overview

The frontend is a Next.js application with 10 pages split across 4 roles. Role is set at auth time and controls which pages and actions are accessible.

| Role | Persona | Home Page | Decision Authority |
|------|---------|-----------|--------------------|
| Analyst | Priya | Queue Dashboard `/` | Approve/reject/override HELD payments |
| Investigator | Damien | Investigation Queue `/investigations` | Final determination on escalated cases, outreach logging, returns |
| Director | Lorraine | Governance Dashboard `/governance` | Approve/reject config changes, flag anomalies |
| Admin | Marcus | Admin Dashboard `/admin` | Propose config changes, monitor performance |

---

## Analyst Pages (Priya)

### Page 1: Queue Dashboard (`/`)

Priya's daily working view — open cases sorted by AI confidence score (lowest first = most uncertain = needs attention most).

```
┌──────────────────────────────────────────────────────────────────┐
│  QUEUE DASHBOARD                                                  │
│                                                                  │
│  Filters: [Scenario ▼] [Confidence ▼] [Payment Method ▼]       │
│                                                                  │
│  PMT │ Sender        │ Amount   │ Scenario │ Method │ Rec.  │ Conf │ Age │
│  ────┼───────────────┼──────────┼──────────┼────────┼───────┼──────┼─────│
│  002 │ Sarah Johnson │ $1,250   │ Sc.2     │ ACH    │ APPLY │ 85%  │ 2h  │
│  006 │ M. Al-Hassan  │ $3,100   │ Sc.1     │ Check  │ HOLD  │ 78%  │ 4h  │
│  009 │ Corp Payroll  │ $7,500   │ Sc.3     │ Wire   │ HOLD  │ 61%  │ 6h  │
│                                                                  │
│  ⚠  2 cases in PROCESSING_FAILED → [Reprocess All]              │
└──────────────────────────────────────────────────────────────────┘
```

Columns: scenario, sender name, amount, **payment method**, AI recommendation, confidence band, age in queue. Sortable by confidence score (default), has_risk_flags, payment_method.

---

### Page 3: Payment Detail (`/payments/[id]`)

The primary decision-making page. Every signal, the AI's reasoning, and all actions are on one screen.

```
┌──────────────────────────────────────────────────────────────────┐
│  PMT-002                                        Status: HELD     │
│                                                                  │
│  PAYMENT INFO                                                    │
│  Sender: Sarah Johnson    Amount: $1,250    Method: ACH          │
│  Reference 1: "auto insurance"    Reference 2: (empty)           │
│  Matched Customer: CUST-0042   Matched Policy: POL-20145         │
│                                                                  │
│  COMPUTED SIGNALS                                                │
│  Name Similarity:     100%  ██████████████████████ ✓            │
│    Jaro-Winkler: 100  Levenshtein: 100  Soundex: ✓  LLM: —     │
│  Policy Confidence:     0%  (no policy reference) ✗             │
│  Customer Confidence: 100%  ██████████████████████ ✓            │
│  Amount Variance:       0%  ██████████████████████ ✓            │
│  Timing Quality:    EXCELLENT                      ✓            │
│  Risk Flags:            None                       ✓            │
│  Duplicate:             No                         ✓            │
│  Supporting Signals: 2 of 3 (amount ✓  history ✓)               │
│                                                                  │
│  AI REASONING (Scenario 2 — Customer Match, No Policy)           │
│  Confidence: 85%                                                 │
│  1. Customer Sarah Johnson matched with 100% confidence          │
│  2. No policy reference provided — routed to Scenario 2          │
│  3. Payment amount $1,250 exactly matches Auto Insurance premium  │
│  4. Recommend: APPLY to POL-20145                                │
│                                                                  │
│  AUDIT TIMELINE                                                  │
│  09:01:23  RECEIVED           system                             │
│  09:01:24  SIGNALS_COMPUTED   system                             │
│  09:01:25  RECOMMENDATION_MADE  system (APPLY, 85%, Sc.2)        │
│                                                                  │
│  ANNOTATIONS                                                     │
│  [Add case note...]                                              │
│                                                                  │
│  DOCUMENTS                                                       │
│  [Upload supporting document]  (no documents yet)               │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────────────┐   │
│  │ APPROVE  │  │  REJECT  │  │  OVERRIDE (mandatory reason) │   │
│  └──────────┘  └──────────┘  └──────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

Key sections:
- **Payment Info** — amount (cents displayed as dollars), payment method, matched IDs
- **Computed Signals** — all 19 signals with visual bars; matching signals show full algorithm breakdown (Jaro-Winkler, Levenshtein, Soundex, LLM score) for transparency
- **AI Reasoning** — ordered reasoning list, scenario, confidence score
- **Audit Timeline** — append-only record of every action
- **Annotations** — add/view case notes (Priya) and investigation notes (Damien)
- **Documents** — upload/list supporting evidence, correspondence, bank statements
- **Actions** — Approve (HELD → APPLIED, ledger updated), Reject (HELD → ESCALATED), Override (change AI recommendation with mandatory reason)

---

## Investigator Pages (Damien)

### Page 2: Investigation Queue (`/investigations`)

Damien's home view — escalated cases only, pre-sorted by risk level, showing time since escalation for SLA awareness.

```
┌──────────────────────────────────────────────────────────────────┐
│  INVESTIGATION QUEUE                                              │
│                                                                  │
│  PMT │ Sender         │ Amount   │ Risk     │ Method  │ Escalated │
│  ────┼────────────────┼──────────┼──────────┼─────────┼───────────│
│  011 │ Unknown Corp   │ $15,000  │ ⚠ HIGH   │ Wire    │ 48h ago   │
│  003 │ J. Al-Farsi    │ $5,200   │ ⚠ HIGH   │ Check   │ 12h ago   │
│  008 │ Family Trust   │ $2,900   │ MEDIUM   │ ACH     │ 3h ago    │
│                                                                  │
│  ⚠  1 case SLA breached                                          │
└──────────────────────────────────────────────────────────────────┘
```

Damien also uses the shared Payment Detail page (`/payments/[id]`) where he has access to additional actions: **Return to Sender**, **Log Contact** (records outreach method + outcome), and can add investigation notes. He can also escalate a PENDING_SENDER_RESPONSE case back to ESCALATED if the SLA is breached.

---

## Director Pages (Lorraine)

### Page 4: Governance Dashboard (`/governance`)

Lorraine's high-level oversight view. Shows decision attribution and key governance metrics.

```
┌──────────────────────────────────────────────────────────────────┐
│  GOVERNANCE DASHBOARD          Date Range: [Last 30 days ▼]      │
│                                                                  │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐             │
│  │ AI Auto-Apply│ │ Human Review │ │   On Hold    │             │
│  │      45      │ │     22       │ │      8       │             │
│  └──────────────┘ └──────────────┘ └──────────────┘             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐             │
│  │ Escalated AI │ │ Esc. Human   │ │  Overrides   │             │
│  │      12      │ │      5       │ │      3       │             │
│  └──────────────┘ └──────────────┘ └──────────────┘             │
│                                                                  │
│  Override Rate: 3.5%  SLA Adherence: 94%                        │
│                                                                  │
│  By Payment Method:                                              │
│  ACH    ████████████████ 38  (AI: 30  Human: 7  Override: 1)    │
│  Check  ████████         18  (AI: 10  Human: 6  Override: 2)    │
│  Wire   █████            12  (AI: 5   Human: 4  Override: 0)    │
│                                                                  │
│  Confidence Score Histogram:                                     │
│  90-100% ██████████████  55                                      │
│  80-90%  ████████        30                                      │
│  70-80%  ████             15                                     │
│  < 70%   ██               8                                      │
└──────────────────────────────────────────────────────────────────┘
```

Metric cards: Auto-Applied by AI, Applied after Human Review, Held Pending Review, Escalated by AI, Escalated by Human, Human Overrides. Also shows override rate trend, SLA adherence, payment method breakdown chart, and confidence histogram.

---

### Page 5: Compliance Export (`/governance/export`)

Date range selector + export scope + download button. Generates audit-ready structured report.

---

### Page 6: Exception Dashboard (`/governance/exceptions`)

SLA-breached cases, metric anomaly flags, and config change requests pending Lorraine's approval. Lorraine approves or rejects proposed threshold changes here.

---

## Admin Pages (Marcus)

### Page 7: Admin Dashboard (`/admin`)

Per-scenario analytics: case volume trend, decision distribution, override rate by confidence band, confidence histogram.

---

### Page 8: Override Analysis (`/admin/overrides`)

Filterable view of all human override events. Filters: scenario, confidence band, date range, override reason category. Used to spot patterns that suggest threshold tuning is needed.

---

### Page 9: Configuration Management (`/admin/config`)

Marcus manages threshold changes through a formal change-request workflow:
1. View current thresholds
2. Submit a change request with rationale and projected impact (backed by back-test simulation)
3. Track status: PENDING → APPROVED/REJECTED (Lorraine) → DEPLOYED (Marcus)
4. View full version history + staging simulation
5. Emergency rollback (requires Lorraine approval)

```
┌──────────────────────────────────────────────────────┐
│  CONFIGURATION MANAGEMENT                             │
│                                                      │
│  Parameter            │ Current │ Pending Change     │
│  ─────────────────────┼─────────┼────────────────── │
│  name_match_auto_apply│  90%    │ → 88% (pending)   │
│  name_match_hold      │  75%    │ —                 │
│  name_gray_zone_lower │  70%    │ —                 │
│  name_gray_zone_upper │  92%    │ —                 │
│  amount_tolerance_auto│   2%    │ —                 │
│  duplicate_window_hrs │  72h    │ —                 │
│                                                      │
│  [+ Propose New Change]    [View Version History]    │
└──────────────────────────────────────────────────────┘
```

Note: Marcus cannot directly edit thresholds. Every production change requires an approved `ConfigurationChangeRequest` on record (proto: `config_change.proto`).

---

## Shared Pages

### Page 10: Settings (`/settings`)

Threshold viewer — read-only for non-admin roles. Admin (Marcus) sees a link to the change request form instead of direct edit.

### Page 3: Payment Detail (`/payments/[id]`)

Shared across Analyst and Investigator. Role controls which action buttons are shown:

| Button | Priya (Analyst) | Damien (Investigator) |
|--------|-----------------|-----------------------|
| Approve | ✓ (on HELD) | — |
| Reject | ✓ (on HELD) | — |
| Override | ✓ | ✓ |
| Return to Sender | — | ✓ (on ESCALATED) |
| Log Contact | — | ✓ |
| Add Case Note | ✓ | ✓ |
| Upload Document | ✓ | ✓ |

---

## Frontend File Structure

```
frontend/src/
├── app/
│   ├── page.tsx                          # Queue Dashboard (Priya home)
│   ├── investigations/
│   │   └── page.tsx                      # Investigation Queue (Damien home)
│   ├── payments/
│   │   └── [id]/page.tsx                 # Payment Detail (shared)
│   ├── governance/
│   │   ├── page.tsx                      # Governance Dashboard (Lorraine home)
│   │   ├── export/page.tsx               # Compliance Export
│   │   └── exceptions/page.tsx           # Exception Dashboard + config approvals
│   ├── admin/
│   │   ├── page.tsx                      # Admin Dashboard (Marcus home)
│   │   ├── overrides/page.tsx            # Override Analysis
│   │   └── config/page.tsx              # Configuration Management
│   └── settings/
│       └── page.tsx                      # Threshold viewer (read-only / change-request)
├── components/
│   ├── PaymentCard.tsx                   # Payment summary card
│   ├── SignalsPanel.tsx                  # Signal bars with algorithm breakdown
│   ├── ReasoningPanel.tsx                # AI reasoning display
│   ├── AuditTimeline.tsx                 # Audit trail timeline
│   ├── AnnotationPanel.tsx               # Case notes + investigation notes
│   ├── DocumentPanel.tsx                 # Document upload + list
│   ├── ApprovalActions.tsx               # Approve/Reject/Override/Return buttons
│   ├── GovernanceMetrics.tsx             # Metric cards + charts (Lorraine)
│   ├── ScenarioBreakdown.tsx             # Per-scenario analytics (Marcus)
│   ├── OverrideTable.tsx                 # Override analysis table
│   └── ConfigChangeForm.tsx             # Change request form + version history
└── lib/
    └── api.ts                            # API client for backend calls
```

---

*End of Document*
