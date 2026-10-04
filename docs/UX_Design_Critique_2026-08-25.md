# Design Critique: PayWise / CES Payment Operations App

**Reviewed**: live running build (Next.js frontend + FastAPI backend), all 4 role dashboards + case detail + admin config + exception dashboard, current LinkedIn-Blue palette
**Stage**: functional PoC, pre-launch polish

---

### Overall Impression

The bones are genuinely good — a consistent white-card-on-gray-canvas system, a disciplined green/amber/red status vocabulary used the same way everywhere, and monospace treatment for IDs/amounts that suits a financial audit tool. The biggest opportunity isn't visual, it's that internal engineering vocabulary (`scenario_1`...`scenario_5`, raw `0h ago` timestamps) is leaking into screens meant for non-engineers to make judgment calls under time pressure.

### Usability

| Finding | Severity | Recommendation |
|---|---|---|
| Admin dashboard tabs and the override-reason dropdown show raw `"Scenario 1"`...`"Scenario 5"` instead of what they mean | 🔴 Critical | Reuse the label map already defined in `app/page.tsx` (`"Policy Match"`, `"Cust. Match"`, `"High Variance"`, `"No Match"`, `"Duplicate"`) across `admin/page.tsx`, `admin/overrides/page.tsx`, and `payments/[id]/page.tsx` (currently does a raw `scenario_route.replace("_"," ")`, which is why case detail shows the literal string "scenario 4") |
| Investigator queue's "ESCALATED BY" column is blank ("—") for every row | 🟡 Moderate | Either populate it from the audit log (the case-detail audit trail already captures the escalating actor) or remove the column — an empty column that looks like a data bug undermines trust in an audit tool |
| Case detail gives an analyst only two actions — "Escalate" or "Override & Apply" — even when "Matched Policy: No matched policy." There's no path to manually search/attach a policy before deciding | 🟡 Moderate | Add a "Search policies" or "Attach policy" affordance in the Matched Policy card for the no-match case, so Override & Apply isn't the only alternative to escalating |
| Relative timestamps are inconsistent between tables: analyst queue shows `"16m ago"`, investigator queue shows `"0h ago"` for the same kind of just-created case | 🟢 Minor | Standardize on one relative-time formatter (minutes under an hour, hours/days after) across both tables |

### Visual Hierarchy

- **What draws the eye first**: On every dashboard, the top stat row — correct, that's the information a role needs before triaging the table below.
- **Reading flow**: Left-to-right, top-to-bottom works fine on all four dashboards; the case detail page's AI Recommendation banner at the top is the right anchor for that page.
- **Emphasis**: This is the one place the new LinkedIn Blue palette is working against you — nav links, primary buttons, avatars, badges, the majority pie slice, and the "neutral" bar-chart fills are all the same saturated blue. Nothing signals "this is the button to press" versus "this is just a data color." Recommend reserving full-saturation blue for actions/navigation/links, and shifting decorative chart fills (the plain volume/confidence bar charts, the pie chart's larger slice) to a muted slate so actionable blue stands out.

### Consistency

| Element | Issue | Recommendation |
|---|---|---|
| Scenario naming | Three different vocabularies across the app (see Usability table) | Single source of truth — export the label map from one shared module instead of redefining it per page |
| Empty states (Config Management's Change Requests tabs, all 3 Exception Dashboard cards) | Each renders a full-height card with just a "No X" sentence — on a page with nothing to review, that's 3 tall empty boxes stacked with a lot of dead gray space | Collapse empty sections to a compact single line, or combine into one "All clear" summary card when everything is empty |
| Status colors | Used identically everywhere (badge + icon + label, never color alone) | This one's already right — no change needed, called out below as a strength |

### Accessibility

*(Full contrast-ratio and keyboard/screen-reader pass is what `accessibility-review` is for — flagging what's visible from screenshots/code here.)*

- **Color contrast**: `#0A66C2` on white reads as plausible AA for normal text but I haven't computed exact ratios — worth confirming precisely, especially for the `--text-xs` (11px) labels used all over (stat labels, table headers, filter chips), since small text needs a *higher* contrast ratio than body text to pass AA.
- **Touch targets**: Buttons use ~7-8px vertical padding (`--space-2`/`--space-3`), which likely lands under the 44×44px recommended target on the smaller `.btn-sm` variants used for row-level actions — worth measuring the rendered size.
- **Text readability**: Most body text is 14px (`--text-base`) which is fine; the 11px label text mentioned above is the main risk area.
- **Color-alone signaling**: Not an issue — every status badge pairs color with an icon and an uppercase text label already.

### What Works Well

- The apply/hold/escalate color vocabulary (green/amber/red) is applied identically across all 4 roles' screens — this consistency is what makes the app scannable at a glance.
- Monospace treatment for case IDs, dates, and dollar amounts reduces ambiguity, which matters a lot in a financial audit context.
- The "Audit Active" status bar with user + last-sync on every screen reinforces the compliance framing appropriately for the domain.
- The analyst dashboard's filter chips already solved the naming problem the rest of the app hasn't caught up to — good instinct, just needs to propagate.

### Priority Recommendations

1. **Kill the raw `scenario_N` strings everywhere** — this is the single highest-leverage fix: three files, one shared label map, and every screen a non-engineer looks at stops requiring a mental lookup table.
2. **Fix the blue monochrome hierarchy problem** — mute the decorative/neutral chart fills so full-saturation blue means "you can act on this," restoring the at-a-glance scannability the color system otherwise has going for it.
3. **Compact the empty states** on Config Management and Exception Dashboard, and populate (or remove) the blank "Escalated By" column — both read as bugs rather than intentional design at first glance, which erodes trust in a tool whose whole job is to be trustworthy.
