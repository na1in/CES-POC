"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import {
  Bell, Settings as SettingsIcon, ChevronDown,
  BarChart2, TrendingUp, Activity, AlertTriangle,
} from "lucide-react"
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from "recharts"
import { getAnalyticsDecisions, type AnalyticsDecisions } from "@/lib/api"
import { useAuth } from "@/contexts/auth"

// ── Constants ─────────────────────────────────────────────────────────────────

const TABS = [
  { key: "all",        label: "All" },
  { key: "scenario_1", label: "Scenario 1" },
  { key: "scenario_2", label: "Scenario 2" },
  { key: "scenario_3", label: "Scenario 3" },
  { key: "scenario_4", label: "Scenario 4" },
  { key: "scenario_5", label: "Scenario 5" },
] as const

type TabKey = (typeof TABS)[number]["key"]

const PIE_COLORS: Record<string, string> = {
  "AI Autonomous":   "#10B981",
  "Human Confirmed": "#7C4DFF",
  "Human Override":  "#F59E0B",
}

const DECISION_COLORS: Record<string, string> = {
  "APPLY":    "#10B981",
  "HOLD":     "#F59E0B",
  "ESCALATE": "#EF4444",
}

// ── Sub-components ────────────────────────────────────────────────────────────

function StatTile({ label, value, icon, iconColor, iconBg }: {
  label: string
  value: string | number
  icon: React.ReactNode
  iconColor: string
  iconBg: string
}) {
  return (
    <div className="pw-card" style={{ padding: "16px 20px", flex: 1 }}>
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between" }}>
        <div>
          <p style={{ fontSize: 11, fontWeight: 600, color: "var(--pw-text-secondary)", margin: "0 0 6px", textTransform: "uppercase", letterSpacing: "0.05em" }}>
            {label}
          </p>
          <p style={{ fontSize: 24, fontWeight: 700, fontFamily: "var(--pw-font-display)", color: "var(--pw-text-primary)", margin: 0 }}>
            {value}
          </p>
        </div>
        <div style={{
          width: 36, height: 36, borderRadius: 8,
          background: iconBg, display: "flex", alignItems: "center",
          justifyContent: "center", color: iconColor, flexShrink: 0,
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
      <p style={{ fontSize: 13, fontWeight: 600, color: "var(--pw-text-primary)", margin: "0 0 16px", fontFamily: "var(--pw-font-display)" }}>
        {title}
      </p>
      {children}
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AdminDashboardPage() {
  const router = useRouter()
  const { user, logout } = useAuth()
  const [roleMenuOpen, setRoleMenuOpen] = useState(false)
  const [activeTab, setActiveTab] = useState<TabKey>("all")
  const [data, setData] = useState<AnalyticsDecisions | null>(null)

  useEffect(() => {
    getAnalyticsDecisions().then(setData).catch(console.error)
  }, [])

  const tooltipStyle = { border: "1px solid var(--pw-border)", borderRadius: 8, fontSize: 12 }
  const axisTickStyle = { fontSize: 11, fill: "var(--pw-text-muted)" }

  // Build scenario-specific stats
  const scenarioData = data?.by_scenario ?? []
  const activeScenario = activeTab === "all"
    ? null
    : scenarioData.find(s => s.scenario_route === activeTab) ?? null

  const volume = activeTab === "all"
    ? (data?.summary.total_processed ?? 0)
    : (activeScenario?.volume ?? 0)

  const avgConf = activeTab === "all"
    ? (scenarioData.length > 0
        ? Math.round(scenarioData.reduce((a, s) => a + s.avg_confidence, 0) / scenarioData.length)
        : 0)
    : Math.round(activeScenario?.avg_confidence ?? 0)

  const overrideCount = activeTab === "all"
    ? (data?.summary.human_overrides ?? 0)
    : (activeScenario?.override_count ?? 0)

  // Decision distribution pie data
  const pieData = activeTab === "all"
    ? [
        { label: "AI Autonomous",   value: data?.summary.auto_applied ?? 0 },
        { label: "Human Confirmed", value: data?.summary.applied_human_review ?? 0 },
        { label: "Human Override",  value: data?.summary.human_overrides ?? 0 },
      ].filter(d => d.value > 0)
    : [
        { label: "AI Autonomous",   value: activeScenario?.ai_autonomous ?? 0 },
        { label: "Human Confirmed", value: activeScenario?.human_confirmed ?? 0 },
        { label: "Human Override",  value: activeScenario?.human_override ?? 0 },
      ].filter(d => d.value > 0)

  // Decision outcome bar data
  const outcomeData = activeTab === "all"
    ? scenarioData.map(s => ({
        scenario: s.scenario_route?.replace("scenario_", "S") ?? s.scenario_route,
        APPLY:    s.apply_count,
        HOLD:     s.hold_count,
        ESCALATE: s.escalate_count,
      }))
    : activeScenario
      ? [{ scenario: activeTab.replace("scenario_", "S"), APPLY: activeScenario.apply_count, HOLD: activeScenario.hold_count, ESCALATE: activeScenario.escalate_count }]
      : []

  // Confidence histogram
  const histData = data
    ? Object.entries(data.confidence_histogram).map(([bucket, count]) => ({ bucket, count }))
    : []

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
          <BarChart2 size={18} color="var(--pw-primary)" />
          <h1 style={{ fontSize: 20, fontWeight: 700, fontFamily: "var(--pw-font-display)", color: "var(--pw-text-primary)", margin: 0 }}>
            Admin Dashboard
          </h1>
          <button
            onClick={() => router.push("/admin/overrides")}
            style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 6, background: "var(--pw-bg)", border: "1px solid var(--pw-border)", borderRadius: 8, padding: "6px 14px", fontSize: 13, fontWeight: 500, color: "var(--pw-text-secondary)", cursor: "pointer" }}
          >
            Override Analysis
          </button>
          <button
            onClick={() => router.push("/admin/config")}
            style={{ display: "flex", alignItems: "center", gap: 6, background: "var(--pw-primary)", color: "#fff", border: "none", borderRadius: 8, padding: "6px 14px", fontSize: 13, fontWeight: 600, cursor: "pointer" }}
          >
            Config Management
          </button>
        </div>
        <p style={{ fontSize: 13, color: "var(--pw-text-secondary)", margin: "4px 0 0" }}>
          Per-scenario AI performance analytics and threshold tuning signals.
        </p>
      </div>

      {/* Scenario tabs */}
      <div style={{ background: "var(--pw-surface)", borderBottom: "1px solid var(--pw-border)", padding: "0 24px", display: "flex", gap: 0 }}>
        {TABS.map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            aria-selected={activeTab === tab.key}
            style={{
              padding: "12px 16px", fontSize: 13, fontWeight: activeTab === tab.key ? 600 : 400,
              color: activeTab === tab.key ? "var(--pw-primary)" : "var(--pw-text-secondary)",
              background: "none", border: "none", cursor: "pointer",
              borderBottom: activeTab === tab.key ? "2px solid var(--pw-primary)" : "2px solid transparent",
              marginBottom: -1, transition: "color 0.1s",
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Body */}
      <div style={{ flex: 1, padding: "24px", width: "100%", boxSizing: "border-box" }}>

        {/* Summary tiles */}
        <div style={{ display: "flex", gap: 12, marginBottom: 24 }}>
          <StatTile
            label="Volume"
            value={volume.toLocaleString()}
            icon={<Activity size={18} />}
            iconColor="var(--pw-primary)"
            iconBg="rgba(124,77,255,0.1)"
          />
          <StatTile
            label="Avg Confidence"
            value={`${avgConf}%`}
            icon={<TrendingUp size={18} />}
            iconColor="var(--pw-apply)"
            iconBg="var(--pw-apply-tint)"
          />
          <StatTile
            label="Override Count"
            value={overrideCount}
            icon={<AlertTriangle size={18} />}
            iconColor="#EF4444"
            iconBg="rgba(239,68,68,0.1)"
          />
        </div>

        {/* Charts 2×2 */}
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>

          {/* 1 — Decision outcomes by scenario */}
          <ChartCard title={activeTab === "all" ? "Decision Outcomes by Scenario" : "Decision Outcomes"}>
            {volume === 0 ? (
              <div style={{ height: 200, display: "flex", alignItems: "center", justifyContent: "center" }}>
                <span style={{ fontSize: 13, color: "var(--pw-text-muted)" }}>No data for this scenario</span>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={outcomeData} barCategoryGap="35%">
                  <XAxis dataKey="scenario" tick={axisTickStyle} axisLine={false} tickLine={false} />
                  <YAxis tick={axisTickStyle} axisLine={false} tickLine={false} width={30} />
                  <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "var(--pw-bg)" }} />
                  {["APPLY", "HOLD", "ESCALATE"].map(k => (
                    <Bar key={k} dataKey={k} name={k} fill={DECISION_COLORS[k]} radius={[4, 4, 0, 0]} stackId="a" />
                  ))}
                </BarChart>
              </ResponsiveContainer>
            )}
          </ChartCard>

          {/* 2 — Decision distribution pie */}
          <ChartCard title="Decision Attribution">
            {volume === 0 ? (
              <div style={{ height: 200, display: "flex", alignItems: "center", justifyContent: "center" }}>
                <span style={{ fontSize: 13, color: "var(--pw-text-muted)" }}>No data for this scenario</span>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={pieData}
                    dataKey="value"
                    nameKey="label"
                    cx="50%" cy="50%"
                    outerRadius={70}
                    label={({ percent }) => `${Math.round((percent ?? 0) * 100)}%`}
                    labelLine={false}
                  >
                    {pieData.map(entry => (
                      <Cell key={entry.label} fill={PIE_COLORS[entry.label] ?? "#94A3B8"} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={tooltipStyle} />
                  <Legend
                    iconType="circle" iconSize={8}
                    formatter={(value) => <span style={{ fontSize: 11, color: "var(--pw-text-secondary)" }}>{value}</span>}
                  />
                </PieChart>
              </ResponsiveContainer>
            )}
          </ChartCard>

          {/* 3 — Scenario volume comparison (all) or placeholder */}
          <ChartCard title="Volume by Scenario">
            {scenarioData.length === 0 ? (
              <div style={{ height: 200, display: "flex", alignItems: "center", justifyContent: "center" }}>
                <span style={{ fontSize: 13, color: "var(--pw-text-muted)" }}>No data</span>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={200}>
                <BarChart
                  data={scenarioData.map(s => ({
                    scenario: s.scenario_route?.replace("scenario_", "S") ?? s.scenario_route,
                    volume: s.volume,
                  }))}
                  barCategoryGap="35%"
                >
                  <XAxis dataKey="scenario" tick={axisTickStyle} axisLine={false} tickLine={false} />
                  <YAxis tick={axisTickStyle} axisLine={false} tickLine={false} width={30} />
                  <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "var(--pw-bg)" }} />
                  <Bar dataKey="volume" name="VOLUME" fill="#7C4DFF" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </ChartCard>

          {/* 4 — Confidence histogram */}
          <ChartCard title="Confidence Score Distribution">
            {histData.length === 0 ? (
              <div style={{ height: 200, display: "flex", alignItems: "center", justifyContent: "center" }}>
                <span style={{ fontSize: 13, color: "var(--pw-text-muted)" }}>No data</span>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={histData} barCategoryGap="20%">
                  <XAxis dataKey="bucket" tick={axisTickStyle} axisLine={false} tickLine={false} />
                  <YAxis tick={axisTickStyle} axisLine={false} tickLine={false} width={30} />
                  <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "var(--pw-bg)" }} />
                  <Bar dataKey="count" name="PAYMENTS" fill="#7C4DFF" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
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
