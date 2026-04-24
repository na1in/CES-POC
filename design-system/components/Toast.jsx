/**
 * PayWise Toast
 *
 * Fixed bottom-right notification. Auto-dismisses after `duration` ms.
 *
 * Usage (with useToast hook):
 *   const { toast, showToast } = useToast()
 *   showToast({ title: 'Case accepted', desc: 'PMT-1001 marked as resolved.' })
 *   return <>{toast && <Toast {...toast} />}</>
 *
 * Or uncontrolled:
 *   <Toast title="Action submitted" type="success" />
 */

import { useState, useEffect } from 'react'
import { colors, radius, shadows, typography } from '../tokens.js'

const TYPE_STYLES = {
  success: { iconBg: 'rgba(16,185,129,.15)', iconColor: colors.apply,    icon: '✓' },
  warning: { iconBg: 'rgba(245,158,11,.15)', iconColor: colors.hold,     icon: '⏸' },
  error:   { iconBg: 'rgba(239,68,68,.15)',  iconColor: colors.escalate, icon: '⚠' },
  info:    { iconBg: 'rgba(59,130,246,.15)', iconColor: colors.info,     icon: 'ℹ' },
}

export function Toast({ title, desc, type = 'success', onClose }) {
  const t = TYPE_STYLES[type] || TYPE_STYLES.success

  return (
    <div style={{
      position: 'fixed',
      bottom: 48,
      right: 24,
      background: colors.bgSurface,
      border: `1px solid ${colors.border}`,
      borderRadius: radius.lg,
      padding: '12px 16px',
      boxShadow: shadows.xl,
      zIndex: 200,
      minWidth: 300,
      display: 'flex',
      alignItems: 'flex-start',
      gap: 10,
      animation: 'toastIn .25s ease',
    }}>
      <div style={{
        width: 20, height: 20,
        borderRadius: radius.full,
        background: t.iconBg,
        color: t.iconColor,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 11, flexShrink: 0, marginTop: 1,
      }}>
        {t.icon}
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ fontWeight: typography.semibold, fontSize: typography.textSm, color: colors.textPrimary }}>
          {title}
        </div>
        {desc && (
          <div style={{ fontSize: typography.textXs, color: colors.textSecondary, marginTop: 2 }}>
            {desc}
          </div>
        )}
      </div>
      {onClose && (
        <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: colors.textMuted, fontSize: 14, lineHeight: 1 }}>
          ✕
        </button>
      )}
    </div>
  )
}

/** Hook for managing toast state */
export function useToast(duration = 3500) {
  const [toast, setToast] = useState(null)

  const showToast = (opts) => {
    setToast(opts)
    setTimeout(() => setToast(null), duration)
  }

  return { toast, showToast, hideToast: () => setToast(null) }
}
