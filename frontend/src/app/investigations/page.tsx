"use client"

import { useRouter } from "next/navigation"
import { Search, Bell, Settings, Clock, AlertTriangle, CheckCircle2, Search as SearchIcon } from "lucide-react"
import {
  Table, TableBody, TableCell, TableHead, TableHeader, TableRow,
} from "@/components/ui/table"
import { mockPayments, mockPaymentSignals, mockRecommendations, mockAuditLogs } from "@/mocks/payments"
import type { Payment } from "@/types/payment"
import type { AuditLogEntry } from "@/types/user"

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

function getRiskLevel(paymentId: string): RiskLevel {
  const signals = mockPaymentSignals[paymentId]
  if (!signals) return "medium"
  if (signals.risk.has_risk_flags) return "high"
  return signals.risk.payment_method_risk_level
}

function getInvestigationStatus(payment: Payment, logs: AuditLogEntry[]): InvestigationStatus {
  if (payment.sla_breached) return "sla_breached"
  if (payment.status === "pending_sender_response") return "pending_outreach"
  if (logs.some(l => l.action_type === "contact_logged")) return "pending_outreach"
  return "new"
}

function getEscalationEntry(logs: AuditLogEntry[]): AuditLogEntry | null {
  return [...logs].reverse().find(l => l.action_type === "escalated") ?? null
}

