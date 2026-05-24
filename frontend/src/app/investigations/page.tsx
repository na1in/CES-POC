"use client"

import React, { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import { Search, Bell, Settings, Clock, AlertTriangle, CheckCircle2, Search as SearchIcon, ChevronDown } from "lucide-react"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import { listPayments, type PaymentRow } from "@/lib/api"
import { useAuth } from "@/contexts/auth"

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatUSD(cents: number): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(cents / 100)
}

function formatTimeSince(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const totalHours = Math.floor(diff / 3_600_000)
  const days = Math.floor(totalHours / 24)
  const hours = totalHours % 24
  if (days === 0) return `${totalHours}h ago`
  if (hours === 0) return `${days}d ago`
  return `${days}d ${hours}h ago`
}

function formatEscalationDate(iso: string): string {
  return new Date(iso).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  })
}

function formatToday(): string {
  return new Date().toLocaleDateString("en-US", {
    weekday: "long", month: "long", day: "numeric", year: "numeric",
  })
}

type RiskLevel = "high" | "medium" | "low"
type InvestigationStatus = "sla_breached" | "pending_outreach" | "new"

function getRiskLevel(payment: PaymentRow): RiskLevel {
  if (payment.has_risk_flags) return "high"
  return "medium"
}

function getInvestigationStatus(payment: PaymentRow): InvestigationStatus {
  if (payment.sla_breached) return "sla_breached"
  if (payment.status === "pending_sender_response") return "pending_outreach"
  return "new"
}

function getReason(payment: PaymentRow): string {
  if (payment.scenario_route === "scenario_5") return "Duplicate payment detected within 72h"
  if (payment.scenario_route === "scenario_4") return "No matching customer found"
  if (payment.scenario_route === "scenario_3") return "High amount variance"
  if (payment.scenario_route === "scenario_2") return "Customer match, no policy reference"
  return "—"
}

// ── FilterChip ────────────────────────────────────────────────────────────────

function FilterChip({
  active, activeStyle, onClick, children,
}: {
  active: boolean
  activeStyle?: React.CSSProperties
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      onClick={onClick}
      style={active
        ? { border: "1px solid transparent", ...activeStyle }
        : { border: "1px solid var(--pw-border)", color: "var(--pw-text-secondary)", background: "transparent" }}
      className="rounded-md px-2 py-0.5 text-xs font-medium transition-colors hover:opacity-80"
    >
      {children}
    </button>
  )
}

// ── Sub-components ────────────────────────────────────────────────────────────

function RiskLevelBadge({ level }: { level: RiskLevel }) {
  const styles: Record<RiskLevel, { bg: string; color: string }> = {
    high:   { bg: "var(--pw-escalate-tint)", color: "var(--pw-escalate)" },
    medium: { bg: "var(--pw-hold-tint)",     color: "var(--pw-hold)"     },
    low:    { bg: "var(--pw-apply-tint)",    color: "var(--pw-apply)"    },
  }
  const s = styles[level]
  return (
    <span
      className="pw-badge"
      style={{ background: s.bg, color: s.color, textTransform: "capitalize" }}
    >
      {level}
    </span>
  )
}

function StatusBadge({ status }: { status: InvestigationStatus }) {
  if (status === "sla_breached") {
    return (
      <span className="pw-badge pw-badge-escalate">SLA BREACHED</span>
    )
  }
  if (status === "pending_outreach") {
    return (
      <span className="pw-badge pw-badge-hold">Pending Outreach</span>
    )
  }
  return (
    <span className="pw-badge pw-badge-neutral">New</span>
  )
}

// ── Nav ───────────────────────────────────────────────────────────────────────

