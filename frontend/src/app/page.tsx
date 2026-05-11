"use client"

import { useState, useEffect } from "react"
import { useRouter } from "next/navigation"
import useSWR from "swr"
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
import { Skeleton } from "@/components/ui/skeleton"
import { apiFetch, ApiError } from "@/lib/api"
import { useToast } from "@/contexts/ToastContext"
import type { PaymentListResponse, PaymentListItem } from "@/types/api"
import type { ScenarioRoute } from "@/types/recommendation"
import type { PaymentMethod, Payment } from "@/types/payment"
import type { PaymentSignals } from "@/types/signals"

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

function getFlags(payment: Payment, signals: PaymentSignals | null | undefined): string[] {
  const flags: string[] = []
  if (!signals) return flags
  if (signals.duplicate?.is_duplicate_match) flags.push("Duplicate")
  if ((signals.amount?.amount_variance_pct ?? 0) > 2) flags.push("Amount Variance")
  if ((signals.risk?.risk_flag_types?.length ?? 0) > 0) {
    signals.risk.risk_flag_types.forEach(f =>
      flags.push(f.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase()))
    )
  }
  if (payment.sla_breached) flags.push("SLA Breach")
  return flags
}

const SCENARIO_LABEL: Record<ScenarioRoute, string> = {
  scenario_1: "Sc1",
  scenario_2: "Sc2",
  scenario_3: "Sc3",
  scenario_4: "Sc4",
  scenario_5: "Sc5",
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
  return (
    <nav
      className="flex items-center gap-3 px-5 border-b"
      style={{
        height: "var(--pw-nav-height)",
        background: "var(--pw-surface)",
        borderColor: "var(--pw-border)",
      }}
    >
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

      <div
        className="w-8 h-8 rounded-full flex items-center justify-center text-white text-xs font-semibold shrink-0"
        style={{ background: "var(--pw-primary)" }}
      >
        PV
      </div>
    </nav>
  )
}

// ── Stat cards ────────────────────────────────────────────────────────────────

function StatCards({ items, loading }: { items: PaymentListItem[]; loading: boolean }) {
  const payments = items.map(i => i.payment)
  const total = payments.length
  const onHold = payments.filter(p => p.status === "held").length
  const escalated = payments.filter(p => p.status === "escalated" || p.status === "pending_sender_response").length
  const applied = payments.filter(p => p.status === "applied").length

  const statStyle = { height: 56 }

  return (
    <div
      className="pw-card grid grid-cols-4 divide-x"
      style={{ borderColor: "var(--pw-border)" }}
    >
      <div className="px-5 py-4">
        <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--pw-text-secondary)" }}>
          Cases Open
        </p>
        {loading ? (
          <Skeleton className="mt-1 h-8 w-16" />
        ) : (
          <p className="mt-1 text-3xl font-bold" style={{ color: "var(--pw-text-primary)" }}>
            {total - applied}
          </p>
        )}
      </div>

      <div className="px-5 py-4 flex items-start gap-3">
        <div className="mt-0.5 rounded-full p-1.5" style={{ background: "var(--pw-apply-tint)" }}>
          <CheckCircle2 size={14} style={{ color: "var(--pw-apply)" }} />
        </div>
        <div style={statStyle}>
          <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--pw-text-secondary)" }}>
            Auto-Applied
          </p>
          {loading ? <Skeleton className="mt-1 h-8 w-12" /> : (
            <>
              <p className="mt-1 text-3xl font-bold" style={{ color: "var(--pw-text-primary)" }}>{applied}</p>
              <p className="text-xs" style={{ color: "var(--pw-text-muted)" }}>
                {total > 0 ? Math.round((applied / total) * 100) : 0}%
              </p>
            </>
          )}
        </div>
      </div>

      <div className="px-5 py-4 flex items-start gap-3">
        <div className="mt-0.5 rounded-full p-1.5" style={{ background: "var(--pw-hold-tint)" }}>
          <Clock size={14} style={{ color: "var(--pw-hold)" }} />
        </div>
        <div style={statStyle}>
          <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--pw-text-secondary)" }}>
            On Hold
          </p>
          {loading ? <Skeleton className="mt-1 h-8 w-12" /> : (
            <>
              <p className="mt-1 text-3xl font-bold" style={{ color: "var(--pw-text-primary)" }}>{onHold}</p>
              <p className="text-xs" style={{ color: "var(--pw-text-muted)" }}>
                {total > 0 ? Math.round((onHold / total) * 100) : 0}%
              </p>
            </>
          )}
        </div>
      </div>

      <div className="px-5 py-4 flex items-start gap-3">
        <div className="mt-0.5 rounded-full p-1.5" style={{ background: "var(--pw-escalate-tint)" }}>
          <TriangleAlert size={14} style={{ color: "var(--pw-escalate)" }} />
        </div>
        <div style={statStyle}>
          <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--pw-text-secondary)" }}>
            Escalated
          </p>
          {loading ? <Skeleton className="mt-1 h-8 w-12" /> : (
            <>
              <p className="mt-1 text-3xl font-bold" style={{ color: "var(--pw-text-primary)" }}>{escalated}</p>
              <p className="text-xs" style={{ color: "var(--pw-text-muted)" }}>
                {total > 0 ? Math.round((escalated / total) * 100) : 0}%
              </p>
            </>
          )}
        </div>
      </div>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

