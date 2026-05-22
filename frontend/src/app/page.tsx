"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { AlertTriangle, X, Search, Bell, Settings, CheckCircle2, Clock, TriangleAlert } from "lucide-react"
import { Button } from "@/components/ui/button"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { listPayments, type PaymentRow } from "@/lib/api"
import { useAuth } from "@/contexts/auth"
import type { ScenarioRoute } from "@/types/recommendation"
import type { PaymentMethod } from "@/types/payment"

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatUSD(cents: number): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(cents / 100)
}

function formatAge(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const minutes = Math.floor(diff / 60_000)
  const hours = Math.floor(diff / 3_600_000)
  const days = Math.floor(diff / 86_400_000)
  if (minutes < 60) return `${minutes}m ago`
  if (hours < 24) return `${hours}h ago`
  return `${days}d ago`
}

function formatToday(): string {
  return new Date().toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  })
}

type ConfidenceBand = "Low" | "Medium" | "High"

function getBand(score: number): ConfidenceBand {
  if (score < 40) return "Low"
  if (score <= 70) return "Medium"
  return "High"
}

function getFlags(payment: PaymentRow): string[] {
  const flags: string[] = []
  if (payment.has_risk_flags) flags.push("Risk Flag")
  if (payment.sla_breached) flags.push("SLA Breach")
  return flags
}

const SCENARIO_LABEL: Record<ScenarioRoute, string> = {
  scenario_1: "Policy Match",
  scenario_2: "Cust. Match",
  scenario_3: "High Variance",
  scenario_4: "No Match",
  scenario_5: "Duplicate",
}

const ALL_SCENARIOS: ScenarioRoute[] = [
  "scenario_1", "scenario_2", "scenario_3", "scenario_4", "scenario_5",
]
const ALL_METHODS: PaymentMethod[] = ["ACH", "Check", "Credit Card", "Wire"]

// ── Sub-components ────────────────────────────────────────────────────────────

function FilterChip({
  active,
  activeStyle,
  onClick,
  children,
}: {
  active: boolean
  activeStyle?: React.CSSProperties
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      style={
        active
          ? { border: "1px solid transparent", ...activeStyle }
          : {
              border: "1px solid var(--pw-border)",
              color: "var(--pw-text-secondary)",
              background: "transparent",
            }
      }
      className="rounded-md px-2 py-0.5 text-xs font-medium transition-colors hover:opacity-80"
    >
      {children}
    </button>
  )
}

function RecBadge({ rec }: { rec: "apply" | "hold" | "escalate" }) {
  const cls =
    rec === "apply"
      ? "pw-badge pw-badge-apply"
      : rec === "hold"
        ? "pw-badge pw-badge-hold"
        : "pw-badge pw-badge-escalate"
  return <span className={cls}>{rec.toUpperCase()}</span>
}

function ConfidencePct({ score }: { score: number }) {
  const band = getBand(score)
  const color =
    band === "High"
      ? "var(--pw-apply)"
      : band === "Medium"
        ? "var(--pw-hold)"
        : "var(--pw-escalate)"
  return (
    <span className="text-sm font-medium mono" style={{ color, fontFamily: "var(--pw-font-mono)" }}>
      {score}%
    </span>
  )
}

// ── Nav ───────────────────────────────────────────────────────────────────────

