"use client"

import { createContext, useContext, useState, useCallback } from "react"
import { CheckCircle2, AlertTriangle, Info, X } from "lucide-react"

type ToastType = "success" | "error" | "warning" | "info"

interface ToastMessage {
  id: number
  title: string
  type: ToastType
}

interface ToastContextValue {
  showToast: (opts: { title: string; type: ToastType }) => void
}

const ToastContext = createContext<ToastContextValue>({ showToast: () => {} })

let nextId = 0

const TOAST_STYLES: Record<ToastType, { bg: string; border: string; color: string }> = {
  success: { bg: "var(--pw-apply-tint)",    border: "var(--pw-apply)",    color: "var(--pw-apply)"    },
  error:   { bg: "var(--pw-escalate-tint)", border: "var(--pw-escalate)", color: "var(--pw-escalate)" },
  warning: { bg: "var(--pw-hold-tint)",     border: "var(--pw-hold)",     color: "var(--pw-hold)"     },
  info:    { bg: "var(--pw-info-tint)",     border: "var(--pw-info)",     color: "var(--pw-info)"     },
}

const TOAST_ICON: Record<ToastType, React.ReactNode> = {
  success: <CheckCircle2 size={14} />,
  error:   <AlertTriangle size={14} />,
  warning: <AlertTriangle size={14} />,
  info:    <Info size={14} />,
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastMessage[]>([])

  const showToast = useCallback(({ title, type }: { title: string; type: ToastType }) => {
    const id = ++nextId
    setToasts(prev => [...prev, { id, title, type }])
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 4000)
  }, [])

  function dismiss(id: number) {
    setToasts(prev => prev.filter(t => t.id !== id))
  }

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}
      <div
        style={{
          position: "fixed",
          top: 16,
          right: 24,
          zIndex: 9999,
          display: "flex",
          flexDirection: "column",
          gap: 8,
          pointerEvents: "none",
        }}
      >
        {toasts.map(t => {
          const s = TOAST_STYLES[t.type]
          return (
            <div
              key={t.id}
              role="status"
              style={{
                background: s.bg,
                border: `1px solid ${s.border}`,
                color: s.color,
                padding: "10px 14px 10px 12px",
                borderRadius: 8,
                fontSize: 13,
                fontWeight: 600,
                boxShadow: "0 4px 12px rgba(0,0,0,0.12)",
                minWidth: 220,
                maxWidth: 360,
                display: "flex",
                alignItems: "center",
                gap: 8,
                pointerEvents: "auto",
              }}
            >
              {TOAST_ICON[t.type]}
              <span style={{ flex: 1 }}>{t.title}</span>
              <button
                onClick={() => dismiss(t.id)}
                style={{ background: "none", border: "none", cursor: "pointer", padding: 0, color: "inherit", opacity: 0.6, lineHeight: 1 }}
                aria-label="Dismiss"
              >
                <X size={12} />
              </button>
            </div>
          )
        })}
      </div>
    </ToastContext.Provider>
  )
}

export function useToast() {
  return useContext(ToastContext)
}
