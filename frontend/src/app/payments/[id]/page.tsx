"use client"

import { useState } from "react"
import { useRouter, useParams } from "next/navigation"
import { ArrowLeft, Bell, Settings, AlertTriangle, CheckCircle2, Clock } from "lucide-react"
import {
  mockPayments,
  mockPaymentSignals,
  mockRecommendations,
  mockAuditLogs,
  mockAnnotations,
} from "@/mocks/payments"

// ── Mock policy data (keyed by policy ID) ─────────────────────────────────────

const POLICY_INFO: Record<string, {
  holder: string
  type: string
  premium: string
  next_due: string
  balance_cents: number
}> = {
  "POL-88341": {
    holder: "Riverside Medical Group",
    type: "Commercial Health Insurance",
    premium: "$2,450 Monthly",
    next_due: "2026-05-18",
    balance_cents: 0,
  },
  "POL-55209": {
    holder: "Jonathan Hartwell Associates LLC",
    type: "Professional Liability",
    premium: "$1,187 Monthly",
    next_due: "2026-05-17",
    balance_cents: 0,
  },
  "POL-44100": {
    holder: "Blue Pines Construction Inc.",
    type: "General Liability",
    premium: "$5,000 Monthly",
    next_due: "2026-05-15",
    balance_cents: 500000,
  },
  "POL-10291": {
    holder: "Summit Risk & Advisory Group",
    type: "Commercial Property",
    premium: "$10,000 Monthly",
    next_due: "2026-05-10",
    balance_cents: 1000000,
  },
  "POL-67003": {
    holder: "Lakeview Dental Partners",
    type: "Business Owners Policy",
    premium: "$950 Monthly",
    next_due: "2026-05-13",
    balance_cents: 5100,
  },
}

const PAYMENT_HISTORY: Record<string, Array<{ date: string; desc: string; amount: number }>> = {
  "POL-88341": [
    { date: "2026-03-18", desc: "ACH — Premium", amount: 245000 },
    { date: "2026-02-18", desc: "ACH — Premium", amount: 245000 },
    { date: "2026-01-18", desc: "ACH — Premium", amount: 245000 },
  ],
  "POL-55209": [
    { date: "2026-03-17", desc: "Check — Premium", amount: 118750 },
    { date: "2026-02-17", desc: "Check — Premium", amount: 118750 },
  ],
  "POL-44100": [
    { date: "2026-03-15", desc: "ACH — Premium", amount: 500000 },
    { date: "2026-02-15", desc: "ACH — Premium", amount: 500000 },
  ],
  "POL-10291": [
    { date: "2026-03-10", desc: "Wire — Premium", amount: 1000000 },
    { date: "2026-02-10", desc: "Wire — Premium", amount: 1000000 },
  ],
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatUSD(cents: number): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(cents / 100)
}

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString("en-US", {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
  })
}

function formatAuditTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  })
}

const ACTION_LABELS: Record<string, string> = {
  received: "Case Created",
  signals_computed: "Analysis Complete",
  recommendation_made: "Recommendation Made",
  held: "Payment Held",
  applied: "Payment Applied",
  escalated: "Escalated",
  sla_breached: "SLA Breached",
  contact_logged: "Contact Logged",
  annotated: "Note Added",
  approved: "Approved",
}

function auditActor(actor: string, actionType: string): string {
  if (actor === "system") {
    if (actionType === "signals_computed" || actionType === "recommendation_made") return "AI Agent"
    return "System"
  }
  return actor
}