function Nav() {
  const { user, logout } = useAuth()
  const router = useRouter()
  const initials = user?.name.split(" ").map(w => w[0]).join("").slice(0, 2) ?? "?"

  function handleLogout() {
    logout()
    router.push("/login")
  }

  return (
    <nav
      className="flex items-center gap-3 px-5 border-b"
      style={{
        height: "var(--pw-nav-height)",
        background: "var(--pw-surface)",
        borderColor: "var(--pw-border)",
      }}
    >
      {/* Logo */}
      <div className="flex items-center gap-2 flex-1">
        <div
          className="w-7 h-7 rounded-lg flex items-center justify-center text-white text-xs font-bold shrink-0"
          style={{ background: "var(--pw-primary)" }}
        >
          P
        </div>
        <span
          className="font-semibold text-sm"
          style={{ fontFamily: "var(--pw-font-display)", color: "var(--pw-text-primary)" }}
        >
          PayWise
        </span>
      </div>

      {/* Search */}
      <div
        className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs"
        style={{ background: "var(--pw-surface-elevated)", color: "var(--pw-text-muted)" }}
      >
        <Search size={13} />
        <span>Search...</span>
        <kbd
          className="ml-1 rounded px-1 text-[10px]"
          style={{ background: "var(--pw-border)", color: "var(--pw-text-secondary)" }}
        >
          ⌘K
        </kbd>
      </div>

      <Bell size={18} style={{ color: "var(--pw-text-secondary)" }} />
      <Settings size={18} style={{ color: "var(--pw-text-secondary)" }} />

      {/* Avatar + logout */}
      <button
        onClick={handleLogout}
        title={`${user?.name} (${user?.role}) — click to sign out`}
        className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-semibold shrink-0"
        style={{ background: "var(--pw-primary)", border: "none", cursor: "pointer" }}
      >
        {initials}
      </button>
    </nav>
  )
}

// ── Stat cards ────────────────────────────────────────────────────────────────

type StatusFilter = "apply" | "hold" | "escalate" | null

