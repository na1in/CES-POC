"use client"

import { useState, useEffect, useCallback } from "react"
import { useRouter } from "next/navigation"
import {
  Bell, Settings as SettingsIcon, ChevronDown, ChevronRight,
  AlertTriangle, Activity, Shield, X,
} from "lucide-react"
import {
  listPayments, getAnomalies, getChangeRequests, approveChangeRequest, rejectChangeRequest,
  type PaymentRow, type AnomalyFlag, type ChangeRequest,
} from "@/lib/api"
import { useAuth } from "@/contexts/auth"

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatUSD(cents: number): string {
  return (cents / 100).toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 0 })
}

function timeSince(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const days = Math.floor(diff / 86_400_000)
  const hours = Math.floor((diff % 86_400_000) / 3_600_000)
  if (days > 0) return `${days}d ${hours}h ago`
  return `${hours}h ago`
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
}

// ── Collapsible section ───────────────────────────────────────────────────────

function SectionCard({ title, count, icon, accentColor, children, defaultOpen = true }: {
  title: string; count: number; icon: React.ReactNode
  accentColor: string; children: React.ReactNode; defaultOpen?: boolean
}) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="pw-card" style={{ marginBottom: 16, overflow: "hidden" }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{ width: "100%", display: "flex", alignItems: "center", gap: 10, padding: "14px 20px", background: "none", border: "none", cursor: "pointer", borderBottom: open ? "1px solid var(--pw-border)" : "none" }}
      >
        <span style={{ color: accentColor }}>{icon}</span>
        <span style={{ fontSize: 14, fontWeight: 700, color: "var(--pw-text-primary)", fontFamily: "var(--pw-font-display)", flex: 1, textAlign: "left" }}>{title}</span>
        <span style={{
          fontSize: 11, fontWeight: 700, padding: "2px 8px", borderRadius: 9999,
          background: count === 0 ? "var(--pw-surface-elevated)" : `rgba(${accentColor === "var(--pw-escalate)" ? "239,68,68" : "245,158,11"},0.1)`,
          color: count === 0 ? "var(--pw-text-muted)" : accentColor,
        }}>
          {count}
        </span>
        {open ? <ChevronDown size={16} color="var(--pw-text-muted)" /> : <ChevronRight size={16} color="var(--pw-text-muted)" />}
      </button>
      {open && <div>{children}</div>}
    </div>
  )
}

// ── Anomaly status chip ───────────────────────────────────────────────────────

function AnomalyStatusChip({ status }: { status: string }) {
  const map: Record<string, { label: string; cls: string }> = {
    open:          { label: "Open",          cls: "pw-badge pw-badge-escalate" },
    investigating: { label: "Investigating", cls: "pw-badge pw-badge-hold" },
    resolved:      { label: "Resolved",      cls: "pw-badge pw-badge-apply" },
  }
  const { label, cls } = map[status] ?? { label: status, cls: "pw-badge pw-badge-neutral" }
  return <span className={cls}>{label}</span>
}

// ── Reject modal ──────────────────────────────────────────────────────────────

