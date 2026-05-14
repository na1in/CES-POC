"use client"

import { useState, useEffect, useCallback } from "react"
import { useRouter } from "next/navigation"
import {
  Bell, Settings as SettingsIcon, ChevronDown, ChevronLeft, TrendingUp,
} from "lucide-react"
import { getOverrides, type OverrideRow } from "@/lib/api"
import { useAuth } from "@/contexts/auth"

// ── Constants ─────────────────────────────────────────────────────────────────

const SCENARIO_OPTIONS = [
  { value: "",           label: "All" },
  { value: "scenario_1", label: "Scenario 1" },
  { value: "scenario_2", label: "Scenario 2" },
  { value: "scenario_3", label: "Scenario 3" },
  { value: "scenario_4", label: "Scenario 4" },
  { value: "scenario_5", label: "Scenario 5" },
]

const BAND_OPTIONS = [
  { value: "",      label: "All" },
  { value: "0-25",  label: "Low <25" },
  { value: "25-50", label: "Medium 25–50" },
  { value: "50-75", label: "High 50–75" },
  { value: "75-100",label: "Very High >75" },
]

const REC_COLORS: Record<string, { bg: string; color: string }> = {
  APPLY:    { bg: "var(--pw-apply-tint)",    color: "var(--pw-apply)"    },
  HOLD:     { bg: "var(--pw-hold-tint)",     color: "var(--pw-hold)"     },
  ESCALATE: { bg: "var(--pw-escalate-tint)", color: "var(--pw-escalate)" },
}

function RecBadge({ rec }: { rec: string | null }) {
  if (!rec) return <span style={{ color: "var(--pw-text-muted)", fontSize: 12 }}>—</span>
  const { bg, color } = REC_COLORS[rec] ?? { bg: "var(--pw-bg)", color: "var(--pw-text-secondary)" }
  return (
    <span style={{
      display: "inline-flex", alignItems: "center",
      background: bg, color, borderRadius: 4,
      padding: "2px 8px", fontSize: 11, fontWeight: 700, letterSpacing: "0.04em",
    }}>
      {rec}
    </span>
  )
}

