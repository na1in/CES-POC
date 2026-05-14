"use client"

import { createContext, useCallback, useContext, useEffect, useState } from "react"
import { login as apiLogin, type LoginResponse } from "@/lib/api"

interface AuthUser {
  user_id: string
  name: string
  role: string
}

interface AuthContextValue {
  user: AuthUser | null
  loading: boolean
  login: (userId: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<AuthUser | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = localStorage.getItem("ces_token")
    const stored = localStorage.getItem("ces_user")
    if (token && stored) {
      try {
        setUser(JSON.parse(stored))
      } catch {
        localStorage.removeItem("ces_token")
        localStorage.removeItem("ces_user")
      }
    }
    setLoading(false)
  }, [])

  const login = useCallback(async (userId: string) => {
    const res: LoginResponse = await apiLogin(userId)
    localStorage.setItem("ces_token", res.access_token)
    const u: AuthUser = { user_id: userId, name: res.name, role: res.role }
    localStorage.setItem("ces_user", JSON.stringify(u))
    setUser(u)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem("ces_token")
    localStorage.removeItem("ces_user")
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error("useAuth must be used inside AuthProvider")
  return ctx
}