function statusLabel(status: string): string {
  switch (status) {
    case "held": return "Open — Awaiting Decision"
    case "applied": return "Closed — Applied"
    case "escalated": return "Escalated"
    case "pending_sender_response": return "Pending Sender Response"
    case "processing_failed": return "Processing Failed"
    default: return status
  }
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function PaymentDetail() {
  const router = useRouter()
  const params = useParams()
  const rawId = params?.id
  const id = Array.isArray(rawId) ? rawId[0] : rawId

  const payment = mockPayments.find(p => p.payment_id === id)
  const signals = id ? mockPaymentSignals[id] : undefined
  const rec = id ? mockRecommendations[id] : undefined
  const logs = id ? (mockAuditLogs[id] ?? []) : []
  const annotations = id ? (mockAnnotations[id] ?? []) : []

  const [overrideOpen, setOverrideOpen] = useState(false)
  const [overrideReason, setOverrideReason] = useState("")
  const [toast, setToast] = useState<string | null>(null)

  function showToast(msg: string) {
    setToast(msg)
    setTimeout(() => setToast(null), 3000)
  }

  // ── Not found ──────────────────────────────────────────────────────────────

  if (!payment) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100vh", background: "var(--pw-bg)" }}>
        <div style={{ textAlign: "center" }}>
          <p style={{ fontSize: 18, color: "var(--pw-text-secondary)", marginBottom: 12 }}>Payment not found</p>
          <button
            onClick={() => router.push("/")}
            style={{ color: "var(--pw-primary)", fontSize: 14, background: "none", border: "none", cursor: "pointer" }}
          >
            ← Back to Queue
          </button>
        </div>
      </div>
    )
  }

  const policyId = payment.matched_policy_id
  const policy = policyId ? POLICY_INFO[policyId] : null
  const paymentHistory = policyId ? (PAYMENT_HISTORY[policyId] ?? []) : []

  const recColor =
    rec?.recommendation === "apply" ? "var(--pw-apply)" :
    rec?.recommendation === "hold" ? "var(--pw-hold)" :
    "var(--pw-escalate)"

  const recTint =
    rec?.recommendation === "apply" ? "var(--pw-apply-tint)" :
    rec?.recommendation === "hold" ? "var(--pw-hold-tint)" :
    "var(--pw-escalate-tint)"

  const recBorder =
    rec?.recommendation === "apply" ? "rgba(16,185,129,0.4)" :
    rec?.recommendation === "hold" ? "rgba(245,158,11,0.4)" :
    "rgba(239,68,68,0.4)"

  const nameSimilarity = signals?.matching.name_similarity_score ?? 0
  const variance = signals?.amount.amount_variance_pct ?? 0
  const isDuplicate = signals?.duplicate.is_duplicate_match ?? false
  const duplicateOf = signals?.duplicate.duplicate_payment_id
  const usedLLM = signals?.matching.used_llm ?? false

  return (
    <div style={{ minHeight: "100vh", background: "var(--pw-bg)", display: "flex", flexDirection: "column" }}>
      {/* Nav */}
      <nav style={{
        height: "var(--pw-nav-height)",
        background: "var(--pw-surface)",
        borderBottom: "1px solid var(--pw-border)",
        display: "flex",
        alignItems: "center",
        padding: "0 20px",
        gap: 12,
        position: "sticky",
        top: 0,
        zIndex: 50,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6, marginRight: "auto" }}>
          <div style={{
            width: 28, height: 28, background: "var(--pw-primary)", borderRadius: 6,
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <span style={{ color: "#fff", fontWeight: 700, fontSize: 13, fontFamily: "var(--pw-font-display)" }}>P</span>
          </div>
          <span style={{ fontWeight: 700, fontSize: 15, fontFamily: "var(--pw-font-display)", color: "var(--pw-text-primary)" }}>
            PayWise
          </span>
        </div>
        <div style={{
          display: "flex", alignItems: "center", gap: 6,
          background: "var(--pw-bg)", border: "1px solid var(--pw-border)",
          borderRadius: 8, padding: "5px 10px", width: 200,
        }}>
          <span style={{ fontSize: 12, color: "var(--pw-text-muted)", flex: 1 }}>Search…</span>
          <span style={{ fontSize: 10, color: "var(--pw-text-muted)", background: "var(--pw-border)", padding: "1px 4px", borderRadius: 3 }}>⌘K</span>
        </div>
        <Bell size={16} color="var(--pw-text-secondary)" style={{ cursor: "pointer" }} />
        <Settings size={16} color="var(--pw-text-secondary)" style={{ cursor: "pointer" }} />
        <div style={{
          width: 28, height: 28, borderRadius: "50%", background: "var(--pw-primary)",
          display: "flex", alignItems: "center", justifyContent: "center",
          color: "#fff", fontWeight: 700, fontSize: 11,
        }}>
          PV
        </div>
      </nav>

      {/* Page header */}
      <div style={{ background: "var(--pw-surface)", borderBottom: "1px solid var(--pw-border)", padding: "12px 24px" }}>
        <button
          onClick={() => router.back()}
          aria-label="Go back"
          style={{
            display: "flex", alignItems: "center", gap: 5,
            color: "var(--pw-text-secondary)", fontSize: 13,
            background: "none", border: "none", cursor: "pointer", marginBottom: 6, padding: 0,
          }}
        >
          <ArrowLeft size={14} />
          Back
        </button>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <h1 style={{
            fontSize: 22, fontWeight: 700, fontFamily: "var(--pw-font-display)",
            color: "var(--pw-text-primary)", margin: 0,
          }}>
            Case {payment.payment_id}
          </h1>
          {payment.sla_breached && (
            <span className="pw-badge pw-badge-escalate">SLA Breached</span>
          )}
        </div>
        <p style={{ fontSize: 12, color: "var(--pw-text-muted)", margin: "3px 0 0" }}>
          Payment received {formatDateTime(payment.created_timestamp)}
        </p>
      </div>

      {/* Body — two-column */}
      <div style={{
        display: "flex",
        gap: 20,
        flex: 1,
        padding: "20px 24px",
        maxWidth: 1200,
        width: "100%",
        boxSizing: "border-box",
      }}>
        {/* Left column */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 16, minWidth: 0 }}>

          {/* AI Recommendation banner */}
          {rec && (
            <div style={{
              background: recTint,
              border: `1px solid ${recBorder}`,
              borderRadius: 12,
              padding: "16px 20px",
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                <div style={{
                  width: 24, height: 24, borderRadius: "50%", background: recColor,
                  display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0,
                }}>
                  {rec.recommendation === "apply"
                    ? <CheckCircle2 size={13} color="#fff" />
                    : rec.recommendation === "hold"
                    ? <Clock size={13} color="#fff" />
                    : <AlertTriangle size={13} color="#fff" />}
                </div>
                <span style={{ fontWeight: 700, fontSize: 15, color: recColor, fontFamily: "var(--pw-font-display)" }}>
                  AI Recommendation: {rec.recommendation.toUpperCase()}
                </span>
              </div>
              <p style={{ fontSize: 12, color: "var(--pw-text-secondary)", margin: "2px 0 12px 32px" }}>
                Confidence Score: {rec.confidence_score}%
              </p>

              {/* First reasoning line */}
              <div style={{ margin: "0 0 14px" }}>
                <p style={{ fontSize: 10, fontWeight: 600, color: "var(--pw-text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", margin: "0 0 4px" }}>
                  REASONING
                </p>
                <p style={{ fontSize: 13, color: "var(--pw-text-primary)", margin: 0 }}>
                  {rec.reasoning[0]}
                </p>
              </div>

              {/* Signal mini-grid */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
                <div style={{ background: "rgba(255,255,255,0.65)", borderRadius: 8, padding: "10px 12px" }}>
                  <p style={{ fontSize: 10, fontWeight: 600, color: "var(--pw-text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", margin: "0 0 4px" }}>
                    BEST NAME MATCH
                  </p>
                  <p style={{ fontSize: 13, fontWeight: 600, color: "var(--pw-text-primary)", margin: 0 }}>
                    {payment.beneficiary_name ?? payment.sender_name}
                    {signals?.risk.account_status === "inactive" ? " (INACTIVE)" : ""}
                  </p>
                </div>
                <div style={{ background: "rgba(255,255,255,0.65)", borderRadius: 8, padding: "10px 12px" }}>
                  <p style={{ fontSize: 10, fontWeight: 600, color: "var(--pw-text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", margin: "0 0 4px" }}>
                    SIMILARITY SCORE
                  </p>
                  <p style={{ fontSize: 13, fontWeight: 600, color: "var(--pw-text-primary)", margin: 0 }}>
                    {nameSimilarity}%{usedLLM ? " (LLM)" : ""}
                  </p>
                </div>
                <div style={{ background: "rgba(255,255,255,0.65)", borderRadius: 8, padding: "10px 12px" }}>
                  <p style={{ fontSize: 10, fontWeight: 600, color: "var(--pw-text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", margin: "0 0 4px" }}>
                    AMOUNT CORRELATION
                  </p>
                  <p style={{ fontSize: 13, fontWeight: 600, color: "var(--pw-text-primary)", margin: 0 }}>
                    {variance === 0 ? "On target" : `${variance > 0 ? "+" : ""}${variance}% variance`}
                  </p>
                </div>
                <div style={{ background: "rgba(255,255,255,0.65)", borderRadius: 8, padding: "10px 12px" }}>
                  <p style={{ fontSize: 10, fontWeight: 600, color: "var(--pw-text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", margin: "0 0 4px" }}>
                    DUPLICATE CHECK
                  </p>
                  <p style={{ fontSize: 13, fontWeight: 600, color: "var(--pw-text-primary)", margin: 0 }}>
                    {isDuplicate && duplicateOf ? `Duplicate of ${duplicateOf}` : "No duplicates"}
                  </p>
                </div>
              </div>

              {/* Manual review required */}
              {rec.requires_human_approval && (
                <div style={{
                  marginTop: 12,
                  background: "rgba(245,158,11,0.10)",
                  border: "1px solid rgba(245,158,11,0.35)",
                  borderRadius: 6, padding: "7px 12px",
                  display: "flex", alignItems: "center", gap: 7,
                }}>
                  <AlertTriangle size={12} color="var(--pw-hold)" style={{ flexShrink: 0 }} />
                  <span style={{ fontSize: 12, color: "#92400e" }}>
                    Manual Review Required: {rec.approval_reason ?? "Confidence < 90% or risk flags detected"}
                  </span>
                </div>
              )}
            </div>
          )}

          {/* Decision Actions */}
          {payment.status === "held" && rec && (
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              <button
                onClick={() => showToast(`Payment ${payment.payment_id} marked as approved`)}
                style={{
                  background: recColor, color: "#fff", border: "none",
                  borderRadius: 8, padding: "9px 20px", fontWeight: 600, fontSize: 13,
                  cursor: "pointer", display: "flex", alignItems: "center", gap: 6,
                }}
              >
                {rec.recommendation === "apply"
                  ? <CheckCircle2 size={14} />
                  : <Clock size={14} />}
                Accept {rec.recommendation.toUpperCase()}
              </button>
              <button
                onClick={() => setOverrideOpen(true)}
                style={{
                  background: "var(--pw-text-primary)", color: "#fff", border: "none",
                  borderRadius: 8, padding: "9px 20px", fontWeight: 600, fontSize: 13,
                  cursor: "pointer",
                }}
              >
                Override Recommendation
              </button>
              <button
                onClick={() => showToast(`Payment ${payment.payment_id} escalated`)}
                style={{
                  background: "transparent", color: "var(--pw-escalate)",
                  border: "1px solid var(--pw-escalate)", borderRadius: 8,
                  padding: "9px 20px", fontWeight: 600, fontSize: 13,
                  cursor: "pointer", display: "flex", alignItems: "center", gap: 6,
                }}
              >
                <AlertTriangle size={14} />
                Escalate
              </button>
            </div>
          )}

          {payment.status === "applied" && (
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span className="pw-badge pw-badge-apply" style={{ padding: "6px 14px", fontSize: 12 }}>
                ✓ Applied — No action required
              </span>
            </div>
          )}

          {(payment.status === "escalated" || payment.status === "pending_sender_response") && (
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              <button
                onClick={() => showToast("Marked as returned to sender")}
                style={{
                  background: "var(--pw-text-primary)", color: "#fff", border: "none",
                  borderRadius: 8, padding: "9px 20px", fontWeight: 600, fontSize: 13, cursor: "pointer",
                }}
              >
                Return to Sender
              </button>
              <button
                onClick={() => setOverrideOpen(true)}
                style={{
                  background: "transparent", color: "var(--pw-primary)",
                  border: "1px solid var(--pw-primary)", borderRadius: 8,
                  padding: "9px 20px", fontWeight: 600, fontSize: 13, cursor: "pointer",
                }}
              >
                Add Investigation Note
              </button>
            </div>
          )}

          {payment.status === "processing_failed" && (
            <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
              <button
                onClick={() => showToast("Reprocess request submitted")}
                style={{
                  background: "var(--pw-hold)", color: "#fff", border: "none",
                  borderRadius: 8, padding: "9px 20px", fontWeight: 600, fontSize: 13, cursor: "pointer",
                }}
              >
                Reprocess Payment
              </button>
            </div>
          )}

          {/* Payment Information */}
          <div className="pw-card" style={{ padding: 20 }}>
            <h2 style={{
              fontSize: 15, fontWeight: 700, margin: "0 0 16px",
              color: "var(--pw-text-primary)", fontFamily: "var(--pw-font-display)",
            }}>
              Payment Information
            </h2>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px 24px" }}>
              <div>
                <p style={{ fontSize: 10, fontWeight: 600, color: "var(--pw-text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", margin: "0 0 3px" }}>SENDER NAME</p>
                <p style={{ fontSize: 14, fontWeight: 500, color: "var(--pw-text-primary)", margin: 0 }}>{payment.sender_name}</p>
              </div>
              <div>
                <p style={{ fontSize: 10, fontWeight: 600, color: "var(--pw-text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", margin: "0 0 3px" }}>AMOUNT</p>
                <p style={{ fontSize: 22, fontWeight: 700, color: "var(--pw-text-primary)", margin: 0, fontFamily: "var(--pw-font-mono)" }}>
                  {formatUSD(payment.amount)}
                </p>
              </div>
              <div>
                <p style={{ fontSize: 10, fontWeight: 600, color: "var(--pw-text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", margin: "0 0 3px" }}>PAYMENT DATE</p>
                <p style={{ fontSize: 14, color: "var(--pw-text-primary)", margin: 0 }}>{payment.payment_date.slice(0, 10)}</p>
              </div>
              <div>
                <p style={{ fontSize: 10, fontWeight: 600, color: "var(--pw-text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", margin: "0 0 3px" }}>PAYMENT METHOD</p>
                <p style={{ fontSize: 14, color: "var(--pw-text-primary)", margin: 0 }}>{payment.payment_method}</p>
              </div>
              {(payment.reference_field_1 || payment.reference_field_2) && (
                <div style={{ gridColumn: "1 / -1" }}>
                  <p style={{ fontSize: 10, fontWeight: 600, color: "var(--pw-text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", margin: "0 0 3px" }}>REFERENCE</p>
                  <p style={{ fontSize: 14, fontFamily: "var(--pw-font-mono)", color: "var(--pw-text-primary)", margin: 0 }}>
                    {[payment.reference_field_1, payment.reference_field_2].filter(Boolean).join(" / ")}
                  </p>
                </div>
              )}
              {payment.sender_account && (
                <div>
                  <p style={{ fontSize: 10, fontWeight: 600, color: "var(--pw-text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", margin: "0 0 3px" }}>ACCOUNT</p>
                  <p style={{ fontSize: 14, fontFamily: "var(--pw-font-mono)", color: "var(--pw-text-primary)", margin: 0 }}>{payment.sender_account}</p>
                </div>
              )}
            </div>
          </div>

          {/* Payment History */}
          {paymentHistory.length > 0 && (
            <div className="pw-card" style={{ padding: 20 }}>
              <h2 style={{
                fontSize: 15, fontWeight: 700, margin: "0 0 14px",
                color: "var(--pw-text-primary)", fontFamily: "var(--pw-font-display)",
              }}>
                Payment History
              </h2>
              <div style={{ display: "flex", flexDirection: "column" }}>
                {paymentHistory.map((h, i) => (
                  <div
                    key={i}
                    style={{
                      display: "flex", alignItems: "center", justifyContent: "space-between",
                      padding: "9px 0",
                      borderBottom: i < paymentHistory.length - 1 ? "1px solid var(--pw-border)" : "none",
                    }}
                  >
                    <div>
                      <p style={{ fontSize: 13, fontWeight: 500, color: "var(--pw-text-primary)", margin: 0 }}>{h.date}</p>
                      <p style={{ fontSize: 12, color: "var(--pw-text-secondary)", margin: "2px 0 0" }}>{h.desc}</p>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                      <span style={{ fontSize: 14, fontWeight: 600, fontFamily: "var(--pw-font-mono)", color: "var(--pw-text-primary)" }}>
                        {formatUSD(h.amount)}
                      </span>
                      <span className="pw-badge pw-badge-apply">Applied</span>
                    </div>
                  </div>
                ))}
              </div>
              <p style={{ fontSize: 12, color: "var(--pw-text-muted)", margin: "10px 0 0" }}>Regular payment history</p>
            </div>
          )}

          {/* Audit Trail */}
          {logs.length > 0 && (
            <div className="pw-card" style={{ padding: 20 }}>
              <h2 style={{
                fontSize: 15, fontWeight: 700, margin: "0 0 16px",
                color: "var(--pw-text-primary)", fontFamily: "var(--pw-font-display)",
              }}>
                Audit Trail
              </h2>
              <div>
                {logs.map((log, i) => (
                  <div key={log.log_id} style={{ display: "flex", gap: 12, paddingBottom: i < logs.length - 1 ? 16 : 0 }}>
                    <div style={{ display: "flex", flexDirection: "column", alignItems: "center" }}>
                      <div style={{
                        width: 10, height: 10, borderRadius: "50%", flexShrink: 0, marginTop: 3,
                        background: log.action_type === "sla_breached" ? "var(--pw-escalate)" : "var(--pw-primary)",
                      }} />
                      {i < logs.length - 1 && (
                        <div style={{ width: 1, flex: 1, background: "var(--pw-border)", marginTop: 3 }} />
                      )}
                    </div>
                    <div style={{ paddingBottom: i < logs.length - 1 ? 0 : 0 }}>
                      <p style={{ fontSize: 11, color: "var(--pw-text-muted)", margin: "0 0 2px" }}>
                        {new Date(log.timestamp).toLocaleDateString()} {formatAuditTime(log.timestamp)} — {auditActor(log.actor, log.action_type)}
                      </p>
                      <p style={{ fontSize: 13, fontWeight: 600, color: "var(--pw-text-primary)", margin: "0 0 2px" }}>
                        {ACTION_LABELS[log.action_type] ?? log.action_type}
                      </p>
                      {log.details && (
                        <p style={{ fontSize: 12, color: "var(--pw-text-secondary)", margin: 0 }}>
                          {Object.entries(log.details as Record<string, unknown>)
                            .map(([k, v]) => `${k}: ${v}`)
                            .join(", ")}
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Case Notes */}
          {annotations.length > 0 && (
            <div className="pw-card" style={{ padding: 20 }}>
              <h2 style={{
                fontSize: 15, fontWeight: 700, margin: "0 0 14px",
                color: "var(--pw-text-primary)", fontFamily: "var(--pw-font-display)",
              }}>
                Case Notes
              </h2>
              <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                {annotations.map(ann => (
                  <div key={ann.annotation_id} style={{ background: "var(--pw-bg)", borderRadius: 8, padding: "10px 14px" }}>
                    <p style={{ fontSize: 11, color: "var(--pw-text-muted)", margin: "0 0 4px" }}>
                      {formatDateTime(ann.created_at)} — {ann.author_user_id}
                    </p>
                    <p style={{ fontSize: 13, color: "var(--pw-text-primary)", margin: 0 }}>{ann.content}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right sidebar */}
        <div style={{ width: 240, flexShrink: 0, display: "flex", flexDirection: "column", gap: 14 }}>
          {/* Matched Policy */}
          <div className="pw-card" style={{ padding: 20 }}>
            <h2 style={{
              fontSize: 11, fontWeight: 700, margin: "0 0 16px",
              color: "var(--pw-text-muted)", fontFamily: "var(--pw-font-display)",
              textTransform: "uppercase", letterSpacing: "0.05em",
            }}>
              Matched Policy
            </h2>
            {policy && policyId ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
                <div>
                  <p style={{ fontSize: 10, fontWeight: 600, color: "var(--pw-text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", margin: "0 0 2px" }}>POLICY NUMBER</p>
                  <p style={{ fontSize: 14, fontFamily: "var(--pw-font-mono)", fontWeight: 600, color: "var(--pw-text-primary)", margin: 0 }}>{policyId}</p>
                </div>
                <div>
                  <p style={{ fontSize: 10, fontWeight: 600, color: "var(--pw-text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", margin: "0 0 2px" }}>POLICY HOLDER</p>
                  <p style={{ fontSize: 13, color: "var(--pw-text-primary)", margin: 0 }}>{policy.holder}</p>
                </div>
                <div>
                  <p style={{ fontSize: 10, fontWeight: 600, color: "var(--pw-text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", margin: "0 0 2px" }}>POLICY TYPE</p>
                  <p style={{ fontSize: 13, color: "var(--pw-text-primary)", margin: 0 }}>{policy.type}</p>
                </div>
                <div>
                  <p style={{ fontSize: 10, fontWeight: 600, color: "var(--pw-text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", margin: "0 0 4px" }}>STATUS</p>
                  <span className="pw-badge pw-badge-apply" style={{ fontSize: 10 }}>Active</span>
                </div>
                <div>
                  <p style={{ fontSize: 10, fontWeight: 600, color: "var(--pw-text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", margin: "0 0 2px" }}>PREMIUM</p>
                  <p style={{ fontSize: 13, color: "var(--pw-text-primary)", margin: 0 }}>{policy.premium}</p>
                </div>
                <div>
                  <p style={{ fontSize: 10, fontWeight: 600, color: "var(--pw-text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", margin: "0 0 2px" }}>NEXT DUE</p>
                  <p style={{ fontSize: 13, color: "var(--pw-text-primary)", margin: 0 }}>{policy.next_due}</p>
                </div>
                <div>
                  <p style={{ fontSize: 10, fontWeight: 600, color: "var(--pw-text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", margin: "0 0 2px" }}>CURRENT BALANCE</p>
                  <p style={{
                    fontSize: 15, fontWeight: 700, fontFamily: "var(--pw-font-mono)", margin: 0,
                    color: policy.balance_cents > 0 ? "var(--pw-escalate)" : "var(--pw-text-primary)",
                  }}>
                    {formatUSD(policy.balance_cents)}
                  </p>
                </div>
              </div>
            ) : (
              <p style={{ fontSize: 13, color: "var(--pw-text-muted)", margin: 0 }}>No matched policy</p>
            )}
          </div>

          {/* Case metadata */}
          <div className="pw-card" style={{ padding: "16px 20px" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              <div>
                <p style={{ fontSize: 10, fontWeight: 600, color: "var(--pw-text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", margin: "0 0 2px" }}>CASE ID</p>
                <p style={{ fontSize: 13, fontFamily: "var(--pw-font-mono)", color: "var(--pw-text-primary)", margin: 0 }}>{payment.payment_id}</p>
              </div>
              <div>
                <p style={{ fontSize: 10, fontWeight: 600, color: "var(--pw-text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", margin: "0 0 2px" }}>OPENED</p>
                <p style={{ fontSize: 12, color: "var(--pw-text-secondary)", margin: 0 }}>{formatDateTime(payment.created_timestamp)}</p>
              </div>
              <div>
                <p style={{ fontSize: 10, fontWeight: 600, color: "var(--pw-text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", margin: "0 0 3px" }}>STATUS</p>
                <p style={{ fontSize: 12, color: "var(--pw-text-secondary)", margin: 0 }}>{statusLabel(payment.status)}</p>
              </div>
              {rec && (
                <div>
                  <p style={{ fontSize: 10, fontWeight: 600, color: "var(--pw-text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", margin: "0 0 2px" }}>SCENARIO</p>
                  <p style={{ fontSize: 12, color: "var(--pw-text-secondary)", margin: 0 }}>
                    {rec.scenario_route.replace("_", " ")}
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Override modal */}
      {overrideOpen && (
        <div
          style={{
            position: "fixed", inset: 0, background: "rgba(0,0,0,0.4)", zIndex: 100,
            display: "flex", alignItems: "center", justifyContent: "center",
          }}
          onClick={() => setOverrideOpen(false)}
        >
          <div
            role="dialog"
            aria-label="Override Recommendation"
            style={{
              background: "var(--pw-surface)", borderRadius: 12, padding: 24, width: 420,
              boxShadow: "0 20px 40px rgba(0,0,0,0.15)",
            }}
            onClick={e => e.stopPropagation()}
          >
            <h2 style={{ fontSize: 17, fontWeight: 700, margin: "0 0 8px", fontFamily: "var(--pw-font-display)" }}>
              Override Recommendation
            </h2>
            <p style={{ fontSize: 13, color: "var(--pw-text-secondary)", margin: "0 0 16px" }}>
              Provide a reason for overriding the AI recommendation. This will be logged in the audit trail.
            </p>
            <textarea
              aria-label="Override reason"
              value={overrideReason}
              onChange={e => setOverrideReason(e.target.value)}
              placeholder="Enter reason for override…"
              rows={4}
              style={{
                width: "100%", border: "1px solid var(--pw-border)", borderRadius: 8,
                padding: "10px 12px", fontSize: 13, resize: "vertical",
                boxSizing: "border-box", fontFamily: "var(--pw-font-sans)",
                outline: "none",
              }}
            />
            <div style={{ display: "flex", gap: 10, marginTop: 16, justifyContent: "flex-end" }}>
              <button
                onClick={() => { setOverrideOpen(false); setOverrideReason("") }}
                style={{
                  background: "none", border: "1px solid var(--pw-border)", borderRadius: 8,
                  padding: "8px 18px", fontSize: 13, cursor: "pointer",
                }}
              >
                Cancel
              </button>
              <button
                disabled={overrideReason.trim().length === 0}
                onClick={() => {
                  showToast("Override recorded")
                  setOverrideOpen(false)
                  setOverrideReason("")
                }}
                style={{
                  background: overrideReason.trim() ? "var(--pw-primary)" : "var(--pw-text-muted)",
                  color: "#fff", border: "none", borderRadius: 8,
                  padding: "8px 18px", fontSize: 13, fontWeight: 600,
                  cursor: overrideReason.trim() ? "pointer" : "not-allowed",
                }}
              >
                Submit Override
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div
          role="status"
          style={{
            position: "fixed", bottom: 48, right: 24,
            background: "var(--pw-text-primary)", color: "#fff",
            padding: "10px 20px", borderRadius: 8, fontSize: 13, fontWeight: 500,
            zIndex: 200, boxShadow: "0 4px 12px rgba(0,0,0,0.2)",
          }}
        >
          {toast}
        </div>
      )}

      {/* Footer */}
      <footer style={{
        height: "var(--pw-footer-height)", background: "var(--pw-surface)",
        borderTop: "1px solid var(--pw-border)", display: "flex",
        alignItems: "center", padding: "0 20px", gap: 16, fontSize: 11,
        color: "var(--pw-text-muted)", position: "sticky", bottom: 0, zIndex: 40,
      }}>
        <span style={{ color: "var(--pw-apply)", fontWeight: 600 }}>● Audit Active</span>
        <span>User: Priya Venkataraman</span>
        <span>Last sync: 2 minutes ago</span>
        <span style={{ marginLeft: "auto" }}>
          Press{" "}
          <kbd style={{ background: "var(--pw-surface-elevated)", padding: "1px 5px", borderRadius: 3, fontFamily: "var(--pw-font-mono)" }}>?</kbd>
          {" "}for keyboard shortcuts
        </span>
      </footer>
    </div>
  )
}