function RejectModal({ request, onConfirm, onClose }: {
  request: ChangeRequest; onConfirm: (comment: string) => void; onClose: () => void
}) {
  const [comment, setComment] = useState("")
  const invalid = comment.trim().length === 0
  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)", zIndex: 100, display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div className="pw-card" style={{ width: 480, padding: "24px", position: "relative" }}>
        <button onClick={onClose} style={{ position: "absolute", top: 16, right: 16, background: "none", border: "none", cursor: "pointer", color: "var(--pw-text-muted)" }} aria-label="Close modal">
          <X size={18} />
        </button>
        <h2 style={{ fontSize: 16, fontWeight: 700, fontFamily: "var(--pw-font-display)", color: "var(--pw-text-primary)", margin: "0 0 6px" }}>Reject Change Request</h2>
        <p style={{ fontSize: 13, color: "var(--pw-text-secondary)", margin: "0 0 16px" }}>
          Rejecting <span style={{ fontFamily: "var(--pw-font-mono)", fontSize: 12, background: "var(--pw-surface-elevated)", padding: "1px 5px", borderRadius: 4 }}>{request.parameter_name}</span>{" "}
          → <strong>{request.proposed_value}</strong> proposed by {request.proposed_by}.
        </p>
        <label style={{ fontSize: 12, fontWeight: 600, color: "var(--pw-text-secondary)", display: "block", marginBottom: 6 }}>
          Review comment <span style={{ color: "var(--pw-escalate)" }}>*</span>
        </label>
        <textarea
          value={comment} onChange={e => setComment(e.target.value)}
          placeholder="Explain the reason for rejection…" rows={4}
          style={{ width: "100%", boxSizing: "border-box", border: `1px solid ${invalid && comment.length > 0 ? "var(--pw-escalate)" : "var(--pw-border)"}`, borderRadius: 8, padding: "8px 12px", fontSize: 13, color: "var(--pw-text-primary)", resize: "vertical", outline: "none" }}
          aria-label="Review comment"
        />
        <div style={{ display: "flex", gap: 8, marginTop: 16, justifyContent: "flex-end" }}>
          <button onClick={onClose} style={{ padding: "7px 16px", borderRadius: 8, fontSize: 13, border: "1px solid var(--pw-border)", background: "none", color: "var(--pw-text-secondary)", cursor: "pointer" }}>Cancel</button>
          <button
            onClick={() => !invalid && onConfirm(comment)} disabled={invalid}
            style={{ padding: "7px 16px", borderRadius: 8, fontSize: 13, fontWeight: 600, border: "1px solid var(--pw-escalate)", background: invalid ? "var(--pw-surface-elevated)" : "transparent", color: invalid ? "var(--pw-text-muted)" : "var(--pw-escalate)", cursor: invalid ? "not-allowed" : "pointer" }}
          >
            Confirm Reject
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Table helpers ─────────────────────────────────────────────────────────────

function TH({ children }: { children: React.ReactNode }) {
  return (
    <th style={{ padding: "9px 16px", fontSize: 10, fontWeight: 700, color: "var(--pw-text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", textAlign: "left", whiteSpace: "nowrap" }}>
      {children}
    </th>
  )
}

function TD({ children, style }: { children: React.ReactNode; style?: React.CSSProperties }) {
  return (
    <td style={{ padding: "12px 16px", fontSize: 13, color: "var(--pw-text-primary)", verticalAlign: "middle", ...style }}>
      {children}
    </td>
  )
}