const QUEUE_KEY = "/api/payments?status=held,processing_failed&sort_by=confidence_score"

export default function QueueDashboard() {
  const router = useRouter()
  const { showToast } = useToast()

  const { data, error, isLoading, mutate } = useSWR<PaymentListResponse>(QUEUE_KEY)

  const items: PaymentListItem[] = data?.data ?? []

  const [scenarioFilter, setScenarioFilter] = useState<Set<ScenarioRoute>>(new Set())
  const [bandFilter, setBandFilter] = useState<Set<ConfidenceBand>>(new Set())
  const [methodFilter, setMethodFilter] = useState<Set<PaymentMethod>>(new Set())
  const [bannerDismissed, setBannerDismissed] = useState(false)
  const [sortKey, setSortKey] = useState<string>("confidence_desc")
  const [reprocessing, setReprocessing] = useState(false)

  useEffect(() => {
    if (!error) return
    if (error instanceof ApiError) {
      if (error.status === 403) showToast({ title: "Permission denied", type: "warning" })
      else if (error.status >= 500) showToast({ title: "Something went wrong", type: "error" })
    }
  }, [error, showToast])

  function toggle<T>(set: Set<T>, value: T): Set<T> {
    const next = new Set(set)
    next.has(value) ? next.delete(value) : next.add(value)
    return next
  }

  function clearFilters() {
    setScenarioFilter(new Set())
    setBandFilter(new Set())
    setMethodFilter(new Set())
  }

  async function reprocessAll() {
    const failed = items.filter(i => i.payment.status === "processing_failed")
    if (failed.length === 0) return
    setReprocessing(true)
    try {
      await Promise.all(
        failed.map(i =>
          apiFetch(`/api/payments/${i.payment.payment_id}/reprocess`, { method: "POST" })
        )
      )
      showToast({ title: `${failed.length} payment${failed.length !== 1 ? "s" : ""} queued for reprocessing`, type: "success" })
      mutate()
    } catch {
      showToast({ title: "Reprocess failed", type: "error" })
    } finally {
      setReprocessing(false)
    }
  }

  const hasFilters = scenarioFilter.size > 0 || bandFilter.size > 0 || methodFilter.size > 0
  const failedCount = items.filter(i => i.payment.status === "processing_failed").length
  const openCount = items.filter(i => i.payment.status !== "applied" && i.payment.status !== "returned").length
  const closedCount = items.filter(i => i.payment.status === "applied" || i.payment.status === "returned").length

  const rows = items
    .map(item => ({ payment: item.payment, rec: item.recommendation, signals: item.signals }))
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
    if (!rec) return true
    if (scenarioFilter.size > 0 && !scenarioFilter.has(rec.scenario_route)) return false
    if (bandFilter.size > 0 && !bandFilter.has(getBand(rec.confidence_score))) return false
    if (methodFilter.size > 0 && !methodFilter.has(payment.payment_method)) return false
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

        <StatCards items={items} loading={isLoading} />

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
              <button
                onClick={reprocessAll}
                disabled={reprocessing}
                className="font-semibold underline underline-offset-2 hover:no-underline disabled:opacity-60"
              >
                {reprocessing ? "Reprocessing…" : "Reprocess all"}
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
                className="flex items-center gap-2 py-3 text-sm font-medium border-b-2 -mb-px"
                style={{ borderColor: "var(--pw-primary)", color: "var(--pw-primary)" }}
              >
                Open Cases
                <span className="pw-badge" style={{ background: "var(--pw-primary)", color: "#fff" }}>
                  {openCount}
                </span>
              </button>
              <button
                className="flex items-center gap-2 py-3 text-sm font-medium border-b-2 border-transparent"
                style={{ color: "var(--pw-text-secondary)" }}
              >
                Closed Cases
                <span className="pw-badge pw-badge-neutral">{closedCount}</span>
              </button>
            </div>
          </div>

          {/* Filter bar */}
          <div
            className="flex flex-wrap items-center gap-x-5 gap-y-2 px-5 py-3 border-b text-xs"
            style={{ borderColor: "var(--pw-border)", background: "var(--pw-surface-elevated)" }}
          >
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

            <div className="flex items-center gap-1.5 ml-auto">
              <span className="font-semibold uppercase tracking-wide" style={{ color: "var(--pw-text-secondary)", fontSize: 10 }}>
                Sort
              </span>
              <select
                aria-label="Sort by"
                value={sortKey}
                onChange={e => setSortKey(e.target.value)}
                style={{
                  fontSize: 12, color: "var(--pw-text-primary)",
                  background: "var(--pw-surface)", border: "1px solid var(--pw-border)",
                  borderRadius: 6, padding: "2px 6px", cursor: "pointer", outline: "none",
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

          {/* Loading skeletons */}
          {isLoading && (
            <div className="p-5 space-y-3">
              {Array.from({ length: 6 }, (_: unknown, i: number) => (
                <Skeleton key={i} style={{ height: 44, width: "100%" }} />
              ))}
            </div>
          )}

          {/* Error state */}
          {error && !isLoading && (
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <p style={{ color: "var(--pw-escalate)" }}>
                {error instanceof ApiError && error.status === 404
                  ? "No payments found."
                  : "Failed to load payments."}
              </p>
              <Button variant="outline" size="sm" className="mt-3" onClick={() => mutate()}>
                Retry
              </Button>
            </div>
          )}

          {/* Table / Empty state */}
          {!isLoading && !error && (
            filtered.length === 0 ? (
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
                  {filtered.map(({ payment, rec, signals }) => {
                    const flags = getFlags(payment, signals)
                    return (
                      <TableRow
                        key={payment.payment_id}
                        className="cursor-pointer"
                        style={{ borderColor: "var(--pw-border)" }}
                        onClick={() => router.push(`/payments/${payment.payment_id}`)}
                      >
                        <TableCell>
                          <span
                            className="text-xs font-medium"
                            style={{ fontFamily: "var(--pw-font-mono)", color: "var(--pw-primary)" }}
                          >
                            {payment.payment_id}
                          </span>
                        </TableCell>
                        <TableCell className="font-medium text-sm" style={{ color: "var(--pw-text-primary)" }}>
                          {payment.sender_name}
                        </TableCell>
                        <TableCell
                          className="text-sm font-medium"
                          style={{ fontFamily: "var(--pw-font-mono)", color: "var(--pw-text-primary)" }}
                        >
                          {formatUSD(payment.amount)}
                        </TableCell>
                        <TableCell>
                          {rec ? (
                            <RecBadge rec={rec.recommendation} />
                          ) : (
                            <span className="pw-badge pw-badge-neutral">FAILED</span>
                          )}
                        </TableCell>
                        <TableCell>
                          {rec ? (
                            <ConfidencePct score={rec.confidence_score} />
                          ) : (
                            <span style={{ color: "var(--pw-text-muted)" }}>—</span>
                          )}
                        </TableCell>
                        <TableCell>
                          {flags.length > 0 ? (
                            <div className="flex flex-wrap gap-1">
                              {flags.map(f => (
                                <span key={f} className="text-xs font-medium" style={{ color: "var(--pw-hold)" }}>
                                  {f}
                                </span>
                              ))}
                            </div>
                          ) : (
                            <span style={{ color: "var(--pw-text-muted)" }}>—</span>
                          )}
                        </TableCell>
                        <TableCell className="text-xs" style={{ color: "var(--pw-text-muted)" }}>
                          {formatAge(payment.created_timestamp)}
                        </TableCell>
                      </TableRow>
                    )
                  })}
                </TableBody>
              </Table>
            )
          )}

          {/* Table footer */}
          {!isLoading && !error && (
            <div
              className="px-5 py-2.5 border-t text-xs"
              style={{ borderColor: "var(--pw-border)", color: "var(--pw-text-muted)" }}
            >
              Showing {filtered.length} of {items.length} cases
            </div>
          )}
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
          <span>User: Priya Venkataraman</span>
        </div>
        <span style={{ color: "var(--pw-text-muted)" }}>
          Press <kbd className="rounded px-1 py-0.5 text-[10px]" style={{ background: "var(--pw-surface-elevated)" }}>?</kbd> for keyboard shortcuts
        </span>
      </footer>
    </div>
  )
}
