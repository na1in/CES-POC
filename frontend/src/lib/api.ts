const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

export function getToken(): string | null {
  if (typeof window === "undefined") return null
  return localStorage.getItem("auth_token")
}

export function setToken(token: string): void {
  localStorage.setItem("auth_token", token)
}

export function clearToken(): void {
  localStorage.removeItem("auth_token")
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message)
    this.name = "ApiError"
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init?.headers as Record<string, string> | undefined),
  }
  if (token) headers["Authorization"] = `Bearer ${token}`

  const res = await fetch(`${API_BASE}${path}`, { ...init, headers })

  if (res.status === 401) {
    clearToken()
    if (typeof window !== "undefined") window.location.href = "/login"
    throw new ApiError(401, "Unauthorized")
  }

  if (!res.ok) {
    const text = await res.text().catch(() => "")
    throw new ApiError(res.status, text || res.statusText)
  }

  if (res.status === 204) return undefined as T

  return res.json() as Promise<T>
}

// SWR-compatible fetcher
export const fetcher = <T>(url: string) => apiFetch<T>(url)
