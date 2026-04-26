"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { Bell, Settings as SettingsIcon, Shield, ChevronDown } from "lucide-react"
import { mockThresholds, mockUsers } from "@/mocks/thresholds"
import type { UserRole } from "@/types/user"

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    year: "numeric", month: "short", day: "numeric",
  })
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function SettingsPage() {
  const router = useRouter()
  const [activeRole, setActiveRole] = useState<UserRole>("analyst")
  const [roleMenuOpen, setRoleMenuOpen] = useState(false)

  const currentUser = mockUsers.find(u => u.role === activeRole) ?? mockUsers[0]
  const isAdmin = activeRole === "admin"

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
        <SettingsIcon size={16} color="var(--pw-primary)" style={{ cursor: "pointer" }} />
        {/* Role switcher (demo) */}
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
              {currentUser.name.split(" ").map(w => w[0]).join("").slice(0, 2)}
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
              {mockUsers.map(u => (
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
                  <span style={{ fontSize: 11, color: "var(--pw-text-muted)", marginLeft: 6 }}>
                    ({u.role})
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
      </nav>

      {/* Page header */}
      <div style={{ background: "var(--pw-surface)", borderBottom: "1px solid var(--pw-border)", padding: "16px 24px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <Shield size={18} color="var(--pw-primary)" />
          <h1 style={{
            fontSize: 20, fontWeight: 700, fontFamily: "var(--pw-font-display)",
            color: "var(--pw-text-primary)", margin: 0,
          }}>
            Settings
          </h1>
        </div>
        <p style={{ fontSize: 13, color: "var(--pw-text-secondary)", margin: "4px 0 0" }}>
          Configuration thresholds that govern the payment resolution pipeline.
        </p>
      </div>

      {/* Body */}
      <div style={{ flex: 1, padding: "24px", maxWidth: 960, width: "100%", boxSizing: "border-box" }}>

        {/* Non-admin notice */}
        {!isAdmin && (
          <p
            aria-label="Admin notice"
            style={{
              fontSize: 13, color: "var(--pw-text-secondary)",
              margin: "0 0 16px",
            }}
          >
            Contact your admin to request threshold changes.
          </p>
        )}

        {/* Admin notice */}
        {isAdmin && (
          <p style={{ fontSize: 13, color: "var(--pw-text-secondary)", margin: "0 0 16px" }}>
            As an admin, you can propose changes via the{" "}
            <button
              onClick={() => router.push("/admin/config")}
              style={{ color: "var(--pw-primary)", background: "none", border: "none", cursor: "pointer", fontSize: 13, padding: 0, textDecoration: "underline" }}
            >
              Configuration Management
            </button>
            {" "}page.
          </p>
        )}

        {/* Threshold table card */}
        <div className="pw-card" style={{ overflow: "hidden" }}>
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ background: "var(--pw-bg)", borderBottom: "1px solid var(--pw-border)" }}>
                {["PARAMETER", "VALUE", "DESCRIPTION", "LAST CHANGED", ...(isAdmin ? ["ACTION"] : [])].map(col => (
                  <th
                    key={col}
                    style={{
                      padding: "10px 16px",
                      fontSize: 10, fontWeight: 700,
                      color: "var(--pw-text-muted)",
                      textTransform: "uppercase",
                      letterSpacing: "0.06em",
                      textAlign: "left",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {mockThresholds.map((t, i) => (
                <tr
                  key={t.parameter_name}
                  style={{
                    borderBottom: i < mockThresholds.length - 1 ? "1px solid var(--pw-border)" : "none",
                    background: "transparent",
                  }}
                >
                  <td style={{ padding: "12px 16px", verticalAlign: "middle" }}>
                    <span style={{
                      fontFamily: "var(--pw-font-mono)",
                      fontSize: 12,
                      color: "var(--pw-text-primary)",
                      background: "var(--pw-surface-elevated)",
                      padding: "2px 6px",
                      borderRadius: 4,
                    }}>
                      {t.parameter_name}
                    </span>
                  </td>
                  <td style={{ padding: "12px 16px", verticalAlign: "middle" }}>
                    <span style={{
                      fontFamily: "var(--pw-font-mono)",
                      fontSize: 14,
                      fontWeight: 700,
                      color: "var(--pw-primary)",
                    }}>
                      {t.parameter_value}
                    </span>
                  </td>
                  <td style={{ padding: "12px 16px", fontSize: 13, color: "var(--pw-text-secondary)", verticalAlign: "middle" }}>
                    {t.description}
                  </td>
                  <td style={{ padding: "12px 16px", fontSize: 12, color: "var(--pw-text-muted)", verticalAlign: "middle", whiteSpace: "nowrap" }}>
                    {formatDate(t.effective_date)}
                  </td>
                  {isAdmin && (
                    <td style={{ padding: "12px 16px", verticalAlign: "middle" }}>
                      <button
                        onClick={() => router.push("/admin/config")}
                        aria-label={`Propose change for ${t.parameter_name}`}
                        style={{
                          background: "none",
                          border: "1px solid var(--pw-border)",
                          borderRadius: 6,
                          padding: "4px 10px",
                          fontSize: 12,
                          color: "var(--pw-primary)",
                          cursor: "pointer",
                          fontWeight: 500,
                          whiteSpace: "nowrap",
                        }}
                      >
                        Propose Change
                      </button>
                    </td>
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p style={{ fontSize: 12, color: "var(--pw-text-muted)", marginTop: 14 }}>
          {mockThresholds.length} thresholds · Changes require admin approval and are versioned in the audit log.
        </p>
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
