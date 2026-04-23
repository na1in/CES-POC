/**
 * PayWise Badges
 *
 * Components:
 *   <RecBadge rec="APPLY|HOLD|ESCALATE" />
 *   <StatusBadge status="open|resolved|held|escalated|pending" />
 *   <FlagBadge flag="Amount Variance" />
 *   <RiskBadge level="high|medium|low" />
 *   <CountBadge count={4} />
 *   <ConfidenceText value={98} rec="APPLY" />
 */

import { colors, radius, typography } from '../tokens.js'

const REC_MAP = {
  APPLY:    { bg: colors.applyTint,    color: colors.apply    },
  HOLD:     { bg: colors.holdTint,     color: colors.hold     },
  ESCALATE: { bg: colors.escalateTint, color: colors.escalate },
}

const STATUS_MAP = {
  open:      { bg: colors.bgSurfaceElevated, color: colors.textSecondary },
  resolved:  { bg: colors.applyTint,         color: colors.apply         },
  held:      { bg: colors.holdTint,           color: colors.hold          },
  escalated: { bg: colors.escalateTint,       color: colors.escalate      },
  pending:   { bg: colors.bgSurfaceElevated,  color: colors.textMuted     },
}

const RISK_MAP = {
  high:   { bg: colors.escalateTint, color: colors.escalate },
  medium: { bg: colors.holdTint,     color: colors.hold     },
  low:    { bg: colors.applyTint,    color: colors.apply    },
}

const baseBadgeStyle = {
  display: 'inline-flex',
  alignItems: 'center',
  padding: '2px 10px',
  borderRadius: radius.full,
  fontSize: typography.textXs,
  fontWeight: typography.semibold,
  fontFamily: typography.fontSans,
  letterSpacing: '0.04em',
  textTransform: 'uppercase',
}

export function RecBadge({ rec }) {
  const t = REC_MAP[rec] || { bg: colors.bgSurfaceElevated, color: colors.textSecondary }
  return <span style={{ ...baseBadgeStyle, background: t.bg, color: t.color }}>{rec}</span>
}

export function StatusBadge({ status }) {
  const t = STATUS_MAP[status] || STATUS_MAP.pending
  return <span style={{ ...baseBadgeStyle, background: t.bg, color: t.color, textTransform: 'capitalize' }}>{status}</span>
}

export function FlagBadge({ flag }) {
  return (
    <span style={{ ...baseBadgeStyle, background: colors.holdTint, color: colors.hold, textTransform: 'none' }}>
      ⚠ {flag}
    </span>
  )
}

export function RiskBadge({ level }) {
  const t = RISK_MAP[level] || RISK_MAP.medium
  return (
    <span style={{ ...baseBadgeStyle, background: t.bg, color: t.color, textTransform: 'capitalize' }}>
      {level} Risk
    </span>
  )
}

export function CountBadge({ count, active = false }) {
  return (
    <span style={{
      ...baseBadgeStyle,
      padding: '1px 8px',
      background: active ? colors.primary : colors.bgSurfaceElevated,
      color: active ? '#fff' : colors.textSecondary,
      textTransform: 'none',
      letterSpacing: 0,
    }}>
      {count}
    </span>
  )
}

export function ConfidenceText({ value, rec }) {
  const color = rec === 'APPLY' ? colors.apply : rec === 'HOLD' ? colors.hold : colors.escalate
  return (
    <span style={{ fontSize: typography.textSm, fontWeight: typography.semibold, color, fontFamily: typography.fontSans }}>
      {value}%
    </span>
  )
}
