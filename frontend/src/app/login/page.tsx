"use client"

import { useState } from "react"
import { useRouter } from "next/navigation"
import { apiFetch, setToken } from "@/lib/api"
import { useToast } from "@/contexts/ToastContext"

export default function LoginPage() {
  const router = useRouter()
  const { showToast } = useToast()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setLoading(true)
    try {
      const data = await apiFetch<{ access_token: string }>("/api/auth/token", {
        method: "POST",
        body: JSON.stringify({ username: email, password }),
      })
      setToken(data.access_token)
      router.push("/")
    } catch {
      showToast({ title: "Invalid credentials", type: "error" })
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "var(--pw-bg)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <div className="pw-card" style={{ width: 360, padding: 32 }}>
        {/* Logo */}
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 28 }}>
          <div
            style={{
              width: 32, height: 32, background: "var(--pw-primary)", borderRadius: 8,
              display: "flex", alignItems: "center", justifyContent: "center",
            }}
          >
            <span style={{ color: "#fff", fontWeight: 700, fontSize: 15 }}>P</span>
          </div>
          <span
            style={{
              fontSize: 18, fontWeight: 700,
              fontFamily: "var(--pw-font-display)",
              color: "var(--pw-text-primary)",
            }}
          >
            PayWise
          </span>
        </div>

        <h1 style={{ fontSize: 17, fontWeight: 700, margin: "0 0 4px", color: "var(--pw-text-primary)" }}>
          Sign in
        </h1>
        <p style={{ fontSize: 13, color: "var(--pw-text-muted)", margin: "0 0 24px" }}>
          Payment Resolution Console
        </p>

        <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div>
            <label
              htmlFor="email"
              style={{ fontSize: 12, fontWeight: 600, color: "var(--pw-text-secondary)", display: "block", marginBottom: 4 }}
            >
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              placeholder="you@company.com"
              style={{
                width: "100%", border: "1px solid var(--pw-border)", borderRadius: 8,
                padding: "9px 12px", fontSize: 13, boxSizing: "border-box",
                outline: "none", color: "var(--pw-text-primary)", background: "var(--pw-surface)",
              }}
            />
          </div>
          <div>
            <label
              htmlFor="password"
              style={{ fontSize: 12, fontWeight: 600, color: "var(--pw-text-secondary)", display: "block", marginBottom: 4 }}
            >
              Password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              placeholder="••••••••"
              style={{
                width: "100%", border: "1px solid var(--pw-border)", borderRadius: 8,
                padding: "9px 12px", fontSize: 13, boxSizing: "border-box",
                outline: "none", color: "var(--pw-text-primary)", background: "var(--pw-surface)",
              }}
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            style={{
              background: loading ? "var(--pw-text-muted)" : "var(--pw-primary)",
              color: "#fff", border: "none", borderRadius: 8,
              padding: "10px 0", fontWeight: 600, fontSize: 14,
              cursor: loading ? "not-allowed" : "pointer",
              marginTop: 4,
            }}
          >
            {loading ? "Signing in…" : "Sign in"}
          </button>
        </form>
      </div>
    </div>
  )
}
