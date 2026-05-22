"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import {
  Bell, Settings as SettingsIcon, ChevronDown,
  CheckCircle2, Clock, AlertTriangle, Users, TrendingUp, BarChart2,
} from "lucide-react"
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line, CartesianGrid,
} from "recharts"
import { getAnalyticsDecisions, type AnalyticsDecisions } from "@/lib/api"
import { useAuth } from "@/contexts/auth"

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatUSD(cents: number): string {
  return (cents / 100).toLocaleString("en-US", { style: "currency", currency: "USD", minimumFractionDigits: 0 })
}

// ── Sub-components ────────────────────────────────────────────────────────────

interface StatCardProps {
  label: string
  value: string | number
  sub?: string
  icon: React.ReactNode
  iconColor: string
  iconBg: string
}

function StatCard({ label, value, sub, icon, iconColor, iconBg }: StatCardProps) {
  return (
    <div className="pw-card" style={{ padding: "16px 20px", flex: 1, minWidth: 140 }}>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
        <div>
          <p style={{ fontSize: 12, color: "var(--pw-text-secondary)", margin: "0 0 6px", fontWeight: 500 }}>{label}</p>
          <p style={{
            fontSize: 24, fontWeight: 700,
            fontFamily: "var(--pw-font-display)",
            color: "var(--pw-text-primary)", margin: 0,
          }}>{value}</p>
          {sub && (
            <p style={{ fontSize: 12, color: "var(--pw-text-muted)", margin: "4px 0 0" }}>{sub}</p>
          )}
        </div>
        <div style={{
          width: 36, height: 36, borderRadius: 8,
          background: iconBg, display: "flex", alignItems: "center", justifyContent: "center",
          color: iconColor, flexShrink: 0,
        }}>
          {icon}
        </div>
      </div>
    </div>
  )
}

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="pw-card" style={{ padding: "20px 24px" }}>
      <p style={{
        fontSize: 13, fontWeight: 600, color: "var(--pw-text-primary)",
        margin: "0 0 16px", fontFamily: "var(--pw-font-display)",
      }}>{title}</p>
      {children}
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

const EMPTY_ANALYTICS: AnalyticsDecisions = {
  summary: {
    auto_applied: 0, applied_human_review: 0, applied_human_override: 0,
    held_pending_review: 0, escalated_by_ai: 0, escalated_by_human: 0,
    human_overrides: 0, returned: 0, total_processed: 0, override_rate_pct: 0,
  },
  by_scenario: [],
  by_payment_method: [],
  confidence_histogram: {},
}

