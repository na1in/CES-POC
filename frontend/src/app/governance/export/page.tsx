"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import {
  Bell, Settings as SettingsIcon, ChevronDown,
  Download, FileText, ChevronLeft,
} from "lucide-react"
import { getGovernanceExport } from "@/lib/api"
import { useAuth } from "@/contexts/auth"

// ── Constants ─────────────────────────────────────────────────────────────────

const SCOPE_OPTIONS = [
  { key: "decisions"     as const, label: "Decisions",      description: "All payment decisions with AI reasoning and attribution" },
  { key: "overrides"     as const, label: "Override Log",   description: "Human overrides with reason codes and timestamps" },
  { key: "config_changes"as const, label: "Config Changes", description: "Threshold change requests and deployment history" },
]

type ScopeKey = (typeof SCOPE_OPTIONS)[number]["key"]

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ComplianceExportPage() {
  const router = useRouter()
  const { user, logout } = useAuth()
  const [roleMenuOpen, setRoleMenuOpen] = useState(false)
  const today = new Date()
  const fiveDaysAgo = new Date(today)
  fiveDaysAgo.setDate(today.getDate() - 5)
  const fmt = (d: Date) => d.toISOString().slice(0, 10)
  const [dateFrom, setDateFrom] = useState(fmt(fiveDaysAgo))
  const [dateTo, setDateTo] = useState(fmt(today))
  const [selectedScope, setSelectedScope] = useState<Set<ScopeKey>>(new Set())
  const [downloading, setDownloading] = useState(false)
  const [exportError, setExportError] = useState<string | null>(null)

  const formComplete = Boolean(dateFrom && dateTo && selectedScope.size > 0)

  function toggleScope(key: ScopeKey) {
    setSelectedScope(prev => {
      const next = new Set(prev)
      next.has(key) ? next.delete(key) : next.add(key)
      return next
    })
  }

  function selectAll() {
    setSelectedScope(new Set(SCOPE_OPTIONS.map(o => o.key)))
  }

  async function handleDownload() {
    if (!formComplete || downloading) return
    setDownloading(true)
    setExportError(null)
    try {
      const scopes = [...selectedScope]
      const scope = scopes.length === SCOPE_OPTIONS.length ? "all" : scopes[0]
      const data = await getGovernanceExport({ from_date: dateFrom, to_date: dateTo, scope })
      const json = JSON.stringify(data, null, 2)
      const blob = new Blob([json], { type: "application/json" })
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `ces-compliance-${dateFrom}-to-${dateTo}.json`
      a.click()
      URL.revokeObjectURL(url)
    } catch (e: unknown) {
      setExportError(e instanceof Error ? e.message : "Export failed.")
    } finally {
      setDownloading(false)
    }
  }

  const inputStyle: React.CSSProperties = {
    border: "1px solid var(--pw-border)", borderRadius: 8,
    padding: "7px 10px", fontSize: 13, color: "var(--pw-text-primary)",
    background: "var(--pw-surface)", outline: "none", flex: 1,
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
          <button onClick={() => router.push("/governance")} style={{ display: "flex", alignItems: "center", gap: 4, background: "none", border: "none", cursor: "pointer", color: "var(--pw-text-secondary)", padding: 0 }} aria-label="Back to Governance">
            <ChevronLeft size={16} />
          </button>
          <FileText size={18} color="var(--pw-primary)" />
          <h1 style={{ fontSize: 20, fontWeight: 700, fontFamily: "var(--pw-font-display)", color: "var(--pw-text-primary)", margin: 0 }}>Compliance Export</h1>
        </div>
        <p style={{ fontSize: 13, color: "var(--pw-text-secondary)", margin: "4px 0 0 54px" }}>
          Download an audit-ready report for any date range and scope.
        </p>
      </div>

      {/* Body */}
      <div style={{ flex: 1, padding: "32px 24px", display: "flex", justifyContent: "center" }}>
        <div style={{ width: "100%", maxWidth: 560 }}>

          <div className="pw-card" style={{ padding: "24px 28px" }}>

            {/* Date range */}
            <div style={{ marginBottom: 24 }}>
              <label style={{ fontSize: 12, fontWeight: 600, color: "var(--pw-text-secondary)", display: "block", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.04em" }}>Date Range</label>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} style={inputStyle} aria-label="Date from" />
                <span style={{ fontSize: 12, color: "var(--pw-text-muted)", flexShrink: 0 }}>to</span>
                <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} style={inputStyle} aria-label="Date to" />
              </div>
            </div>

            {/* Scope */}
            <div style={{ marginBottom: 28 }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
                <label style={{ fontSize: 12, fontWeight: 600, color: "var(--pw-text-secondary)", textTransform: "uppercase", letterSpacing: "0.04em" }}>Export Scope</label>
                <button onClick={selectAll} style={{ fontSize: 12, color: "var(--pw-primary)", background: "none", border: "none", cursor: "pointer", fontWeight: 600, padding: 0 }}>Select All</button>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {SCOPE_OPTIONS.map(opt => {
                  const checked = selectedScope.has(opt.key)
                  return (
                    <label key={opt.key} style={{ display: "flex", alignItems: "flex-start", gap: 12, cursor: "pointer", padding: "12px 14px", borderRadius: 8, border: `1px solid ${checked ? "var(--pw-primary)" : "var(--pw-border)"}`, background: checked ? "color-mix(in srgb, var(--pw-primary) 5%, transparent)" : "transparent", transition: "border-color 0.1s, background 0.1s" }}>
                      <input type="checkbox" checked={checked} onChange={() => toggleScope(opt.key)} style={{ marginTop: 2, accentColor: "var(--pw-primary)", width: 14, height: 14, flexShrink: 0 }} />
                      <div>
                        <p style={{ fontSize: 13, fontWeight: 600, color: "var(--pw-text-primary)", margin: 0 }}>{opt.label}</p>
                        <p style={{ fontSize: 12, color: "var(--pw-text-muted)", margin: "3px 0 0" }}>{opt.description}</p>
                      </div>
                    </label>
                  )
                })}
              </div>
            </div>

            {exportError && (
              <p style={{ fontSize: 12, color: "var(--pw-escalate)", margin: "0 0 12px" }} role="alert">{exportError}</p>
            )}

            <button
              onClick={handleDownload}
              disabled={!formComplete || downloading}
              style={{ width: "100%", display: "flex", alignItems: "center", justifyContent: "center", gap: 8, background: "var(--pw-primary)", color: "#fff", border: "none", borderRadius: 8, padding: "11px 20px", fontSize: 14, fontWeight: 600, cursor: formComplete && !downloading ? "pointer" : "not-allowed", opacity: formComplete && !downloading ? 1 : 0.5, transition: "opacity 0.15s" }}
            >
              <Download size={15} />
              {downloading ? "Generating…" : "Download Report"}
            </button>
          </div>

          <p style={{ fontSize: 11, color: "var(--pw-text-muted)", marginTop: 10, textAlign: "center" }}>
            Report is exported as JSON. Requires director role.
          </p>
        </div>
      </div>

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
