# CES Payment Exception Pipeline — Interactive Architecture

Companion to `pipeline-diagram.html`. Open the HTML in any browser:

```bash
open docs/architecture/pipeline-diagram.html
```

Shortcuts: `Space` play/pause · `←`/`→` step · `1`–`5` flow · `O` mode · `T` theme · `F` fullscreen · `R` reset layout. Nodes are draggable and clickable (clicking a node jumps to the first step it appears in).

---

## The problem this pipeline solves

Unidentified and miscellaneous payments used to reach an analyst as a **flat, arrival-ordered list with no supporting context**. For each case the analyst opened customer records, policy data and payment history in separate screens and reconstructed the evidence by hand — which meant triage quality depended on individual experience, two analysts could reach different conclusions on the same payment, and the reasoning behind a decision was never captured.

This pipeline moves that work upstream. Every payment is scored on **19 signals**, classified into one of **5 exception scenarios**, and delivered to a **queue ranked by confidence** where each case opens as a pre-built dossier. The analyst's job shifts from *assembling* evidence to *judging* it.

The governing constraint: **a deterministic rule engine owns every decision, and the LLM only explains it.** Nothing auto-applies money.

---

## Components

| Node | Role | What it is |
|---|---|---|
| **Payment Sender** | entry point | Inbound ACH / check / wire the ledger could not auto-apply |
| **Ingest API** | deterministic | FastAPI `POST /api/payments/ingest` — validates, persists as `RECEIVED` |
| **Reference Parser** | LLM | Gemini 2.5 Flash — extracts policy number, intent, period count from free text |
| **Reference Data** | datastore | `customers`, `policies`, `payment_history` — what the analyst used to search manually |
| **Signal Engine** | signal engine | 19 signals across 5 categories, 3 dependency-ordered waves, parallel fan-out per wave |
| **Scenario Router** | deterministic | `if/else` routing across 5 scenarios. **No LLM involvement.** |
| **Rationale Writer** | LLM | Gemini 2.5 Flash — writes analyst-facing reasoning for an already-decided outcome |
| **Persist** | deterministic | Single transaction; 3 retries with 1s/3s backoff |
| **PostgreSQL** | datastore | 16 tables, 24 indexes, 18 enum types; immutable per-payment signal snapshot |
| **Analyst Queue** | human | Next.js, ranked by confidence descending — Priya |
| **Investigation Queue** | human | Escalations with SLA tracking — Damien |
| **Config Console** | control plane | 9 thresholds behind change-request → approve → deploy → rollback — Marcus, Lorraine |

---

## Modes

| Mode | Reference Parser | Rationale Writer |
|---|---|---|
| **Live LLM** | Gemini 2.5 Flash via OpenRouter, `max_tokens` 256, 10s timeout | Gemini 2.5 Flash, `max_tokens` 512, 10s timeout |
| **Mocked LLM** | `conftest.py` stub, deterministic | `fallback_reasoning`, deterministic |

Mocked is the default for the 393-test pytest suite; `--live-llm` switches to real provider calls. The mode toggle shows which nodes are stubbed — and makes the point that **both LLM touchpoints have a deterministic fallback, so no model outage can fail a request.**

---

## Flows

### 1 · Scenario 1 — Strong Policy Match (12 steps)
The common case. Policy number present, name matches at 96.2% via the three-algorithm ensemble — above the 92% gray-zone ceiling, so **no LLM call is made for matching at all**. Amount covers exactly two periods with 0% variance.

`sender → ingest → llm_parse → ingest → signals → refdata → signals → router → llm_reason → router → persist → pgdb → analyst`

Ends as `HELD` with a recommendation of `APPLY` — the strongest possible match still requires a human.

### 2 · Scenario 5 — Duplicate Payment (10 steps)
**Runs first on every payment**, in signal wave 1, before scenarios 1–4 are considered. Matches on three exact fields plus a $2 amount tolerance within a 72-hour window. Outstanding balance decides the outcome: `> 0` → HOLD (a second payment may be intentional), `= 0` → ESCALATE.

### 3 · Scenario 4 — No Match → Escalate (10 steps)
All matching fails — best candidate scores 61.3%, below the 70% gray-zone floor, so again **no LLM call**. Third-party payer is detected but cannot be bounded without a candidate policy, so the rule escalates. The case then crosses from analyst to investigator carrying its full history, and outreach starts an SLA timer that surfaces on the director's exception dashboard if breached.

### 4 · Analyst Review & Apply (6 steps)
**The flow that carries the value proposition.** Queue loads ranked by confidence with band, scenario and recommendation filters. One request returns the whole case — payment, 19 signal bars, the algorithm-level name breakdown, written reasoning, audit timeline, annotations, documents. The analyst applies, escalates or overrides; an override requires a written reason. Attribution is recorded at closure, which is what makes AI-vs-human analysis possible.

### 5 · Threshold Change (5 steps)
Override analysis shows a 31% override rate in the 75–80% name-match band. The admin proposes raising `name_match_hold` from 75 to 78; the change is simulated against recent cases (possible **because every decision has an immutable signal snapshot**), the director approves, the admin deploys, a version-history row is written. The next payment reads the new value at routing time — **no code change, no redeploy, no engineer.**

---

## Talking points

- **Where the LLM sits.** Step 8 of flow 1 is the moment to pause on: the recommendation is already decided in code before the model is called. Compare with steps 6 of flows 1 and 4 of flow 3, where the deterministic score falls outside the 70–92% gray zone and no model call happens at all.
- **Why nothing auto-applies.** Flow 1 ends at `HELD` despite a 97.4% confidence score.
- **What changed for the analyst.** Run flow 4 step 1 and contrast the ranked, evidence-backed queue against an arrival-ordered list with no context.
- **Who owns the decision boundaries.** Flow 5 shows the business retuning its own logic without engineering involvement.
- **What happens when the model fails.** Toggle to Mocked LLM and re-run flow 1 — the pipeline completes on deterministic fallbacks.
