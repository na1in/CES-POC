"use client"

import { useEffect } from "react"
import { usePathname, useRouter } from "next/navigation"
import { useAuth } from "@/contexts/auth"

const PUBLIC_PATHS = ["/login"]

export function RouteGuard({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth()
  const pathname = usePathname()
  const router = useRouter()

  useEffect(() => {
    if (loading) return
    const isPublic = PUBLIC_PATHS.some(p => pathname.startsWith(p))
    if (!user && !isPublic) {
      router.replace("/login")
    } else if (user && pathname === "/login") {
      const roleHome: Record<string, string> = {
        analyst: "/",
        investigator: "/investigations",
        director: "/governance",
        admin: "/admin",
      }
      router.replace(roleHome[user.role] ?? "/")
    }
  }, [user, loading, pathname, router])

  if (loading) {
    return (
      <div style={{
        minHeight: "100vh", display: "flex", alignItems: "center",
        justifyContent: "center", background: "var(--pw-bg)",
      }}>
        <div style={{ fontSize: 13, color: "var(--pw-text-muted)" }}>Loading…</div>
      </div>
    )
  }

  const isPublic = PUBLIC_PATHS.some(p => pathname.startsWith(p))
  if (!user && !isPublic) return null

  return <>{children}</>
}