function Nav({ user, logout, router }: { user: { name: string; role?: string } | null; logout: () => void; router: ReturnType<typeof import("next/navigation").useRouter> }) {
  const [roleMenuOpen, setRoleMenuOpen] = React.useState(false)
  const initials = user?.name.split(" ").map((w: string) => w[0]).join("").slice(0, 2) ?? "?"
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
      <div style={{ position: "relative" }}>
        <button
          aria-label="Switch role"
          onClick={() => setRoleMenuOpen(o => !o)}
          style={{
            display: "flex", alignItems: "center", gap: 6,
            background: "var(--pw-bg)", border: "1px solid var(--pw-border)",
            borderRadius: 8, padding: "4px 10px", fontSize: 12,
            color: "var(--pw-text-secondary)", cursor: "pointer",
          }}
        >
          <div style={{
            width: 22, height: 22, borderRadius: "50%", background: "var(--pw-primary)",
            display: "flex", alignItems: "center", justifyContent: "center",
            color: "#fff", fontWeight: 700, fontSize: 10,
          }}>
            {initials}
          </div>
          {user?.name.split(" ")[0] ?? "User"}
          <ChevronDown size={12} />
        </button>
        {roleMenuOpen && (
          <div style={{
            position: "absolute", right: 0, top: "calc(100% + 6px)",
            background: "var(--pw-surface)", border: "1px solid var(--pw-border)",
            borderRadius: 8, boxShadow: "var(--pw-shadow-md)", zIndex: 60,
            minWidth: 180, overflow: "hidden",
          }}>
            <button
              onClick={() => { logout(); router.push("/login"); setRoleMenuOpen(false) }}
              style={{
                display: "block", width: "100%", textAlign: "left",
                padding: "9px 14px", fontSize: 13, cursor: "pointer",
                background: "transparent",
                border: "none", color: "var(--pw-escalate)",
              }}
            >
              Sign out
              <span style={{ fontSize: 11, color: "var(--pw-text-muted)", marginLeft: 6 }}>({user?.role})</span>
            </button>
          </div>
        )}
      </div>
    </nav>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function InvestigationQueue() {
  const router = useRouter()
  const { user, logout } = useAuth()

  const [payments, setPayments] = useState<PaymentRow[]>([])
  const [activeTab, setActiveTab] = useState<"open" | "closed">("open")
  const [riskFilter, setRiskFilter] = useState<Set<RiskLevel>>(new Set())
  const [statusFilter, setStatusFilter] = useState<Set<InvestigationStatus>>(new Set())
  const [sortKey, setSortKey] = useState("risk_asc")
  const [showSlaReport, setShowSlaReport] = useState(false)

  useEffect(() => {
    listPayments({ page_size: 200 })
      .then(res => {
        const inv = res.payments.filter(
          p => ["escalated", "pending_sender_response", "returned", "applied"].includes(p.status)
            && p.recommendation === "escalate"
        )
        setPayments(inv)
      })
      .catch(console.error)
  }, [])

  function toggle<T>(set: Set<T>, val: T): Set<T> {
    const next = new Set(set)
    next.has(val) ? next.delete(val) : next.add(val)
    return next
  }

  const allRows = payments.map(p => ({
    payment: p,
    riskLevel: getRiskLevel(p),
    invStatus: getInvestigationStatus(p),
    reason: getReason(p),
  }))

  const openRows = allRows.filter(r => r.payment.status === "escalated" || r.payment.status === "pending_sender_response")
  const closedRows = allRows.filter(r => r.payment.status === "returned" || r.payment.status === "applied")

  const fraudFlaggedCount = openRows.filter(r => r.payment.has_risk_flags).length
  const pendingOutreachCount = openRows.filter(r => r.invStatus === "pending_outreach").length
  const closedToday = closedRows.filter(r => {
    const d = new Date(r.payment.created_timestamp)
    const now = new Date()
    return d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth() && d.getDate() === now.getDate()
  }).length

  const tabRows = activeTab === "open" ? openRows : closedRows

  const filteredRows = tabRows.filter(r => {
    if (riskFilter.size > 0 && !riskFilter.has(r.riskLevel)) return false
    if (statusFilter.size > 0 && !statusFilter.has(r.invStatus)) return false
    return true
  }).sort((a, b) => {
    switch (sortKey) {
      case "risk_asc": {
        const order = { high: 0, medium: 1, low: 2 }
        if (a.riskLevel !== b.riskLevel) return order[a.riskLevel] - order[b.riskLevel]
        return new Date(a.payment.created_timestamp).getTime() - new Date(b.payment.created_timestamp).getTime()
      }
      case "amount_desc": return b.payment.amount - a.payment.amount
      case "amount_asc":  return a.payment.amount - b.payment.amount
      case "newest": return new Date(b.payment.created_timestamp).getTime() - new Date(a.payment.created_timestamp).getTime()
      case "oldest": return new Date(a.payment.created_timestamp).getTime() - new Date(b.payment.created_timestamp).getTime()
      default: return 0
    }
  })

  const hasFilters = riskFilter.size > 0 || statusFilter.size > 0
  function clearFilters() { setRiskFilter(new Set()); setStatusFilter(new Set()) }

  return (
    <div className="min-h-screen" style={{ background: "var(--pw-bg)" }}>
      <Nav user={user} logout={logout} router={router} />

      <div className="px-6 py-5 space-y-5">
        {/* Page header */}
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold" style={{ color: "var(--pw-text-primary)" }}>
              Investigation Queue
            </h1>
            <p className="text-sm mt-0.5" style={{ color: "var(--pw-text-secondary)" }}>
              Escalated cases requiring specialist investigation
            </p>
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
        <div className="pw-card grid grid-cols-4 divide-x" style={{ borderColor: "var(--pw-border)" }}>
          {[
            {
              label: "Open Investigations", value: openRows.length, icon: <SearchIcon size={14} style={{ color: "var(--pw-info)" }} />,
              tint: "var(--pw-info-tint)", onClick: () => { setActiveTab("open"); clearFilters() },
              active: activeTab === "open",
            },
            {
              label: "Fraud Flagged", value: fraudFlaggedCount, icon: <AlertTriangle size={14} style={{ color: "var(--pw-escalate)" }} />,
              tint: "var(--pw-escalate-tint)", onClick: () => { setActiveTab("open"); setRiskFilter(new Set(["high"])); setStatusFilter(new Set()) },
              active: activeTab === "open" && riskFilter.has("high"),
            },
            {
              label: "Pending Outreach", value: pendingOutreachCount, icon: <Clock size={14} style={{ color: "var(--pw-hold)" }} />,
              tint: "var(--pw-hold-tint)", onClick: () => { setActiveTab("open"); setStatusFilter(new Set(["pending_outreach"])); setRiskFilter(new Set()) },
              active: activeTab === "open" && statusFilter.has("pending_outreach"),
            },
            {
              label: "Cases Closed Today", value: closedToday, icon: <CheckCircle2 size={14} style={{ color: "var(--pw-apply)" }} />,
              tint: "var(--pw-apply-tint)", onClick: () => { setActiveTab("closed"); clearFilters() },
              active: activeTab === "closed",
            },
          ].map(({ label, value, icon, tint, onClick, active }) => (
            <button
              key={label}
              onClick={onClick}
              className="px-5 py-4 text-left flex items-start gap-3 transition-colors hover:opacity-80 w-full"
              style={{ background: active ? "var(--pw-surface-elevated)" : "transparent", border: "none", cursor: "pointer" }}
            >
              <div className="mt-0.5 rounded-full p-1.5" style={{ background: tint }}>{icon}</div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--pw-text-secondary)" }}>{label}</p>
                <p className="mt-1 text-3xl font-bold" style={{ color: "var(--pw-text-primary)" }}>{value}</p>
                {active && <p className="text-[10px] font-semibold mt-0.5" style={{ color: "var(--pw-primary)" }}>Filtered ✕</p>}
              </div>
            </button>
          ))}
        </div>

        {/* Table card */}
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
                  {openRows.length}
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
                  {closedRows.length}
                </span>
              </button>
            </div>
          </div>

          {/* Filter bar */}
          <div
            className="flex flex-wrap items-center gap-x-5 gap-y-2 px-5 py-3 border-b text-xs"
            style={{ borderColor: "var(--pw-border)", background: "var(--pw-surface-elevated)" }}
          >
            <div className="flex items-center gap-1.5">
              <span className="font-semibold uppercase tracking-wide" style={{ color: "var(--pw-text-secondary)", fontSize: 10 }}>Risk</span>
              {(["high", "medium", "low"] as RiskLevel[]).map(r => (
                <FilterChip key={r} active={riskFilter.has(r)}
                  activeStyle={{ background: r === "high" ? "var(--pw-escalate-tint)" : r === "medium" ? "var(--pw-hold-tint)" : "var(--pw-apply-tint)", color: r === "high" ? "var(--pw-escalate)" : r === "medium" ? "var(--pw-hold)" : "var(--pw-apply)", border: "1px solid currentColor" }}
                  onClick={() => setRiskFilter(toggle(riskFilter, r))}
                >
                  {r.charAt(0).toUpperCase() + r.slice(1)}
                </FilterChip>
              ))}
            </div>
            {activeTab === "open" && (
              <div className="flex items-center gap-1.5">
                <span className="font-semibold uppercase tracking-wide" style={{ color: "var(--pw-text-secondary)", fontSize: 10 }}>Status</span>
                <FilterChip active={statusFilter.has("sla_breached")} activeStyle={{ background: "var(--pw-escalate-tint)", color: "var(--pw-escalate)", border: "1px solid var(--pw-escalate)" }} onClick={() => setStatusFilter(toggle(statusFilter, "sla_breached"))}>SLA Breached</FilterChip>
                <FilterChip active={statusFilter.has("pending_outreach")} activeStyle={{ background: "var(--pw-hold-tint)", color: "var(--pw-hold)", border: "1px solid var(--pw-hold)" }} onClick={() => setStatusFilter(toggle(statusFilter, "pending_outreach"))}>Pending Outreach</FilterChip>
                <FilterChip active={statusFilter.has("new")} activeStyle={{ background: "var(--pw-info-tint)", color: "var(--pw-info)", border: "1px solid var(--pw-info)" }} onClick={() => setStatusFilter(toggle(statusFilter, "new"))}>New</FilterChip>
              </div>
            )}
            <div className="flex items-center gap-1.5 ml-auto">
              <span className="font-semibold uppercase tracking-wide" style={{ color: "var(--pw-text-secondary)", fontSize: 10 }}>Sort</span>
              <select
                aria-label="Sort by"
                value={sortKey}
                onChange={e => setSortKey(e.target.value)}
                style={{ fontSize: 12, color: "var(--pw-text-primary)", background: "var(--pw-surface)", border: "1px solid var(--pw-border)", borderRadius: 6, padding: "2px 6px", cursor: "pointer", outline: "none" }}
              >
                <option value="risk_asc">Risk: High → Low</option>
                <option value="newest">Newest First</option>
                <option value="oldest">Oldest First</option>
                <option value="amount_desc">Amount: High → Low</option>
                <option value="amount_asc">Amount: Low → High</option>
              </select>
            </div>
            {hasFilters && (
              <button onClick={clearFilters} className="text-xs underline underline-offset-2 hover:no-underline" style={{ color: "var(--pw-text-muted)" }}>
                Clear filters
              </button>
            )}
          </div>

          {/* Table / Empty state */}
          {filteredRows.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <p style={{ color: "var(--pw-text-secondary)" }}>
                {activeTab === "open" ? "No open investigations." : "No closed cases yet."}
              </p>
              {hasFilters && <button onClick={clearFilters} className="mt-2 text-sm underline underline-offset-2" style={{ color: "var(--pw-primary)" }}>Clear filters</button>}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow style={{ borderColor: "var(--pw-border)" }}>
                  <TableHead className="w-[100px]" style={{ color: "var(--pw-text-secondary)", fontSize: 11 }}>ID</TableHead>
                  <TableHead style={{ color: "var(--pw-text-secondary)", fontSize: 11 }}>SENDER</TableHead>
                  <TableHead style={{ color: "var(--pw-text-secondary)", fontSize: 11 }}>AMOUNT</TableHead>
                  <TableHead style={{ color: "var(--pw-text-secondary)", fontSize: 11 }}>REASON</TableHead>
                  <TableHead style={{ color: "var(--pw-text-secondary)", fontSize: 11 }}>RISK</TableHead>
                  <TableHead style={{ color: "var(--pw-text-secondary)", fontSize: 11 }}>ESCALATED BY</TableHead>
                  <TableHead style={{ color: "var(--pw-text-secondary)", fontSize: 11 }}>TIME IN QUEUE</TableHead>
                  <TableHead style={{ color: "var(--pw-text-secondary)", fontSize: 11 }}>STATUS</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredRows.map(({ payment, riskLevel, invStatus, reason }) => (
                  <TableRow
                    key={payment.payment_id}
                    className="cursor-pointer hover:bg-[var(--pw-surface-elevated)]"
                    style={{ borderColor: "var(--pw-border)", background: invStatus === "sla_breached" ? "rgba(239,68,68,0.04)" : undefined }}
                    onClick={() => router.push(`/payments/${payment.payment_id}`)}
                  >
                    <TableCell>
                      <span className="text-xs font-medium" style={{ fontFamily: "var(--pw-font-mono)", color: "var(--pw-primary)" }}>
                        {payment.payment_id}
                      </span>
                    </TableCell>
                    <TableCell className="font-medium text-sm" style={{ color: "var(--pw-text-primary)" }}>
                      {payment.sender_name}
                    </TableCell>
                    <TableCell className="text-sm font-medium" style={{ fontFamily: "var(--pw-font-mono)", color: "var(--pw-text-primary)" }}>
                      {formatUSD(payment.amount)}
                    </TableCell>
                    <TableCell className="text-sm max-w-[220px] truncate" style={{ color: "var(--pw-text-secondary)" }} title={reason}>
                      {reason}
                    </TableCell>
                    <TableCell>
                      <RiskLevelBadge level={riskLevel} />
                    </TableCell>
                    <TableCell className="text-sm" style={{ color: "var(--pw-text-muted)" }}>
                      {payment.escalated_by ?? "—"}
                    </TableCell>
                    <TableCell className="text-sm font-medium" style={{ color: "var(--pw-text-secondary)" }}>
                      {formatTimeSince(payment.created_timestamp)}
                    </TableCell>
                    <TableCell>
                      {activeTab === "open"
                        ? <StatusBadge status={invStatus} />
                        : <span className="pw-badge" style={payment.status === "applied" ? { background: "var(--pw-apply-tint)", color: "var(--pw-apply)" } : { background: "var(--pw-border)", color: "var(--pw-text-secondary)" }}>
                            {payment.status === "applied" ? "Applied" : "Returned"}
                          </span>
                      }
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}

          {/* Card footer */}
          <div
            className="flex items-center justify-between px-5 py-3 border-t"
            style={{ borderColor: "var(--pw-border)" }}
          >
            <p className="text-xs" style={{ color: "var(--pw-text-muted)" }}>
              Showing {filteredRows.length} of {tabRows.length} {activeTab === "open" ? "open" : "closed"} case{tabRows.length !== 1 ? "s" : ""}
            </p>
            <div className="flex gap-2">
              <button
                onClick={() => setShowSlaReport(true)}
                className="rounded-md px-3 py-1.5 text-xs font-medium border"
                style={{
                  borderColor: "var(--pw-border)",
                  color: "var(--pw-text-secondary)",
                  background: "var(--pw-surface)",
                }}
              >
                View SLA Report
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Status bar */}
      {/* ── SLA Report modal ── */}
      {showSlaReport && (() => {
        const slaBreached   = openRows.filter(r => r.invStatus === "sla_breached")
        const pendingOut    = openRows.filter(r => r.invStatus === "pending_outreach")
        const highRisk      = openRows.filter(r => r.riskLevel === "high")
        const mediumRisk    = openRows.filter(r => r.riskLevel === "medium")
        const resolvedCount = closedRows.length
        const generated     = new Date().toLocaleString("en-US", { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit", hour12: true })
        return (
          <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.45)", zIndex: 200, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <div style={{ background: "var(--pw-surface)", borderRadius: 12, width: "100%", maxWidth: 560, boxShadow: "var(--pw-shadow-md)", overflow: "hidden" }}>
              {/* Header */}
              <div style={{ padding: "18px 24px", borderBottom: "1px solid var(--pw-border)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                <div>
                  <p style={{ fontSize: 15, fontWeight: 700, fontFamily: "var(--pw-font-display)", color: "var(--pw-text-primary)", margin: 0 }}>SLA Report — Sample</p>
                  <p style={{ fontSize: 11, color: "var(--pw-text-muted)", margin: "3px 0 0" }}>Generated {generated}</p>
                </div>
                <button onClick={() => setShowSlaReport(false)} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--pw-text-muted)", fontSize: 18, lineHeight: 1 }} aria-label="Close">✕</button>
              </div>
              {/* Metric grid */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 1, background: "var(--pw-border)", borderBottom: "1px solid var(--pw-border)" }}>
                {[
                  { label: "Open Cases",       value: openRows.length,    color: "var(--pw-text-primary)" },
                  { label: "SLA Breached",      value: slaBreached.length, color: "var(--pw-escalate)"    },
                  { label: "Pending Outreach",  value: pendingOut.length,  color: "var(--pw-hold)"        },
                  { label: "High Risk",         value: highRisk.length,    color: "var(--pw-escalate)"    },
                  { label: "Medium Risk",       value: mediumRisk.length,  color: "var(--pw-hold)"        },
                  { label: "Resolved (closed)", value: resolvedCount,      color: "var(--pw-apply)"       },
                ].map(({ label, value, color }) => (
                  <div key={label} style={{ background: "var(--pw-surface)", padding: "16px 20px" }}>
                    <p style={{ fontSize: 11, color: "var(--pw-text-muted)", margin: "0 0 4px", fontWeight: 600, textTransform: "uppercase", letterSpacing: "0.05em" }}>{label}</p>
                    <p style={{ fontSize: 22, fontWeight: 700, color, margin: 0 }}>{value}</p>
                  </div>
                ))}
              </div>
              {/* SLA breached case list */}
              <div style={{ padding: "16px 24px" }}>
                <p style={{ fontSize: 12, fontWeight: 600, color: "var(--pw-text-secondary)", margin: "0 0 10px", textTransform: "uppercase", letterSpacing: "0.05em" }}>SLA Breached Cases</p>
                {slaBreached.length === 0 ? (
                  <p style={{ fontSize: 13, color: "var(--pw-text-muted)", margin: 0 }}>No SLA breaches — all cases within deadline.</p>
                ) : (
                  <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
                    <thead>
                      <tr style={{ borderBottom: "1px solid var(--pw-border)" }}>
                        {["Payment ID", "Sender", "Amount", "Escalated"].map(h => (
                          <th key={h} style={{ padding: "6px 10px", textAlign: "left", fontWeight: 600, color: "var(--pw-text-muted)", fontSize: 10, textTransform: "uppercase", letterSpacing: "0.05em" }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {slaBreached.slice(0, 5).map(r => (
                        <tr key={r.payment.payment_id} style={{ borderBottom: "1px solid var(--pw-border)" }}>
                          <td style={{ padding: "8px 10px", fontFamily: "var(--pw-font-mono)", color: "var(--pw-text-secondary)" }}>{r.payment.payment_id}</td>
                          <td style={{ padding: "8px 10px" }}>{r.payment.sender_name}</td>
                          <td style={{ padding: "8px 10px", fontFamily: "var(--pw-font-mono)" }}>{formatUSD(r.payment.amount)}</td>
                          <td style={{ padding: "8px 10px", color: "var(--pw-text-muted)" }}>{formatTimeSince(r.payment.created_timestamp)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
              {/* Footer */}
              <div style={{ padding: "12px 24px", borderTop: "1px solid var(--pw-border)", display: "flex", justifyContent: "flex-end" }}>
                <button onClick={() => setShowSlaReport(false)} style={{ background: "var(--pw-primary)", color: "#fff", border: "none", borderRadius: 8, padding: "7px 18px", fontSize: 13, fontWeight: 600, cursor: "pointer" }}>Close</button>
              </div>
            </div>
          </div>
        )
      })()}

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
          <span>Last sync: 2 minutes ago</span>
        </div>
        <span>
          Press{" "}
          <kbd className="rounded px-1 py-0.5 text-[10px]" style={{ background: "var(--pw-surface-elevated)" }}>
            ?
          </kbd>{" "}
          for keyboard shortcuts
        </span>
      </footer>
    </div>
  )
}