function StatCards({ payments, activeFilter, onFilter }: {
  payments: PaymentRow[]
  activeFilter: StatusFilter
  onFilter: (f: StatusFilter) => void
}) {
  const OPEN = new Set(["held", "processing_failed", "received", "processing"])
  const openPayments = payments.filter(p => OPEN.has(p.status))
  const total = openPayments.length
  const recApply = openPayments.filter(p => p.recommendation === "apply").length
  const recHold = openPayments.filter(p => p.recommendation === "hold").length
  const recEscalate = openPayments.filter(p => p.recommendation === "escalate").length
  const openCount = openPayments.length

  function tile(filter: StatusFilter, isActive: boolean, children: React.ReactNode) {
    return (
      <button
        onClick={() => onFilter(isActive ? null : filter)}
        className="px-5 py-4 text-left w-full transition-colors hover:opacity-80"
        style={{ background: isActive ? "var(--pw-surface-elevated)" : "transparent", border: "none", cursor: "pointer" }}
      >
        {children}
        {isActive && <span className="text-[10px] font-semibold mt-1 block" style={{ color: "var(--pw-primary)" }}>Filtered ✕</span>}
      </button>
    )
  }

  return (
    <div className="pw-card grid grid-cols-4 divide-x" style={{ borderColor: "var(--pw-border)" }}>
      {/* Cases Open — not filterable, just informational */}
      <div className="px-5 py-4">
        <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--pw-text-secondary)" }}>Cases Open</p>
        <p className="mt-1 text-3xl font-bold" style={{ color: "var(--pw-text-primary)" }}>{openCount}</p>
      </div>

      {tile("apply", activeFilter === "apply", (
        <div className="flex items-start gap-3">
          <div className="mt-0.5 rounded-full p-1.5" style={{ background: "var(--pw-apply-tint)" }}>
            <CheckCircle2 size={14} style={{ color: "var(--pw-apply)" }} />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--pw-text-secondary)" }}>Rec: Apply</p>
            <p className="mt-1 text-3xl font-bold" style={{ color: "var(--pw-text-primary)" }}>{recApply}</p>
            <p className="text-xs" style={{ color: "var(--pw-text-muted)" }}>{total > 0 ? Math.round((recApply / total) * 100) : 0}%</p>
          </div>
        </div>
      ))}

      {tile("hold", activeFilter === "hold", (
        <div className="flex items-start gap-3">
          <div className="mt-0.5 rounded-full p-1.5" style={{ background: "var(--pw-hold-tint)" }}>
            <Clock size={14} style={{ color: "var(--pw-hold)" }} />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--pw-text-secondary)" }}>Rec: Hold</p>
            <p className="mt-1 text-3xl font-bold" style={{ color: "var(--pw-text-primary)" }}>{recHold}</p>
            <p className="text-xs" style={{ color: "var(--pw-text-muted)" }}>{total > 0 ? Math.round((recHold / total) * 100) : 0}%</p>
          </div>
        </div>
      ))}

      {tile("escalate", activeFilter === "escalate", (
        <div className="flex items-start gap-3">
          <div className="mt-0.5 rounded-full p-1.5" style={{ background: "var(--pw-escalate-tint)" }}>
            <TriangleAlert size={14} style={{ color: "var(--pw-escalate)" }} />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--pw-text-secondary)" }}>Rec: Escalate</p>
            <p className="mt-1 text-3xl font-bold" style={{ color: "var(--pw-text-primary)" }}>{recEscalate}</p>
            <p className="text-xs" style={{ color: "var(--pw-text-muted)" }}>{total > 0 ? Math.round((recEscalate / total) * 100) : 0}%</p>
          </div>
        </div>
      ))}
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function QueueDashboard() {
  const router = useRouter()
  const { user } = useAuth()

  const [payments, setPayments] = useState<PaymentRow[]>([])
  const [loadingData, setLoadingData] = useState(true)
  const [activeTab, setActiveTab] = useState<"open" | "closed">("open")
  const [statusFilter, setStatusFilter] = useState<StatusFilter>(null)
  const [scenarioFilter, setScenarioFilter] = useState<Set<ScenarioRoute>>(new Set())
  const [bandFilter, setBandFilter] = useState<Set<ConfidenceBand>>(new Set())
  const [methodFilter, setMethodFilter] = useState<Set<PaymentMethod>>(new Set())
  const [bannerDismissed, setBannerDismissed] = useState(false)
  const [sortKey, setSortKey] = useState<string>("confidence_desc")

  useEffect(() => {
    listPayments({ page_size: 200 })
      .then(res => setPayments(res.payments))
      .catch(console.error)
      .finally(() => setLoadingData(false))
  }, [])

  function toggle<T>(set: Set<T>, value: T): Set<T> {
    const next = new Set(set)
    next.has(value) ? next.delete(value) : next.add(value)
    return next
  }

  function clearFilters() {
    setScenarioFilter(new Set())
    setBandFilter(new Set())
    setMethodFilter(new Set())
    setStatusFilter(null)
  }

  const hasFilters = scenarioFilter.size > 0 || bandFilter.size > 0 || methodFilter.size > 0 || statusFilter !== null
  const failedCount = payments.filter(p => p.status === "processing_failed").length

  const OPEN_STATUSES = new Set(["held", "processing_failed", "received", "processing"])
  const CLOSED_STATUSES = new Set(["applied", "returned", "escalated", "pending_sender_response"])

  const openCount = payments.filter(p => OPEN_STATUSES.has(p.status)).length
  const closedCount = payments.filter(p => CLOSED_STATUSES.has(p.status)).length

  const tabPayments = payments.filter(p => {
    const inTab = activeTab === "open" ? OPEN_STATUSES.has(p.status) : CLOSED_STATUSES.has(p.status)
    const inStatusFilter = statusFilter === null || p.recommendation === statusFilter
    return inTab && inStatusFilter
  })

  const rows = tabPayments
    .map(p => ({ payment: p, rec: p }))
    .sort((a, b) => {
      switch (sortKey) {
        case "confidence_desc": return (b.rec?.confidence_score ?? 0) - (a.rec?.confidence_score ?? 0)
        case "confidence_asc":  return (a.rec?.confidence_score ?? 0) - (b.rec?.confidence_score ?? 0)
        case "sender_asc":      return a.payment.sender_name.localeCompare(b.payment.sender_name)
        case "sender_desc":     return b.payment.sender_name.localeCompare(a.payment.sender_name)
        case "amount_desc":     return b.payment.amount - a.payment.amount
        case "amount_asc":      return a.payment.amount - b.payment.amount
        case "newest":          return new Date(b.payment.created_timestamp).getTime() - new Date(a.payment.created_timestamp).getTime()
        case "oldest":          return new Date(a.payment.created_timestamp).getTime() - new Date(b.payment.created_timestamp).getTime()
        default:                return 0
      }
    })

  const filtered = rows.filter(({ payment, rec }) => {
    if (scenarioFilter.size > 0 && rec.scenario_route && !scenarioFilter.has(rec.scenario_route as ScenarioRoute)) return false
    if (bandFilter.size > 0 && rec.confidence_score != null && !bandFilter.has(getBand(rec.confidence_score))) return false
    if (methodFilter.size > 0 && !methodFilter.has(payment.payment_method as PaymentMethod)) return false
    return true
  })

  return (
    <div className="min-h-screen" style={{ background: "var(--pw-bg)" }}>
      <Nav />

      <div className="px-6 py-5 space-y-5 max-w-[1400px] mx-auto">
        {/* Page header */}
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold" style={{ color: "var(--pw-text-primary)" }}>
              Payment Operations Queue
            </h1>
          </div>
          <div className="text-right">
            <p className="text-[10px] font-semibold uppercase tracking-widest" style={{ color: "var(--pw-text-muted)" }}>
              Today
            </p>
            <p className="text-sm" style={{ color: "var(--pw-text-secondary)" }}>
              {formatToday()}
            </p>
          </div>
        </div>

        {/* Stat cards */}
        <StatCards payments={payments} activeFilter={statusFilter} onFilter={setStatusFilter} />

        {/* Processing-failed banner */}
        {failedCount > 0 && !bannerDismissed && (
          <div
            className="flex items-center justify-between rounded-lg px-4 py-3 text-sm"
            style={{
              background: "var(--pw-hold-tint)",
              border: "1px solid var(--pw-hold)",
              color: "var(--pw-hold)",
            }}
          >
            <div className="flex items-center gap-2">
              <AlertTriangle className="size-4 shrink-0" />
              <span>
                {failedCount} payment{failedCount !== 1 ? "s" : ""} failed to process.
              </span>
              <button className="font-semibold underline underline-offset-2 hover:no-underline">
                Reprocess all
              </button>
            </div>
            <button
              onClick={() => setBannerDismissed(true)}
              aria-label="Dismiss"
              style={{ color: "var(--pw-hold-hover)" }}
            >
              <X className="size-4" />
            </button>
          </div>
        )}

        {/* Main table card */}
        <div className="pw-card overflow-hidden">
          {/* Tabs */}
          <div
            className="flex items-center justify-between px-5 border-b"
            style={{ borderColor: "var(--pw-border)" }}
          >
            <div className="flex gap-6">
              <button
                onClick={() => setActiveTab("open")}
                className="flex items-center gap-2 py-3 text-sm font-medium border-b-2 -mb-px"
                style={activeTab === "open"
                  ? { borderColor: "var(--pw-primary)", color: "var(--pw-primary)" }
                  : { borderColor: "transparent", color: "var(--pw-text-secondary)" }}
              >
                Open Cases
                <span className="pw-badge" style={activeTab === "open" ? { background: "var(--pw-primary)", color: "#fff" } : {}}>
                  {openCount}
                </span>
              </button>
              <button
                onClick={() => setActiveTab("closed")}
                className="flex items-center gap-2 py-3 text-sm font-medium border-b-2 -mb-px"
                style={activeTab === "closed"
                  ? { borderColor: "var(--pw-primary)", color: "var(--pw-primary)" }
                  : { borderColor: "transparent", color: "var(--pw-text-secondary)" }}
              >
                Closed Cases
                <span className="pw-badge" style={activeTab === "closed" ? { background: "var(--pw-primary)", color: "#fff" } : { background: "var(--pw-border)" }}>
                  {closedCount}
                </span>
              </button>
            </div>
          </div>

          {/* Filter bar */}
          <div
            className="flex flex-wrap items-center gap-x-5 gap-y-2 px-5 py-3 border-b text-xs"
            style={{ borderColor: "var(--pw-border)", background: "var(--pw-surface-elevated)" }}
          >
            {/* Scenario */}
            <div className="flex items-center gap-1.5">
              <span className="font-semibold uppercase tracking-wide" style={{ color: "var(--pw-text-secondary)", fontSize: 10 }}>
                Scenario
              </span>
              {ALL_SCENARIOS.map(s => (
                <FilterChip
                  key={s}
                  active={scenarioFilter.has(s)}
                  activeStyle={{ background: "var(--pw-primary)", color: "#fff" }}
                  onClick={() => setScenarioFilter(toggle(scenarioFilter, s))}
                >
                  {SCENARIO_LABEL[s]}
                </FilterChip>
              ))}
            </div>

            {/* Confidence */}
            <div className="flex items-center gap-1.5">
              <span className="font-semibold uppercase tracking-wide" style={{ color: "var(--pw-text-secondary)", fontSize: 10 }}>
                Confidence
              </span>
              <FilterChip
                active={bandFilter.has("Low")}
                activeStyle={{ background: "var(--pw-escalate-tint)", color: "var(--pw-escalate)", border: "1px solid var(--pw-escalate)" }}
                onClick={() => setBandFilter(toggle(bandFilter, "Low"))}
              >
                Low
              </FilterChip>
              <FilterChip
                active={bandFilter.has("Medium")}
                activeStyle={{ background: "var(--pw-hold-tint)", color: "var(--pw-hold)", border: "1px solid var(--pw-hold)" }}
                onClick={() => setBandFilter(toggle(bandFilter, "Medium"))}
              >
                Medium
              </FilterChip>
              <FilterChip
                active={bandFilter.has("High")}
                activeStyle={{ background: "var(--pw-apply-tint)", color: "var(--pw-apply)", border: "1px solid var(--pw-apply)" }}
                onClick={() => setBandFilter(toggle(bandFilter, "High"))}
              >
                High
              </FilterChip>
            </div>

            {/* Method */}
            <div className="flex items-center gap-1.5">
              <span className="font-semibold uppercase tracking-wide" style={{ color: "var(--pw-text-secondary)", fontSize: 10 }}>
                Method
              </span>
              {ALL_METHODS.map(method => (
                <FilterChip
                  key={method}
                  active={methodFilter.has(method)}
                  activeStyle={{ background: "var(--pw-info-tint)", color: "var(--pw-info)", border: "1px solid var(--pw-info)" }}
                  onClick={() => setMethodFilter(toggle(methodFilter, method))}
                >
                  {method}
                </FilterChip>
              ))}
            </div>

            {/* Sort */}
            <div className="flex items-center gap-1.5 ml-auto">
              <span className="font-semibold uppercase tracking-wide" style={{ color: "var(--pw-text-secondary)", fontSize: 10 }}>
                Sort
              </span>
              <select
                aria-label="Sort by"
                value={sortKey}
                onChange={e => setSortKey(e.target.value)}
                style={{
                  fontSize: 12,
                  color: "var(--pw-text-primary)",
                  background: "var(--pw-surface)",
                  border: "1px solid var(--pw-border)",
                  borderRadius: 6,
                  padding: "2px 6px",
                  cursor: "pointer",
                  outline: "none",
                }}
              >
                <option value="confidence_desc">Confidence: High → Low</option>
                <option value="confidence_asc">Confidence: Low → High</option>
                <option value="sender_asc">Sender: A → Z</option>
                <option value="sender_desc">Sender: Z → A</option>
                <option value="amount_desc">Amount: High → Low</option>
                <option value="amount_asc">Amount: Low → High</option>
                <option value="newest">Newest First</option>
                <option value="oldest">Oldest First</option>
              </select>
            </div>

            {hasFilters && (
              <button
                onClick={clearFilters}
                className="text-xs underline underline-offset-2 hover:no-underline"
                style={{ color: "var(--pw-text-muted)" }}
              >
                Clear filters
              </button>
            )}
          </div>

          {/* Table / Empty state */}
          {filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <p style={{ color: "var(--pw-text-secondary)" }}>No payments match your filters.</p>
              <Button variant="outline" size="sm" className="mt-3" onClick={clearFilters}>
                Clear filters
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow style={{ borderColor: "var(--pw-border)" }}>
                  <TableHead className="w-[100px]" style={{ color: "var(--pw-text-secondary)", fontSize: 11 }}>ID</TableHead>
                  <TableHead style={{ color: "var(--pw-text-secondary)", fontSize: 11 }}>SENDER</TableHead>
                  <TableHead style={{ color: "var(--pw-text-secondary)", fontSize: 11 }}>AMOUNT</TableHead>
                  <TableHead style={{ color: "var(--pw-text-secondary)", fontSize: 11 }}>RECOMMENDATION</TableHead>
                  <TableHead style={{ color: "var(--pw-text-secondary)", fontSize: 11 }}>CONFIDENCE</TableHead>
                  <TableHead style={{ color: "var(--pw-text-secondary)", fontSize: 11 }}>FLAGS</TableHead>
                  <TableHead style={{ color: "var(--pw-text-secondary)", fontSize: 11 }}>AGE</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filtered.map(({ payment }) => {
                  const flags = getFlags(payment)
                  return (
                    <TableRow
                      key={payment.payment_id}
                      className="cursor-pointer"
                      style={{ borderColor: "var(--pw-border)" }}
                      onClick={() => router.push(`/payments/${payment.payment_id}`)}
                    >
                      {/* ID */}
                      <TableCell>
                        <span
                          className="text-xs font-medium"
                          style={{
                            fontFamily: "var(--pw-font-mono)",
                            color: "var(--pw-primary)",
                          }}
                        >
                          {payment.payment_id}
                        </span>
                      </TableCell>

                      {/* Sender */}
                      <TableCell className="font-medium text-sm" style={{ color: "var(--pw-text-primary)" }}>
                        {payment.sender_name}
                      </TableCell>

                      {/* Amount */}
                      <TableCell
                        className="text-sm font-medium"
                        style={{ fontFamily: "var(--pw-font-mono)", color: "var(--pw-text-primary)" }}
                      >
                        {formatUSD(payment.amount)}
                      </TableCell>

                      {/* Recommendation */}
                      <TableCell>
                        {payment.recommendation ? (
                          <RecBadge rec={payment.recommendation as "apply" | "hold" | "escalate"} />
                        ) : (
                          <span className="pw-badge pw-badge-neutral">PENDING</span>
                        )}
                      </TableCell>

                      {/* Confidence */}
                      <TableCell>
                        {payment.confidence_score != null ? (
                          <ConfidencePct score={payment.confidence_score} />
                        ) : (
                          <span style={{ color: "var(--pw-text-muted)" }}>—</span>
                        )}
                      </TableCell>

                      {/* Flags */}
                      <TableCell>
                        {flags.length > 0 ? (
                          <div className="flex flex-wrap gap-1">
                            {flags.map(f => (
                              <span
                                key={f}
                                className="text-xs font-medium"
                                style={{ color: "var(--pw-hold)" }}
                              >
                                {f}
                              </span>
                            ))}
                          </div>
                        ) : (
                          <span style={{ color: "var(--pw-text-muted)" }}>—</span>
                        )}
                      </TableCell>

                      {/* Age */}
                      <TableCell className="text-xs" style={{ color: "var(--pw-text-muted)" }}>
                        {formatAge(payment.created_timestamp)}
                      </TableCell>
                    </TableRow>
                  )
                })}
              </TableBody>
            </Table>
          )}

          {/* Table footer */}
          <div
            className="px-5 py-2.5 border-t text-xs"
            style={{ borderColor: "var(--pw-border)", color: "var(--pw-text-muted)" }}
          >
            {loadingData ? "Loading…" : `Showing ${filtered.length} of ${tabPayments.length} cases`}
          </div>
        </div>
      </div>

      {/* Status bar */}
      <footer
        className="fixed bottom-0 left-0 right-0 flex items-center justify-between px-5 text-[11px]"
        style={{
          height: "var(--pw-footer-height)",
          background: "var(--pw-surface)",
          borderTop: "1px solid var(--pw-border)",
          color: "var(--pw-text-muted)",
        }}
      >
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 inline-block" />
            Audit Active
          </div>
          <span>User: {user?.name ?? "—"}</span>
        </div>
        <span style={{ color: "var(--pw-text-muted)" }}>
          Press <kbd className="rounded px-1 py-0.5 text-[10px]" style={{ background: "var(--pw-surface-elevated)" }}>?</kbd> for keyboard shortcuts
        </span>
      </footer>
    </div>
  )
}