function OverrideReasonCell({ reason }: { reason: string | null }) {
  const [expanded, setExpanded] = useState(false)
  if (!reason) return <span style={{ color: "var(--pw-text-muted)", fontSize: 12 }}>—</span>
  const truncated = reason.length > 80
  const display = expanded || !truncated ? reason : reason.slice(0, 80) + "…"
  return (
    <span style={{ fontSize: 12, color: "var(--pw-text-secondary)" }}>
      {display}
      {truncated && (
        <button
          onClick={() => setExpanded(e => !e)}
          aria-label={expanded ? "Collapse reason" : "Expand reason"}
          style={{ marginLeft: 4, fontSize: 11, color: "var(--pw-primary)", background: "none", border: "none", cursor: "pointer", padding: 0, fontWeight: 600 }}
        >
          {expanded ? "less" : "more"}
        </button>
      )}
    </span>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function OverrideAnalysisPage() {
  const router = useRouter()
  const { user, logout } = useAuth()
  const [roleMenuOpen, setRoleMenuOpen] = useState(false)

  const [scenario, setScenario] = useState("")
  const [band, setBand] = useState("")
  const [dateFrom, setDateFrom] = useState("")
  const [dateTo, setDateTo] = useState("")

  const [overrides, setOverrides] = useState<OverrideRow[]>([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)

  const load = useCallback(() => {
    setLoading(true)
    getOverrides({
      scenario: scenario || undefined,
      confidence_band: band || undefined,
      from_date: dateFrom || undefined,
      to_date: dateTo || undefined,
      page_size: 200,
    })
      .then(res => { setOverrides(res.overrides); setTotal(res.total) })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [scenario, band, dateFrom, dateTo])

  useEffect(() => { load() }, [load])

  const selectStyle: React.CSSProperties = {
    border: "1px solid var(--pw-border)", borderRadius: 8,
    padding: "6px 10px", fontSize: 13, color: "var(--pw-text-primary)",
    background: "var(--pw-surface)", outline: "none", cursor: "pointer",
  }
  const inputStyle: React.CSSProperties = { ...selectStyle, cursor: "text" }

  const TH: React.CSSProperties = {
    padding: "10px 14px", fontSize: 11, fontWeight: 600,
    color: "var(--pw-text-secondary)", textTransform: "uppercase",
    letterSpacing: "0.05em", textAlign: "left", borderBottom: "1px solid var(--pw-border)",
    background: "var(--pw-bg)", whiteSpace: "nowrap",
  }
  const TD: React.CSSProperties = {
    padding: "12px 14px", fontSize: 13, color: "var(--pw-text-primary)",
    borderBottom: "1px solid var(--pw-border)", verticalAlign: "top",
  }

  return (
    <div style={{ minHeight: "100vh", background: "var(--pw-bg)", display: "flex", flexDirection: "column" }}>

      {/* Nav */}
      <nav style={{
        height: "var(--pw-nav-height)", background: "var(--pw-surface)",
        borderBottom: "1px solid var(--pw-border)",
        display: "flex", alignItems: "center", padding: "0 20px", gap: 12,
        position: "sticky", top: 0, zIndex: 50,
      }}>
        <button
          onClick={() => router.push("/")}
          style={{ display: "flex", alignItems: "center", gap: 6, background: "none", border: "none", cursor: "pointer", marginRight: "auto" }}
        >
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
          <button
            aria-label="User menu"
            onClick={() => setRoleMenuOpen(o => !o)}
            style={{ display: "flex", alignItems: "center", gap: 6, background: "var(--pw-bg)", border: "1px solid var(--pw-border)", borderRadius: 8, padding: "4px 10px", fontSize: 12, color: "var(--pw-text-secondary)", cursor: "pointer" }}
          >
            <div style={{ width: 22, height: 22, borderRadius: "50%", background: "var(--pw-primary)", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontWeight: 700, fontSize: 10 }}>
              {user?.name.split(" ").map((w: string) => w[0]).join("").slice(0, 2) ?? "?"}
            </div>
            {user?.name.split(" ")[0] ?? "User"}
            <ChevronDown size={12} />
          </button>
          {roleMenuOpen && (
            <div style={{ position: "absolute", right: 0, top: "calc(100% + 6px)", background: "var(--pw-surface)", border: "1px solid var(--pw-border)", borderRadius: 8, boxShadow: "var(--pw-shadow-md)", zIndex: 60, minWidth: 180, overflow: "hidden" }}>
              <button
                onClick={() => { logout(); router.push("/login"); setRoleMenuOpen(false) }}
                style={{ display: "block", width: "100%", textAlign: "left", padding: "9px 14px", fontSize: 13, cursor: "pointer", background: "transparent", border: "none", color: "var(--pw-escalate)" }}
              >
                Sign out
                <span style={{ fontSize: 11, color: "var(--pw-text-muted)", marginLeft: 6 }}>({user?.role})</span>
              </button>
            </div>
          )}
        </div>
      </nav>

      {/* Page header */}
      <div style={{ background: "var(--pw-surface)", borderBottom: "1px solid var(--pw-border)", padding: "16px 24px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <button
            onClick={() => router.push("/admin")}
            style={{ display: "flex", alignItems: "center", gap: 4, background: "none", border: "none", cursor: "pointer", color: "var(--pw-text-secondary)", padding: 0 }}
            aria-label="Back to Admin"
          >
            <ChevronLeft size={16} />
          </button>
          <TrendingUp size={18} color="var(--pw-primary)" />
          <h1 style={{ fontSize: 20, fontWeight: 700, fontFamily: "var(--pw-font-display)", color: "var(--pw-text-primary)", margin: 0 }}>
            Override Analysis
          </h1>
          <span style={{ marginLeft: 8, fontSize: 13, color: "var(--pw-text-muted)" }}>
            {total} override{total !== 1 ? "s" : ""}
          </span>
        </div>
        <p style={{ fontSize: 13, color: "var(--pw-text-secondary)", margin: "4px 0 0 54px" }}>
          Analyst override patterns — primary signal for threshold tuning.
        </p>
      </div>

      {/* Body */}
      <div style={{ flex: 1, padding: "24px" }}>

        {/* Filter bar */}
        <div className="pw-card" style={{ padding: 16, marginBottom: 16, display: "flex", flexWrap: "wrap", gap: 10, alignItems: "flex-end" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <label style={{ fontSize: 11, fontWeight: 600, color: "var(--pw-text-secondary)", textTransform: "uppercase", letterSpacing: "0.04em" }}>Scenario</label>
            <select value={scenario} onChange={e => setScenario(e.target.value)} style={selectStyle} aria-label="Filter by scenario">
              {SCENARIO_OPTIONS.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
            </select>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <label style={{ fontSize: 11, fontWeight: 600, color: "var(--pw-text-secondary)", textTransform: "uppercase", letterSpacing: "0.04em" }}>Confidence Band</label>
            <select value={band} onChange={e => setBand(e.target.value)} style={selectStyle} aria-label="Filter by confidence band">
              {BAND_OPTIONS.map(b => <option key={b.value} value={b.value}>{b.label}</option>)}
            </select>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <label style={{ fontSize: 11, fontWeight: 600, color: "var(--pw-text-secondary)", textTransform: "uppercase", letterSpacing: "0.04em" }}>Date Range</label>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} style={inputStyle} aria-label="Date from" />
              <span style={{ fontSize: 12, color: "var(--pw-text-muted)" }}>to</span>
              <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} style={inputStyle} aria-label="Date to" />
            </div>
          </div>
        </div>

        {/* Table */}
        <div className="pw-card" style={{ overflow: "hidden" }}>
          {loading ? (
            <div style={{ padding: "48px 24px", textAlign: "center" }}>
              <p style={{ fontSize: 14, color: "var(--pw-text-muted)", margin: 0 }}>Loading overrides…</p>
            </div>
          ) : overrides.length === 0 ? (
            <div style={{ padding: "48px 24px", textAlign: "center" }}>
              <p style={{ fontSize: 14, color: "var(--pw-text-muted)", margin: 0 }}>No overrides match your filters.</p>
            </div>
          ) : (
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <thead>
                  <tr>
                    <th style={TH}>Payment ID</th>
                    <th style={TH}>Scenario</th>
                    <th style={TH}>AI Rec</th>
                    <th style={TH}>Confidence</th>
                    <th style={{ ...TH, width: "28%" }}>Override Reason</th>
                    <th style={TH}>Date</th>
                    <th style={TH}>Analyst</th>
                  </tr>
                </thead>
                <tbody>
                  {overrides.map(o => (
                    <tr key={o.payment_id} style={{ background: "var(--pw-surface)" }}>
                      <td style={TD}>
                        <button
                          onClick={() => router.push(`/payments/${o.payment_id}`)}
                          style={{ color: "var(--pw-primary)", fontWeight: 600, fontSize: 13, background: "none", border: "none", cursor: "pointer", padding: 0, fontFamily: "var(--pw-font-mono)" }}
                        >
                          {o.payment_id}
                        </button>
                      </td>
                      <td style={{ ...TD, color: "var(--pw-text-secondary)", whiteSpace: "nowrap", fontSize: 12 }}>
                        {o.scenario_route?.replace("scenario_", "Scenario ") ?? "—"}
                      </td>
                      <td style={TD}><RecBadge rec={o.original_recommendation} /></td>
                      <td style={TD}>
                        {o.confidence_score !== null
                          ? <span style={{ fontFamily: "var(--pw-font-mono)", fontWeight: 600, color: "var(--pw-primary)" }}>{Math.round(o.confidence_score)}%</span>
                          : <span style={{ color: "var(--pw-text-muted)" }}>—</span>
                        }
                      </td>
                      <td style={TD}><OverrideReasonCell reason={o.override_reason} /></td>
                      <td style={{ ...TD, color: "var(--pw-text-secondary)", whiteSpace: "nowrap", fontSize: 12 }}>
                        {o.overridden_at
                          ? new Date(o.overridden_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })
                          : "—"
                        }
                      </td>
                      <td style={{ ...TD, color: "var(--pw-text-secondary)", whiteSpace: "nowrap", fontSize: 12 }}>
                        {o.overridden_by ?? "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Footer */}
      <footer style={{
        height: "var(--pw-footer-height)", background: "var(--pw-surface)",
        borderTop: "1px solid var(--pw-border)", display: "flex",
        alignItems: "center", padding: "0 20px", gap: 16, fontSize: 11,
        color: "var(--pw-text-muted)", position: "sticky", bottom: 0, zIndex: 40,
      }}>
        <span style={{ color: "var(--pw-apply)", fontWeight: 600 }}>● Audit Active</span>
        <span>User: {user?.name ?? "—"}</span>
        <span>Role: {user?.role ?? "—"}</span>
        <span style={{ marginLeft: "auto" }}>
          Press{" "}
          <kbd style={{ background: "var(--pw-surface-elevated)", padding: "1px 5px", borderRadius: 3, fontFamily: "var(--pw-font-mono)" }}>?</kbd>
          {" "}for keyboard shortcuts
        </span>
      </footer>
    </div>
  )
}
