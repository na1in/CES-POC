"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import {
  Bell, Settings as SettingsIcon, ChevronDown,
  Download, FileText, ChevronLeft,
} from "lucide-react"
import { mockGovernanceReviews } from "@/mocks/governance"
import { mockUsers } from "@/mocks/thresholds"
import type { UserRole } from "@/types/user"

// ── Constants ─────────────────────────────────────────────────────────────────

const SCOPE_OPTIONS = [
  {
    key: "decisions" as const,
    label: "Decisions",
    description: "All payment decisions with AI reasoning and attribution",
  },
  {
    key: "override_log" as const,
    label: "Override Log",
    description: "Human overrides with reason codes and timestamps",
  },
  {
    key: "config_changes" as const,
    label: "Config Changes",
    description: "Threshold change requests and deployment history",
  },
]

type ScopeKey = (typeof SCOPE_OPTIONS)[number]["key"]

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ComplianceExportPage() {
  const router = useRouter()
  const [activeRole, setActiveRole] = useState<UserRole>("director")
  const [roleMenuOpen, setRoleMenuOpen] = useState(false)
  const [dateFrom, setDateFrom] = useState("")
  const [dateTo, setDateTo] = useState("")
  const [selectedScope, setSelectedScope] = useState<Set<ScopeKey>>(new Set())
  const [downloading, setDownloading] = useState(false)

  const currentUser = mockUsers.find(u => u.role === activeRole) ?? mockUsers[0]
  const lastExport = mockGovernanceReviews[0] ?? null

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
    try {
      // In production: fetch /api/governance/export?date_from=...&date_to=...&scope=...
      // and pipe the response blob using Content-Disposition filename from headers.
      const scopeList = [...selectedScope].join(", ")
      const mockCsv = [
        "CES Compliance Export",
        `Date Range,${dateFrom},${dateTo}`,
        `Scope,${scopeList}`,
        `Generated,${new Date().toISOString()}`,
        "",
        "payment_id,decision,attribution,scenario,amount,timestamp",
        "PMT-001,APPLIED,AI_AUTO,Scenario 1,125000,2026-04-01T10:00:00Z",
        "PMT-002,HELD,AI_HOLD,Scenario 2,87500,2026-04-02T11:30:00Z",
        "PMT-003,ESCALATED,HUMAN_OVERRIDE,Scenario 3,320000,2026-04-03T09:15:00Z",
      ].join("\n")

      const blob = new Blob([mockCsv], { type: "text/csv" })
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = `ces-compliance-${dateFrom}-to-${dateTo}.csv`
      a.click()
      URL.revokeObjectURL(url)
    } finally {
      setDownloading(false)
    }
  }

  const inputStyle: React.CSSProperties = {
    border: "1px solid var(--pw-border)",
    borderRadius: 8,
    padding: "7px 10px",
    fontSize: 13,
    color: "var(--pw-text-primary)",
    background: "var(--pw-surface)",
    outline: "none",
    flex: 1,
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
              {currentUser.name.split(" ").map((w: string) => w[0]).join("").slice(0, 2)}
            </div>
            {currentUser.name.split(" ")[0]}
            <ChevronDown size={12} />
          </button>
          {roleMenuOpen && (
            <div style={{
              position: "absolute", right: 0, top: "calc(100% + 6px)",
              background: "var(--pw-surface)", border: "1px solid var(--pw-border)",
              borderRadius: 8, boxShadow: "var(--pw-shadow-md)", zIndex: 60,
              minWidth: 180, overflow: "hidden",
            }}>
              {mockUsers.map((u: { user_id: string; role: UserRole; name: string }) => (
                <button
                  key={u.user_id}
                  onClick={() => { setActiveRole(u.role); setRoleMenuOpen(false) }}
                  style={{
                    display: "block", width: "100%", textAlign: "left",
                    padding: "9px 14px", fontSize: 13, cursor: "pointer",
                    background: u.role === activeRole ? "var(--pw-bg)" : "transparent",
                    border: "none", color: "var(--pw-text-primary)",
                  }}
                >
                  {u.name}
                  <span style={{ fontSize: 11, color: "var(--pw-text-muted)", marginLeft: 6 }}>({u.role})</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </nav>

      {/* Page header */}
      <div style={{ background: "var(--pw-surface)", borderBottom: "1px solid var(--pw-border)", padding: "16px 24px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <button
            onClick={() => router.push("/governance")}
            style={{ display: "flex", alignItems: "center", gap: 4, background: "none", border: "none", cursor: "pointer", color: "var(--pw-text-secondary)", padding: 0 }}
            aria-label="Back to Governance"
          >
            <ChevronLeft size={16} />
          </button>
          <FileText size={18} color="var(--pw-primary)" />
          <h1 style={{
            fontSize: 20, fontWeight: 700, fontFamily: "var(--pw-font-display)",
            color: "var(--pw-text-primary)", margin: 0,
          }}>
            Compliance Export
          </h1>
        </div>
        <p style={{ fontSize: 13, color: "var(--pw-text-secondary)", margin: "4px 0 0 54px" }}>
          Download an audit-ready report for any date range and scope.
        </p>
      </div>

      {/* Body */}
      <div style={{ flex: 1, padding: "32px 24px", display: "flex", justifyContent: "center" }}>
        <div style={{ width: "100%", maxWidth: 560 }}>

          {/* Export form card */}
          <div className="pw-card" style={{ padding: "24px 28px" }}>

            {/* Date range */}
            <div style={{ marginBottom: 24 }}>
              <label style={{ fontSize: 12, fontWeight: 600, color: "var(--pw-text-secondary)", display: "block", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.04em" }}>
                Date Range
              </label>
              <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                <input
                  type="date"
                  value={dateFrom}
                  onChange={e => setDateFrom(e.target.value)}
                  style={inputStyle}
                  aria-label="Date from"
                />
                <span style={{ fontSize: 12, color: "var(--pw-text-muted)", flexShrink: 0 }}>to</span>
                <input
                  type="date"
                  value={dateTo}
                  onChange={e => setDateTo(e.target.value)}
                  style={inputStyle}
                  aria-label="Date to"
                />
              </div>
            </div>

            {/* Scope */}
            <div style={{ marginBottom: 28 }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
                <label style={{ fontSize: 12, fontWeight: 600, color: "var(--pw-text-secondary)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
                  Export Scope
                </label>
                <button
                  onClick={selectAll}
                  style={{
                    fontSize: 12, color: "var(--pw-primary)", background: "none",
                    border: "none", cursor: "pointer", fontWeight: 600, padding: 0,
                  }}
                >
                  Select All
                </button>
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                {SCOPE_OPTIONS.map(opt => {
                  const checked = selectedScope.has(opt.key)
                  return (
                    <label
                      key={opt.key}
                      style={{
                        display: "flex", alignItems: "flex-start", gap: 12, cursor: "pointer",
                        padding: "12px 14px", borderRadius: 8,
                        border: `1px solid ${checked ? "var(--pw-primary)" : "var(--pw-border)"}`,
                        background: checked ? "color-mix(in srgb, var(--pw-primary) 5%, transparent)" : "transparent",
                        transition: "border-color 0.1s, background 0.1s",
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={checked}
                        onChange={() => toggleScope(opt.key)}
                        style={{ marginTop: 2, accentColor: "var(--pw-primary)", width: 14, height: 14, flexShrink: 0 }}
                      />
                      <div>
                        <p style={{ fontSize: 13, fontWeight: 600, color: "var(--pw-text-primary)", margin: 0 }}>
                          {opt.label}
                        </p>
                        <p style={{ fontSize: 12, color: "var(--pw-text-muted)", margin: "3px 0 0" }}>
                          {opt.description}
                        </p>
                      </div>
                    </label>
                  )
                })}
              </div>
            </div>

            {/* Download button */}
            <button
              onClick={handleDownload}
              disabled={!formComplete || downloading}
              style={{
                width: "100%",
                display: "flex", alignItems: "center", justifyContent: "center", gap: 8,
                background: "var(--pw-primary)",
                color: "#fff",
                border: "none", borderRadius: 8,
                padding: "11px 20px",
                fontSize: 14, fontWeight: 600,
                cursor: formComplete && !downloading ? "pointer" : "not-allowed",
                opacity: formComplete && !downloading ? 1 : 0.5,
                transition: "opacity 0.15s",
              }}
            >
              <Download size={15} />
              {downloading ? "Generating…" : "Download Report"}
            </button>
          </div>

          {/* Last export notice */}
          {lastExport && (
            <div style={{
              marginTop: 12, padding: "12px 16px",
              borderRadius: 8, border: "1px solid var(--pw-border)",
              background: "var(--pw-surface)",
              display: "flex", alignItems: "center", gap: 8,
            }}>
              <FileText size={13} color="var(--pw-text-muted)" style={{ flexShrink: 0 }} />
              <p style={{ fontSize: 12, color: "var(--pw-text-muted)", margin: 0 }}>
                Last export:{" "}
                <span style={{ color: "var(--pw-text-secondary)", fontWeight: 500 }}>{lastExport.period}</span>
                {" · "}
                {new Date(lastExport.reviewed_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                {" · "}
                {lastExport.reviewed_by}
                {" · "}
                <span style={{ fontStyle: "italic" }}>{lastExport.export_scope.join(", ")}</span>
              </p>
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
        <span>User: {currentUser.name}</span>
        <span>Role: {currentUser.role}</span>
        <span style={{ marginLeft: "auto" }}>
          Press{" "}
          <kbd style={{ background: "var(--pw-surface-elevated)", padding: "1px 5px", borderRadius: 3, fontFamily: "var(--pw-font-mono)" }}>?</kbd>
          {" "}for keyboard shortcuts
        </span>
      </footer>
    </div>
  )
}
