/**
 * PayWise Button
 *
 * Variants: primary | apply | hold | escalate | ghost | outline-escalate
 * Sizes:    md (default) | sm
 *
 * Usage:
 *   <Button variant="apply" onClick={...}>Accept APPLY</Button>
 *   <Button variant="ghost" size="sm">Cancel</Button>
 */

import { colors, radius, typography, transition } from '../tokens.js'

const VARIANT_STYLES = {
  primary: {
    background: colors.primary,
    color: '#fff',
    border: `1px solid ${colors.primary}`,
    '--hover-bg': colors.primaryHover,
  },
  apply: {
    background: colors.apply,
    color: '#fff',
    border: `1px solid ${colors.apply}`,
    '--hover-bg': colors.applyHover,
  },
  hold: {
    background: colors.hold,
    color: '#fff',
    border: `1px solid ${colors.hold}`,
    '--hover-bg': colors.holdHover,
  },
  escalate: {
    background: colors.escalate,
    color: '#fff',
    border: `1px solid ${colors.escalate}`,
    '--hover-bg': colors.escalateHover,
  },
  ghost: {
    background: 'transparent',
    color: colors.textPrimary,
    border: `1px solid ${colors.border}`,
    '--hover-bg': colors.bgSurfaceElevated,
  },
  'outline-escalate': {
    background: 'transparent',
    color: colors.escalate,
    border: `1px solid ${colors.escalate}`,
    '--hover-bg': colors.escalateTint,
  },
}

const SIZE_STYLES = {
  md: { padding: '8px 16px', fontSize: 14, borderRadius: radius.md },
  sm: { padding: '4px 12px', fontSize: 12, borderRadius: radius.sm },
}

export function Button({
  variant = 'primary',
  size = 'md',
  disabled = false,
  onClick,
  children,
  style,
  ...props
}) {
  const v = VARIANT_STYLES[variant] || VARIANT_STYLES.primary
  const s = SIZE_STYLES[size]

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 6,
        fontFamily: typography.fontSans,
        fontWeight: typography.semibold,
        lineHeight: 1,
        cursor: disabled ? 'not-allowed' : 'pointer',
        transition,
        opacity: disabled ? 0.5 : 1,
        ...s,
        background: v.background,
        color: v.color,
        border: v.border,
        ...style,
      }}
      onMouseEnter={e => { if (!disabled) e.currentTarget.style.opacity = '.85' }}
      onMouseLeave={e => { e.currentTarget.style.opacity = '1' }}
      {...props}
    >
      {children}
    </button>
  )
}