function getReason(paymentId: string): string {
  const signals = mockPaymentSignals[paymentId]
  const rec = mockRecommendations[paymentId]
  if (signals?.duplicate?.is_duplicate_match) return "Duplicate payment detected within 72h"
  if (rec?.scenario_route === "scenario_4") return "No matching customer found"
  if (rec?.scenario_route === "scenario_3") return "High amount variance — 20% overpayment"
  if (rec?.scenario_route === "scenario_2") return "Customer match, no policy reference"
  return rec?.reasoning[0]?.slice(0, 60) ?? "—"
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
        DO
      </div>
    </nav>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function InvestigationQueue() {
  const router = useRouter()

  const investigationPayments = mockPayments.filter(
    p => p.status === "escalated" || p.status === "pending_sender_response"
  )

  const sortedRows = investigationPayments
    .map(p => {
      const logs = mockAuditLogs[p.payment_id] ?? []
      const escalationEntry = getEscalationEntry(logs)
      const riskLevel = getRiskLevel(p.payment_id)
      const invStatus = getInvestigationStatus(p, logs)
      const reason = getReason(p.payment_id)
      return { payment: p, logs, escalationEntry, riskLevel, invStatus, reason }
    })
    .sort((a, b) => {
      const aFlagged = mockPaymentSignals[a.payment.payment_id]?.risk.has_risk_flags ?? false
      const bFlagged = mockPaymentSignals[b.payment.payment_id]?.risk.has_risk_flags ?? false
      if (aFlagged !== bFlagged) return aFlagged ? -1 : 1
      const aTime = a.escalationEntry ? new Date(a.escalationEntry.timestamp).getTime() : 0
      const bTime = b.escalationEntry ? new Date(b.escalationEntry.timestamp).getTime() : 0
      return aTime - bTime
    })

  const fraudFlaggedCount = investigationPayments.filter(
    p => mockPaymentSignals[p.payment_id]?.risk.has_risk_flags
  ).length

  const pendingOutreachCount = sortedRows.filter(r => r.invStatus === "pending_outreach").length

  return (
    <div className="min-h-screen" style={{ background: "var(--pw-bg)" }}>
      <Nav />

      <div className="px-6 py-5 space-y-5 max-w-[1400px] mx-auto">
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
          <div className="px-5 py-4 flex items-start gap-3">
            <div className="mt-0.5 rounded-full p-1.5" style={{ background: "var(--pw-info-tint)" }}>
              <SearchIcon size={14} style={{ color: "var(--pw-info)" }} />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--pw-text-secondary)" }}>
                Open Investigations
              </p>
              <p className="mt-1 text-3xl font-bold" style={{ color: "var(--pw-text-primary)" }}>
                {investigationPayments.length}
              </p>
            </div>
          </div>

          <div className="px-5 py-4 flex items-start gap-3">
            <div className="mt-0.5 rounded-full p-1.5" style={{ background: "var(--pw-escalate-tint)" }}>
              <AlertTriangle size={14} style={{ color: "var(--pw-escalate)" }} />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--pw-text-secondary)" }}>
                Fraud Flagged
              </p>
              <p className="mt-1 text-3xl font-bold" style={{ color: "var(--pw-text-primary)" }}>
                {fraudFlaggedCount}
              </p>
            </div>
          </div>

          <div className="px-5 py-4 flex items-start gap-3">
            <div className="mt-0.5 rounded-full p-1.5" style={{ background: "var(--pw-hold-tint)" }}>
              <Clock size={14} style={{ color: "var(--pw-hold)" }} />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--pw-text-secondary)" }}>
                Pending Outreach
              </p>
              <p className="mt-1 text-3xl font-bold" style={{ color: "var(--pw-text-primary)" }}>
                {pendingOutreachCount}
              </p>
            </div>
          </div>

          <div className="px-5 py-4 flex items-start gap-3">
            <div className="mt-0.5 rounded-full p-1.5" style={{ background: "var(--pw-apply-tint)" }}>
              <CheckCircle2 size={14} style={{ color: "var(--pw-apply)" }} />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--pw-text-secondary)" }}>
                Cases Closed Today
              </p>
              <p className="mt-1 text-3xl font-bold" style={{ color: "var(--pw-text-primary)" }}>
                0
              </p>
            </div>
          </div>
        </div>

        {/* Table card */}
        <div className="pw-card overflow-hidden">
          {/* Card header */}
          <div
            className="flex items-center justify-between px-5 py-3 border-b"
            style={{ borderColor: "var(--pw-border)" }}
          >
            <div>
              <h2 className="text-sm font-semibold" style={{ color: "var(--pw-text-primary)" }}>
                Escalated Cases
              </h2>
              <p className="text-xs" style={{ color: "var(--pw-text-muted)" }}>
                Sorted by risk level (highest first)
              </p>
            </div>
            {/* Decorative filter dropdowns */}
            <div className="flex items-center gap-2">
              {["All Risk Levels", "All Ages", "All Statuses"].map(label => (
                <select
                  key={label}
                  className="rounded-md px-3 py-1.5 text-xs border"
                  style={{
                    borderColor: "var(--pw-border)",
                    color: "var(--pw-text-secondary)",
                    background: "var(--pw-surface)",
                  }}
                  aria-label={label}
                >
                  <option>{label}</option>
                </select>
              ))}
            </div>
          </div>

          {/* Table / Empty state */}
          {sortedRows.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-20 text-center">
              <p style={{ color: "var(--pw-text-secondary)" }}>No escalated cases.</p>
              <a
                href="/"
                className="mt-2 text-sm underline underline-offset-2"
                style={{ color: "var(--pw-primary)" }}
              >
                Back to Queue Dashboard
              </a>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow style={{ borderColor: "var(--pw-border)" }}>
                  {["CASE ID", "SENDER", "AMOUNT", "RISK LEVEL", "REASON", "ESCALATED BY", "AGE", "STATUS"].map(h => (
                    <TableHead
                      key={h}
                      style={{ color: "var(--pw-text-secondary)", fontSize: 11 }}
                    >
                      {h}
                    </TableHead>
                  ))}
                </TableRow>
              </TableHeader>
              <TableBody>
                {sortedRows.map(({ payment, escalationEntry, riskLevel, invStatus, reason }) => (
                  <TableRow
                    key={payment.payment_id}
                    className="cursor-pointer"
                    style={{
                      borderColor: "var(--pw-border)",
                      background: invStatus === "sla_breached" ? "rgba(239,68,68,0.06)" : undefined,
                    }}
                    onClick={() => router.push(`/payments/${payment.payment_id}`)}
                  >
                    {/* Case ID */}
                    <TableCell>
                      <span
                        className="text-xs font-medium"
                        style={{ fontFamily: "var(--pw-font-mono)", color: "var(--pw-primary)" }}
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

                    {/* Risk level */}
                    <TableCell>
                      <RiskLevelBadge level={riskLevel} />
                    </TableCell>

                    {/* Reason */}
                    <TableCell
                      className="text-sm max-w-[220px] truncate"
                      style={{ color: "var(--pw-text-secondary)" }}
                      title={reason}
                    >
                      {reason}
                    </TableCell>

                    {/* Escalated by */}
                    <TableCell>
                      {escalationEntry ? (
                        <div>
                          <p className="text-sm font-medium" style={{ color: "var(--pw-text-primary)" }}>
                            {escalationEntry.actor === "system" ? "AI System" : escalationEntry.actor}
                          </p>
                          <p className="text-xs" style={{ color: "var(--pw-text-muted)" }}>
                            {formatEscalationDate(escalationEntry.timestamp)}
                          </p>
                        </div>
                      ) : (
                        <span style={{ color: "var(--pw-text-muted)" }}>—</span>
                      )}
                    </TableCell>

                    {/* Age */}
                    <TableCell className="text-sm font-medium" style={{ color: "var(--pw-text-secondary)" }}>
                      {escalationEntry ? formatTimeSince(escalationEntry.timestamp) : "—"}
                    </TableCell>

                    {/* Status */}
                    <TableCell>
                      <StatusBadge status={invStatus} />
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
              Showing {sortedRows.length} escalated case{sortedRows.length !== 1 ? "s" : ""}
            </p>
            <div className="flex gap-2">
              <button
                className="rounded-md px-3 py-1.5 text-xs font-medium border"
                style={{
                  borderColor: "var(--pw-border)",
                  color: "var(--pw-text-secondary)",
                  background: "var(--pw-surface)",
                }}
              >
                View SLA Report
              </button>
              <button
                className="rounded-md px-3 py-1.5 text-xs font-semibold text-white"
                style={{ background: "var(--pw-primary)" }}
              >
                Export Case List
              </button>
            </div>
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
          <span>User: Damien Okafor</span>
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
