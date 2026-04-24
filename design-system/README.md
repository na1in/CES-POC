# PayWise Design System

Developer reference for the PayWise AI Payment Resolution app.

---

## Quick start

```jsx
// 1. Import the CSS tokens once at your app root (main.jsx / _app.tsx)
import '@/design-system/tokens.css'

// 2. Import components anywhere
import { Button, RecBadge, StatCard, SignalBar } from '@/design-system'
```

---

## Tokens

### Colors (`tokens.js`)

| Token | Value | Usage |
|---|---|---|
| `colors.primary` | `#7C4DFF` | Primary actions, active tabs, focus rings |
| `colors.secondary` | `#00E5FF` | Gradient end, cyan accent |
| `colors.apply` | `#10B981` | APPLY status, success, accept buttons |
| `colors.hold` | `#F59E0B` | HOLD status, warnings |
| `colors.escalate` | `#EF4444` | ESCALATE status, errors |
| `colors.textPrimary` | `#1E293B` | Headings, primary content |
| `colors.textSecondary` | `#64748B` | Labels, metadata |
| `colors.textMuted` | `#94A3B8` | Timestamps, tertiary |
| `colors.border` | `#E2E8F0` | All borders |
| `colors.bgPrimary` | `#F8F9FA` | App canvas |
| `colors.bgSurface` | `#FFFFFF` | Cards, panels, nav |
| `colors.bgSurfaceElevated` | `#F1F3F5` | Inputs, hover, tags |

### Typography

| Token | Value |
|---|---|
| `typography.fontSans` | `'Inter', sans-serif` |
| `typography.fontMono` | `'JetBrains Mono', monospace` |
| `typography.fontDisplay` | `'DM Sans', sans-serif` (logo only) |
| `typography.textXs` | `11px` |
| `typography.textSm` | `12px` |
| `typography.textBase` | `14px` |
| `typography.textMd` | `16px` |
| `typography.textLg` | `20px` |
| `typography.textXl` | `24px` |

### Spacing (4px base unit)

`spacing[1]` = 4px, `[2]` = 8px, `[4]` = 16px, `[6]` = 24px, `[8]` = 32px

### Border Radius

`radius.sm` = 4px · `radius.md` = 8px · `radius.lg` = 12px · `radius.full` = 9999px

---

## Components

### `<Button>`

```jsx
<Button variant="apply">Accept APPLY</Button>
<Button variant="ghost" size="sm">Cancel</Button>
<Button variant="outline-escalate">Escalate</Button>
```

**Variants:** `primary` · `apply` · `hold` · `escalate` · `ghost` · `outline-escalate`  
**Sizes:** `md` (default) · `sm`

---

### Badges

```jsx
<RecBadge rec="APPLY" />          // recommendation badge
<StatusBadge status="resolved" /> // case status badge
<FlagBadge flag="Amount Variance" />
<RiskBadge level="high" />
<CountBadge count={4} active />   // tab count pill
<ConfidenceText value={98} rec="APPLY" />
```

---

### `<SignalBar>` / `<RecommendationBox>`

```jsx
// AI signal bar — colour auto-derived from value
<SignalBar name="Name Similarity" value={100} label="Exact match" />
<SignalBar name="Duplicate Check" value={100} label="DUPLICATE DETECTED" forceColor="escalate" />

// Coloured AI recommendation banner
<RecommendationBox rec="HOLD" confidence={78} reasoning="Payment is 8% higher…" />
```

---

### Cards

```jsx
<Card>…</Card>   // white card, border + shadow-sm

// Dashboard KPI tile
<StatCard label="Cases Closed Today" value={67} icon="⏱" iconColor="#3B82F6" iconBg="rgba(59,130,246,.1)" />

// Row of stat cards
<StatCardRow stats={[{ label, value, icon, iconColor, iconBg, sub }]} />

// Collapsible section card (used in case detail)
<SectionCard title="Audit Trail" collapsible>
  <AuditTimeline entries={…} />
</SectionCard>
```

---

### `<AuditTimeline>`

```jsx
<AuditTimeline entries={[
  { timestamp: '2026-03-28 09:15:23', user: 'AI Agent', action: 'Analysis Complete', details: 'Recommendation: APPLY (98%)' }
]} />
```

---

### `<Logo>` / `<Avatar>`

```jsx
<Logo />              // mark + wordmark
<Logo markOnly />     // icon only
<Avatar initials="PV" size={32} />
```

---

### `<Toast>` / `useToast`

```jsx
const { toast, showToast } = useToast()

showToast({ title: 'Case accepted', desc: 'PMT-1001 marked as resolved.', type: 'success' })

return <>{toast && <Toast {...toast} onClose={hideToast} />}</>
```

**Types:** `success` · `warning` · `error` · `info`

---

## Content & Writing Rules

| Element | Format |
|---|---|
| Page titles | Title Case |
| Table column headers | UPPERCASE |
| Status labels | UPPERCASE (`APPLY`, `HOLD`, `ESCALATE`) |
| Button labels | Title Case (`Accept APPLY`, `Override Recommendation`) |
| Body / descriptions | Sentence case |
| IDs, dates, amounts | Monospace (`PMT-1001`, `$2,500.00`, `2026-03-28`) |

- **No emoji in UI** — only role icons in the profile switcher
- **Audit trail** uses third person: `"AI Agent: Analysis Complete"`
- Keyboard shortcuts documented inline: `⌘K`, `ESC`, `?`

---

## Iconography

**Library:** [Lucide React](https://lucide.dev/) — stroke icons, 1.5px weight  
**Sizes:** `size={16}` inline · `size={18}` buttons · `size={20}` nav

```bash
npm install lucide-react
```

Common icons: `Search`, `Bell`, `Settings`, `CheckCircle2`, `Clock`, `AlertTriangle`, `X`, `ChevronDown`, `Filter`

---

## File structure

```
src/design-system/
├── tokens.css          ← CSS custom properties (import once at root)
├── tokens.js           ← JS token objects
├── index.js            ← barrel export for everything
├── README.md           ← this file
└── components/
    ├── index.js
    ├── Button.jsx
    ├── Badge.jsx
    ├── SignalBar.jsx
    ├── Card.jsx
    ├── Logo.jsx
    ├── AuditTimeline.jsx
    └── Toast.jsx
```