function EmptyState({ message }: { message: string }) {
  return <div style={{ padding: "32px 20px", textAlign: "center", color: "var(--pw-text-muted)", fontSize: 13 }}>{message}</div>
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ExceptionDashboardPage() {
  const router = useRouter()
  const { user, logout } = useAuth()
  const [roleMenuOpen, setRoleMenuOpen] = useState(false)

  const [slaPayments, setSlaPayments] = useState<PaymentRow[]>([])
  const [anomalies, setAnomalies] = useState<AnomalyFlag[]>([])
  const [expandedAnomaly, setExpandedAnomaly] = useState<number | null>(null)
  const [changeRequests, setChangeRequests] = useState<ChangeRequest[]>([])
  const [rejectTarget, setRejectTarget] = useState<ChangeRequest | null>(null)

  const reload = useCallback(() => {
    listPayments({ page_size: 200 })
      .then(r => setSlaPayments(r.payments.filter(p => p.sla_breached)))
      .catch(console.error)
    getAnomalies()
      .then(r => setAnomalies(r.anomalies))
      .catch(console.error)
    getChangeRequests()
      .then(r => setChangeRequests(r.change_requests.filter(r => r.status === "pending")))
      .catch(console.error)
  }, [])

  useEffect(() => { reload() }, [reload])

  async function handleApprove(changeId: number) {
    await approveChangeRequest(changeId).catch(console.error)
    reload()
  }

  async function handleRejectConfirm(changeId: number, comment: string) {
    await rejectChangeRequest(changeId, comment).catch(console.error)
    setRejectTarget(null)
    reload()
  }

  return (
    <div style={{ minHeight: "100vh", background: "var(--pw-bg)", display: "flex", flexDirection: "column" }}>

      {/* Nav */}
      <nav style={{ height: "var(--pw-nav-height)", background: "var(--pw-surface)", borderBottom: "1px solid var(--pw-border)", display: "flex", alignItems: "center", padding: "0 20px", gap: 12, position: "sticky", top: 0, zIndex: 50 }}>
        <button onClick={() => router.push("/")} style={{ display: "flex", alignItems: "center", gap: 6, background: "none", border: "none", cursor: "pointer", marginRight: "auto" }}>
          <div style={{ width: 28, height: 28, background: "var(--pw-primary)", borderRadius: 6, display: "flex", alignItems: "center", justifyContent: "center" }}>
            <span style={{ color: "#fff", fontWeight: 700, fontSize: 13, fontFamily: "var(--pw-font-display)" }}>P</span>
          </div>
          <span style={{ fontWeight: 700, fontSize: 15, fontFamily: "var(--pw-font-display)", color: "var(--pw-text-primary)" }}>PayWise</span>
        </button>
        <div style={{ display: "flex", alignItems: "center", gap: 6, background: "var(--pw-bg)", border: "1px solid var(--pw-border)", borderRadius: 8, padding: "5px 10px", width: 200 }}>
          <span style={{ fontSize: 12, color: "var(--pw-text-muted)", flex: 1 }}>Search…</span>
          <span style={{ fontSize: 10, color: "var(--pw-text-muted)", background: "var(--pw-border)", padding: "1px 4px", borderRadius: 3 }}>⌘K</span>
        </div>
        <Bell size={16} color="var(--pw-text-secondary)" style={{ cursor: "pointer" }} />
        <SettingsIcon size={16} color="var(--pw-text-secondary)" style={{ cursor: "pointer" }} onClick={() => router.push("/settings")} />
        <div style={{ position: "relative" }}>
          <button aria-label="User menu" onClick={() => setRoleMenuOpen(o => !o)} style={{ display: "flex", alignItems: "center", gap: 6, background: "var(--pw-bg)", border: "1px solid var(--pw-border)", borderRadius: 8, padding: "4px 10px", fontSize: 12, color: "var(--pw-text-secondary)", cursor: "pointer" }}>
            <div style={{ width: 22, height: 22, borderRadius: "50%", background: "var(--pw-primary)", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontWeight: 700, fontSize: 10 }}>
              {user?.name.split(" ").map((w: string) => w[0]).join("").slice(0, 2) ?? "?"}
            </div>
            {user?.name.split(" ")[0] ?? "User"}
            <ChevronDown size={12} />
          </button>
          {roleMenuOpen && (
            <div style={{ position: "absolute", right: 0, top: "calc(100% + 6px)", background: "var(--pw-surface)", border: "1px solid var(--pw-border)", borderRadius: 8, boxShadow: "var(--pw-shadow-md)", zIndex: 60, minWidth: 180, overflow: "hidden" }}>
              <button onClick={() => { logout(); router.push("/login"); setRoleMenuOpen(false) }} style={{ display: "block", width: "100%", textAlign: "left", padding: "9px 14px", fontSize: 13, cursor: "pointer", background: "transparent", border: "none", color: "var(--pw-escalate)" }}>
                Sign out <span style={{ fontSize: 11, color: "var(--pw-text-muted)", marginLeft: 6 }}>({user?.role})</span>
              </button>
            </div>
          )}
        </div>
      </nav>

      {/* Page header */}
      <div style={{ background: "var(--pw-surface)", borderBottom: "1px solid var(--pw-border)", padding: "16px 24px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <AlertTriangle size={18} color="var(--pw-escalate)" />
          <h1 style={{ fontSize: 20, fontWeight: 700, fontFamily: "var(--pw-font-display)", color: "var(--pw-text-primary)", margin: 0 }}>Exception Dashboard</h1>
        </div>
        <p style={{ fontSize: 13, color: "var(--pw-text-secondary)", margin: "4px 0 0" }}>
          SLA breaches, anomaly flags, and config changes awaiting approval.
        </p>
      </div>

      {/* Body */}
      <div style={{ flex: 1, padding: "24px", maxWidth: 1120, width: "100%", boxSizing: "border-box" }}>

        {/* ── Section 1: SLA Breached Cases ── */}
        <SectionCard title="SLA Breached Cases" count={slaPayments.length} icon={<AlertTriangle size={16} />} accentColor="var(--pw-escalate)">
          {slaPayments.length === 0 ? (
            <EmptyState message="No SLA breaches — all escalations resolved within deadline." />
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ background: "var(--pw-bg)", borderBottom: "1px solid var(--pw-border)" }}>
                  <TH>Payment ID</TH><TH>Sender</TH><TH>Amount</TH><TH>Scenario</TH><TH>Due Since</TH>
                </tr>
              </thead>
              <tbody>
                {slaPayments.map((p, i) => (
                  <tr
                    key={p.payment_id}
                    style={{ background: "rgba(239,68,68,0.06)", borderBottom: i < slaPayments.length - 1 ? "1px solid var(--pw-border)" : "none", cursor: "pointer" }}
                    onClick={() => router.push(`/payments/${p.payment_id}`)}
                  >
                    <TD><span style={{ fontFamily: "var(--pw-font-mono)", fontSize: 12 }}>{p.payment_id}</span></TD>
                    <TD>{p.sender_name}</TD>
                    <TD><span style={{ fontFamily: "var(--pw-font-mono)", fontSize: 12 }}>{formatUSD(p.amount)}</span></TD>
                    <TD><span className="pw-badge pw-badge-neutral">{p.scenario_route?.replace("scenario_", "S") ?? "—"}</span></TD>
                    <TD style={{ color: "var(--pw-escalate)", fontWeight: 600 }}>
                      {p.investigation_due_date ? timeSince(p.investigation_due_date) : "—"}
                    </TD>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </SectionCard>

        {/* ── Section 2: Anomaly Flags ── */}
        <SectionCard title="Anomaly Flags" count={anomalies.filter(a => a.status !== "resolved").length} icon={<Activity size={16} />} accentColor="var(--pw-hold)">
          {anomalies.length === 0 ? (
            <EmptyState message="No anomaly flags for this period." />
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ background: "var(--pw-bg)", borderBottom: "1px solid var(--pw-border)" }}>
                  <TH>Metric</TH><TH>Description</TH><TH>Period</TH><TH>Flagged By</TH><TH>Status</TH><TH>Details</TH>
                </tr>
              </thead>
              <tbody>
                {anomalies.map((a, i) => (
                  <>
                    <tr key={a.flag_id} style={{ borderBottom: "1px solid var(--pw-border)" }}>
                      <TD><span style={{ fontWeight: 600 }}>{a.metric_name}</span></TD>
                      <TD style={{ color: "var(--pw-text-secondary)", maxWidth: 320 }}>{a.description}</TD>
                      <TD style={{ color: "var(--pw-text-muted)", whiteSpace: "nowrap" }}>
                        {formatDate(a.period_start)} – {formatDate(a.period_end)}
                      </TD>
                      <TD style={{ color: "var(--pw-text-secondary)" }}>{a.flagged_by}</TD>
                      <TD><AnomalyStatusChip status={a.status} /></TD>
                      <TD>
                        <button
                          onClick={() => setExpandedAnomaly(expandedAnomaly === a.flag_id ? null : a.flag_id)}
                          aria-label={`View details for ${a.metric_name}`}
                          style={{ fontSize: 12, color: "var(--pw-primary)", background: "none", border: "none", cursor: "pointer", fontWeight: 500, padding: 0 }}
                        >
                          {expandedAnomaly === a.flag_id ? "Hide" : "View Details"}
                        </button>
                      </TD>
                    </tr>
                    {expandedAnomaly === a.flag_id && (
                      <tr key={`${a.flag_id}-detail`} style={{ borderBottom: i < anomalies.length - 1 ? "1px solid var(--pw-border)" : "none" }}>
                        <td colSpan={6} style={{ padding: "12px 16px", background: "var(--pw-bg)" }}>
                          <p style={{ fontSize: 12, fontWeight: 600, color: "var(--pw-text-secondary)", margin: "0 0 4px" }}>Resolution Notes</p>
                          <p style={{ fontSize: 13, color: "var(--pw-text-primary)", margin: 0 }}>
                            {a.resolution_notes ?? <span style={{ color: "var(--pw-text-muted)" }}>No resolution notes yet.</span>}
                          </p>
                        </td>
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>
          )}
        </SectionCard>

        {/* ── Section 3: Config Changes Pending Approval ── */}
        <SectionCard title="Config Changes Pending Approval" count={changeRequests.length} icon={<Shield size={16} />} accentColor="var(--pw-hold)">
          {changeRequests.length === 0 ? (
            <EmptyState message="No config changes pending approval." />
          ) : (
            <table style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ background: "var(--pw-bg)", borderBottom: "1px solid var(--pw-border)" }}>
                  <TH>Parameter</TH><TH>Current Value</TH><TH>Proposed Value</TH><TH>Proposed By</TH><TH>Date</TH><TH>Actions</TH>
                </tr>
              </thead>
              <tbody>
                {changeRequests.map((r, i) => (
                  <tr key={r.change_id} style={{ borderBottom: i < changeRequests.length - 1 ? "1px solid var(--pw-border)" : "none" }}>
                    <TD>
                      <span style={{ fontFamily: "var(--pw-font-mono)", fontSize: 12, background: "var(--pw-surface-elevated)", padding: "2px 6px", borderRadius: 4 }}>
                        {r.parameter_name}
                      </span>
                    </TD>
                    <TD style={{ fontFamily: "var(--pw-font-mono)", fontSize: 13, color: "var(--pw-text-muted)" }}>{r.current_value}</TD>
                    <TD style={{ fontFamily: "var(--pw-font-mono)", fontSize: 13, fontWeight: 700, color: "var(--pw-primary)" }}>{r.proposed_value}</TD>
                    <TD style={{ color: "var(--pw-text-secondary)" }}>{r.proposed_by}</TD>
                    <TD style={{ color: "var(--pw-text-muted)", whiteSpace: "nowrap" }}>{formatDate(r.proposed_at)}</TD>
                    <TD>
                      <div style={{ display: "flex", gap: 8 }}>
                        <button
                          onClick={() => handleApprove(r.change_id)}
                          aria-label={`Approve ${r.parameter_name}`}
                          style={{ padding: "5px 12px", borderRadius: 6, fontSize: 12, fontWeight: 600, background: "var(--pw-apply-tint)", color: "var(--pw-apply)", border: "1px solid var(--pw-apply)", cursor: "pointer" }}
                        >
                          Approve
                        </button>
                        <button
                          onClick={() => setRejectTarget(r)}
                          aria-label={`Reject ${r.parameter_name}`}
                          style={{ padding: "5px 12px", borderRadius: 6, fontSize: 12, fontWeight: 600, background: "transparent", color: "var(--pw-escalate)", border: "1px solid var(--pw-escalate)", cursor: "pointer" }}
                        >
                          Reject
                        </button>
                      </div>
                    </TD>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </SectionCard>

      </div>

      {rejectTarget && (
        <RejectModal
          request={rejectTarget}
          onConfirm={(comment) => handleRejectConfirm(rejectTarget.change_id, comment)}
          onClose={() => setRejectTarget(null)}
        />
      )}

      {/* Footer */}
      <footer style={{ height: "var(--pw-footer-height)", background: "var(--pw-surface)", borderTop: "1px solid var(--pw-border)", display: "flex", alignItems: "center", padding: "0 20px", gap: 16, fontSize: 11, color: "var(--pw-text-muted)", position: "sticky", bottom: 0, zIndex: 40 }}>
        <span style={{ color: "var(--pw-apply)", fontWeight: 600 }}>● Audit Active</span>
        <span>User: {user?.name ?? "—"}</span>
        <span>Role: {user?.role ?? "—"}</span>
        <span style={{ marginLeft: "auto" }}>
          Press <kbd style={{ background: "var(--pw-surface-elevated)", padding: "1px 5px", borderRadius: 3, fontFamily: "var(--pw-font-mono)" }}>?</kbd> for keyboard shortcuts
        </span>
      </footer>
    </div>
  )
}
