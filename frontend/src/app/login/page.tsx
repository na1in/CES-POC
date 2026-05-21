"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { useAuth } from "@/contexts/auth"

const USERS = [
  { id: "USR-0001", name: "Priya Sharma",   role: "Analyst",      initials: "PS" },
  { id: "USR-0002", name: "Damien Torres",  role: "Investigator", initials: "DT" },
  { id: "USR-0003", name: "Lorraine Chen",  role: "Director",     initials: "LC" },
  { id: "USR-0004", name: "Marcus Webb",    role: "Admin",        initials: "MW" },
]

const ROLE_HOME: Record<string, string> = {
  analyst:      "/",
  investigator: "/investigations",
  director:     "/governance",
  admin:        "/admin",
}

export default function LoginPage() {
  const { login } = useAuth()
  const router = useRouter()
  const [loading, setLoading] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function handleLogin(userId: string, role: string) {
    setLoading(userId)
    setError(null)
    try {
      await login(userId)
      router.push(ROLE_HOME[role.toLowerCase()] ?? "/")
    } catch (e) {
      setError(e instanceof Error ? e.message : "Login failed")
    } finally {
      setLoading(null)
    }
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "var(--pw-bg)",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: 24,
      }}
    >
      {/* Logo */}
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 40 }}>
        <div
          style={{
            width: 40, height: 40, background: "var(--pw-primary)",
            borderRadius: 10, display: "flex", alignItems: "center",
            justifyContent: "center",
          }}
        >
          <span style={{ color: "#fff", fontWeight: 800, fontSize: 18, fontFamily: "var(--pw-font-display)" }}>P</span>
        </div>
        <span style={{ fontWeight: 700, fontSize: 22, fontFamily: "var(--pw-font-display)", color: "var(--pw-text-primary)" }}>
          PayWise
        </span>
      </div>

      <div
        className="pw-card"
        style={{ width: "100%", maxWidth: 420, padding: 32 }}
      >
        <h1 style={{
          fontSize: 20, fontWeight: 700, color: "var(--pw-text-primary)",
          fontFamily: "var(--pw-font-display)", margin: "0 0 6px",
        }}>
          Sign in
        </h1>
        <p style={{ fontSize: 13, color: "var(--pw-text-secondary)", margin: "0 0 28px" }}>
          Select your account to continue
        </p>

        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {USERS.map(u => (
            <button
              key={u.id}
              disabled={loading !== null}
              onClick={() => handleLogin(u.id, u.role)}
              style={{
                display: "flex", alignItems: "center", gap: 14,
                padding: "12px 16px", borderRadius: 10,
                border: "1px solid var(--pw-border)",
                background: loading === u.id ? "var(--pw-surface-elevated)" : "var(--pw-surface)",
                cursor: loading !== null ? "not-allowed" : "pointer",
                opacity: loading !== null && loading !== u.id ? 0.6 : 1,
                transition: "background 0.1s",
                textAlign: "left",
                width: "100%",
              }}
            >
              <div style={{
                width: 38, height: 38, borderRadius: "50%",
                background: "var(--pw-primary)",
                display: "flex", alignItems: "center", justifyContent: "center",
                color: "#fff", fontWeight: 700, fontSize: 13, flexShrink: 0,
              }}>
                {loading === u.id ? "…" : u.initials}
              </div>
              <div style={{ flex: 1 }}>
                <p style={{ margin: 0, fontSize: 14, fontWeight: 600, color: "var(--pw-text-primary)" }}>
                  {u.name}
                </p>
                <p style={{ margin: 0, fontSize: 12, color: "var(--pw-text-muted)" }}>
                  {u.role} · {u.id}
                </p>
              </div>
            </button>
          ))}
        </div>

        {error && (
          <p style={{
            marginTop: 16, fontSize: 13, color: "var(--pw-escalate)",
            background: "var(--pw-escalate-tint)", borderRadius: 6, padding: "8px 12px",
          }}>
            {error}
          </p>
        )}

        <p style={{ marginTop: 20, fontSize: 11, color: "var(--pw-text-muted)", textAlign: "center" }}>
          PoC — no passwords required
        </p>
      </div>
    </div>
  )
}