export default function GovernancePage() {
  const router = useRouter()
  const { user, logout } = useAuth()
  const [roleMenuOpen, setRoleMenuOpen] = useState(false)
  const today = new Date()
  const fiveDaysAgo = new Date(today)
  fiveDaysAgo.setDate(today.getDate() - 5)
  const fmt = (d: Date) => d.toISOString().slice(0, 10)
  const [dateFrom, setDateFrom] = useState(fmt(fiveDaysAgo))
  const [dateTo, setDateTo] = useState(fmt(today))
  const [analytics, setAnalytics] = useState<AnalyticsDecisions>(EMPTY_ANALYTICS)

  useEffect(() => {
    getAnalyticsDecisions({ from_date: dateFrom || undefined, to_date: dateTo || undefined })
      .then(setAnalytics)
      .catch(console.error)
  }, [dateFrom, dateTo])

  const { summary, by_payment_method, confidence_histogram } = analytics

  const inputStyle: React.CSSProperties = {
    border: "1px solid var(--pw-border)",
    borderRadius: 8,
    padding: "5px 10px",
    fontSize: 13,
    color: "var(--pw-text-primary)",
    background: "var(--pw-surface)",
    outline: "none",
  }

  return (
    <div style={{ minHeight: "100vh", background: "var(--pw-bg)", display: "flex", flexDirection: "column" }}>

      {/* Nav */}
      <nav style={{
        height: "var(--pw-nav-height)",
        background: "var(--pw-surface)",
        borderBottom: "1px solid var(--pw-border)",
        display: "flex", alignItems: "center",
        padding: "0 20px", gap: 12,
        position: "sticky", top: 0, zIndex: 50,
      }}>
        <button
          onClick={() => router.push("/")}
          style={{ display: "flex", alignItems: "center", gap: 6, background: "none", border: "none", cursor: "pointer", marginRight: "auto" }}
        >
          <div style={{
            width: 28, height: 28, background: "var(--pw-primary)", borderRadius: 6,
            display: "flex", alignItems: "center", justifyContent: "center",
          }}>
            <span style={{ color: "#fff", fontWeight: 700, fontSize: 13, fontFamily: "var(--pw-font-display)" }}>P</span>
          </div>
          <span style={{ fontWeight: 700, fontSize: 15, fontFamily: "var(--pw-font-display)", color: "var(--pw-text-primary)" }}>
            PayWise
          </span>
        </button>
        <div style={{
          display: "flex", alignItems: "center", gap: 6,
          background: "var(--pw-bg)", border: "1px solid var(--pw-border)",
          borderRadius: 8, padding: "5px 10px", width: 200,
        }}>
          <span style={{ fontSize: 12, color: "var(--pw-text-muted)", flex: 1 }}>Search…</span>
          <span style={{ fontSize: 10, color: "var(--pw-text-muted)", background: "var(--pw-border)", padding: "1px 4px", borderRadius: 3 }}>⌘K</span>
        </div>
        <Bell size={16} color="var(--pw-text-secondary)" style={{ cursor: "pointer" }} />
        <SettingsIcon
          size={16} color="var(--pw-text-secondary)" style={{ cursor: "pointer" }}
          onClick={() => router.push("/settings")}
        />
        {/* Role switcher */}
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
              {user?.name.split(" ").map((w: string) => w[0]).join("").slice(0, 2) ?? "?"}
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

      {/* Page header */}
      <div style={{ background: "var(--pw-surface)", borderBottom: "1px solid var(--pw-border)", padding: "16px 24px" }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <BarChart2 size={18} color="var(--pw-primary)" />
            <h1 style={{
              fontSize: 20, fontWeight: 700, fontFamily: "var(--pw-font-display)",
              color: "var(--pw-text-primary)", margin: 0,
            }}>
              Governance Dashboard
            </h1>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: 12, color: "var(--pw-text-secondary)" }}>Date range:</span>
            <input
              type="date"
              value={dateFrom}
              onChange={e => setDateFrom(e.target.value)}
              style={inputStyle}
              aria-label="Date from"
            />
            <span style={{ fontSize: 12, color: "var(--pw-text-muted)" }}>to</span>
            <input
              type="date"
              value={dateTo}
              onChange={e => setDateTo(e.target.value)}
              style={inputStyle}
              aria-label="Date to"
            />
            <button
              onClick={() => router.push("/governance/export")}
              style={{
                display: "flex", alignItems: "center", gap: 6,
                background: "var(--pw-primary)", color: "#fff",
                border: "none", borderRadius: 8, padding: "6px 14px",
                fontSize: 13, fontWeight: 600, cursor: "pointer",
              }}
            >
              Export Audit Report
            </button>
          </div>
        </div>
        <p style={{ fontSize: 13, color: "var(--pw-text-secondary)", margin: "4px 0 0" }}>
          Performance metrics, SLA tracking & audit exports.
        </p>
      </div>

      {/* Body */}
      <div style={{ flex: 1, padding: "24px", width: "100%", boxSizing: "border-box" }}>

        {/* ── Metric cards ── */}
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap", marginBottom: 24 }}>
          <StatCard
            label="Applied after Operator Review"
            value={summary.applied_human_review}
            icon={<Users size={18} />}
            iconColor="var(--pw-apply)"
            iconBg="var(--pw-apply-tint)"
          />
          <StatCard
            label="Held Pending Review"
            value={summary.held_pending_review}
            icon={<Clock size={18} />}
            iconColor="var(--pw-hold)"
            iconBg="var(--pw-hold-tint)"
          />
          <StatCard
            label="Escalated by AI"
            value={summary.escalated_by_ai}
            icon={<AlertTriangle size={18} />}
            iconColor="var(--pw-escalate)"
            iconBg="var(--pw-escalate-tint)"
          />
          <StatCard
            label="Escalated by Operator"
            value={summary.escalated_by_human}
            icon={<AlertTriangle size={18} />}
            iconColor="var(--pw-escalate)"
            iconBg="var(--pw-escalate-tint)"
          />
          <StatCard
            label="Operator Overrides"
            value={summary.human_overrides}
            sub={`${summary.override_rate_pct}% override rate`}
            icon={<TrendingUp size={18} />}
            iconColor="var(--pw-escalate)"
            iconBg="var(--pw-escalate-tint)"
          />
        </div>

        {/* ── Charts row 1: Payment method + SLA adherence ── */}
        <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: 16, marginBottom: 16 }}>

          <ChartCard title="Payment Method Breakdown">
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={by_payment_method} barCategoryGap="30%">
                <XAxis dataKey="payment_method" tick={{ fontSize: 12, fill: "var(--pw-text-secondary)" }} axisLine={false} tickLine={false} />
                <YAxis yAxisId="left" tick={{ fontSize: 11, fill: "var(--pw-text-muted)" }} axisLine={false} tickLine={false} width={30} />
                <Tooltip
                  contentStyle={{ border: "1px solid var(--pw-border)", borderRadius: 8, fontSize: 12 }}
                  cursor={{ fill: "var(--pw-bg)" }}
                />
                <Bar yAxisId="left" dataKey="volume" name="Count" fill="#7C4DFF" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>

          {/* SLA adherence card */}
          <div className="pw-card" style={{ padding: "20px 24px", display: "flex", flexDirection: "column", justifyContent: "center" }}>
            <p style={{ fontSize: 13, fontWeight: 600, color: "var(--pw-text-primary)", margin: "0 0 20px", fontFamily: "var(--pw-font-display)" }}>
              SLA Adherence
            </p>
            <div style={{ textAlign: "center" }}>
              <p style={{
                fontSize: 52, fontWeight: 800,
                fontFamily: "var(--pw-font-display)",
                color: "var(--pw-apply)",
                margin: 0, lineHeight: 1,
              }}>
                —
              </p>
              <p style={{ fontSize: 13, color: "var(--pw-text-secondary)", margin: "10px 0 0" }}>
                Escalations resolved before SLA breach
              </p>
              <p style={{ fontSize: 12, color: "var(--pw-text-muted)", margin: "6px 0 0" }}>
                {summary.escalated_by_ai + summary.escalated_by_human} total escalations
              </p>
            </div>
          </div>
        </div>

        {/* ── Charts row 2: Override rate trend + Confidence histogram ── */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>

          <ChartCard title="Override Rate">
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: 200 }}>
              <p style={{ fontSize: 52, fontWeight: 800, fontFamily: "var(--pw-font-display)", color: "var(--pw-primary)", margin: 0 }}>
                {summary.override_rate_pct}%
              </p>
              <p style={{ fontSize: 13, color: "var(--pw-text-secondary)", margin: "10px 0 0" }}>
                {summary.human_overrides} overrides of {summary.total_processed} total
              </p>
            </div>
          </ChartCard>

          <ChartCard title="Confidence Score Histogram">
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={Object.entries(confidence_histogram).map(([bucket, count]) => ({ bucket, count }))} barCategoryGap="20%">
                <XAxis dataKey="bucket" tick={{ fontSize: 11, fill: "var(--pw-text-secondary)" }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fontSize: 11, fill: "var(--pw-text-muted)" }} axisLine={false} tickLine={false} width={30} />
                <Tooltip
                  contentStyle={{ border: "1px solid var(--pw-border)", borderRadius: 8, fontSize: 12 }}
                  cursor={{ fill: "var(--pw-bg)" }}
                />
                <Bar dataKey="count" name="Payments" fill="#7C4DFF" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </ChartCard>

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
