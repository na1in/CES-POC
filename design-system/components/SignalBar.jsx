/**
 * PayWise AI Signal Bar
 *
 * Renders a labelled progress bar used in the AI analysis panel.
 * Bar colour is automatically derived from the value:
 *   ≥ 90  → apply green
 *   ≥ 70  → hold amber
 *   > 0   → escalate red
 *   0     → neutral (empty track)
 *
 * Usage:
 *   <SignalBar name="Name Similarity" value={100} label="Exact match" />
 *   <SignalBar name="Duplicate Check" value={100} label="DUPLICATE DETECTED" forceColor="escalate" />
 *
 * Props:
 *   name        string   — left label
 *   value       number   — 0–100
 *   label       string   — right label (descriptive)
 *   forceColor  'apply'|'hold'|'escalate'  — override auto colour
 */

import { colors, typography } from '../tokens.js'

const barColor = (value, force) => {
  if (force === 'escalate') return colors.escalate
  if (force === 'hold')     return colors.hold
  if (force === 'apply')    return colors.apply
  if (value >= 90) return colors.apply
  if (value >= 70) return colors.hold
  if (value > 0)   return colors.escalate
  return colors.border
}

export function SignalBar({ name, value, label, forceColor }) {
  const fill = barColor(value, forceColor)

  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
        <span style={{ fontSize: typography.textSm, color: colors.textSecondary }}>{name}</span>
        <span style={{ fontSize: typography.textXs, color: colors.textPrimary, fontFamily: typography.fontSans }}>{label}</span>
      </div>
      <div style={{ height: 6, background: colors.bgSurfaceElevated, borderRadius: 9999, overflow: 'hidden' }}>
        <div style={{
          height: '100%',
          width: `${Math.min(100, Math.max(0, value))}%`,
          background: fill,
          borderRadius: 9999,
          transition: 'width 0.4s ease',
        }} />
      </div>
    </div>
  )
}

/**
 * AI Recommendation Box — coloured banner with rec + confidence + reasoning.
 *
 * Usage:
 *   <RecommendationBox rec="HOLD" confidence={78} reasoning="Payment is 8% higher…" />
 */
export function RecommendationBox({ rec, confidence, reasoning }) {
  const colorMap = {
    APPLY:    { bg: colors.applyTint,    border: colors.apply,    color: colors.apply    },
    HOLD:     { bg: colors.holdTint,     border: colors.hold,     color: colors.hold     },
    ESCALATE: { bg: colors.escalateTint, border: colors.escalate, color: colors.escalate },
  }
  const t = colorMap[rec] || colorMap.HOLD

  return (
    <div style={{
      background: t.bg,
      border: `1px solid ${t.border}`,
      borderRadius: 8,
      padding: '12px 14px',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: 3 }}>
        <span style={{ fontSize: typography.textXs, fontWeight: typography.semibold, textTransform: 'uppercase', letterSpacing: '0.05em', color: t.color }}>
          Recommendation
        </span>
        <span style={{ fontSize: 18, fontWeight: typography.bold, color: t.color, fontFamily: typography.fontSans }}>
          {confidence}%
        </span>
      </div>
      <div style={{ fontSize: 15, fontWeight: typography.bold, color: t.color, marginBottom: 4 }}>{rec}</div>
      {reasoning && <div style={{ fontSize: typography.textSm, color: colors.textPrimary, lineHeight: 1.5 }}>{reasoning}</div>}
    </div>
  )
}
