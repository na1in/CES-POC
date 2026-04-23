/**
 * PayWise Design System — JS Tokens
 * Mirror of tokens.css. Use in inline styles or styled-components.
 * For Tailwind projects, map these into tailwind.config.js instead.
 */

export const colors = {
  // Backgrounds
  bgPrimary:        '#F8F9FA',
  bgSurface:        '#FFFFFF',
  bgSurfaceElevated:'#F1F3F5',

  // Brand
  primary:          '#7C4DFF',
  primaryHover:     '#6A3FE8',
  secondary:        '#00E5FF',

  // Status
  apply:            '#10B981',
  applyHover:       '#059669',
  applyTint:        'rgba(16, 185, 129, 0.10)',

  hold:             '#F59E0B',
  holdHover:        '#D97706',
  holdTint:         'rgba(245, 158, 11, 0.10)',

  escalate:         '#EF4444',
  escalateHover:    '#DC2626',
  escalateTint:     'rgba(239, 68, 68, 0.10)',

  info:             '#3B82F6',
  infoTint:         'rgba(59, 130, 246, 0.10)',

  // Text
  textPrimary:      '#1E293B',
  textSecondary:    '#64748B',
  textMuted:        '#94A3B8',

  // Border
  border:           '#E2E8F0',
}

export const typography = {
  fontSans:    "'Inter', sans-serif",
  fontMono:    "'JetBrains Mono', monospace",
  fontDisplay: "'DM Sans', sans-serif", // logo / wordmark only

  textXs:   11,
  textSm:   12,
  textBase: 14,
  textMd:   16,
  textLg:   20,
  textXl:   24,

  leading: 1.5,

  normal:   400,
  medium:   500,
  semibold: 600,
  bold:     700,
}

export const spacing = {
  1:  4,
  2:  8,
  3:  12,
  4:  16,
  5:  20,
  6:  24,
  8:  32,
  10: 40,
}

export const radius = {
  sm:   4,
  md:   8,
  lg:   12,
  xl:   16,
  full: 9999,
}

export const shadows = {
  sm: '0 1px 2px rgba(0,0,0,0.05)',
  md: '0 4px 6px rgba(0,0,0,0.07)',
  xl: '0 20px 40px rgba(0,0,0,0.12)',
}

export const layout = {
  panelWidth:   480,
  navHeight:    52,
  footerHeight: 28,
}

export const transition = 'all 200ms ease'

/** Gradient used on logo mark and avatars */
export const gradientBrand = 'linear-gradient(135deg, #7C4DFF, #00E5FF)'

/**
 * Semantic token map for recommendation / status values.
 * Usage: REC_TOKENS['APPLY'].bg → the tint background
 */
export const REC_TOKENS = {
  APPLY: {
    bg:    colors.apply,
    tint:  colors.applyTint,
    hover: colors.applyHover,
    color: colors.apply,
    text:  '#fff',
  },
  HOLD: {
    bg:    colors.hold,
    tint:  colors.holdTint,
    hover: colors.holdHover,
    color: colors.hold,
    text:  '#fff',
  },
  ESCALATE: {
    bg:    colors.escalate,
    tint:  colors.escalateTint,
    hover: colors.escalateHover,
    color: colors.escalate,
    text:  '#fff',
  },
}

export const STATUS_TOKENS = {
  open:      { bg: colors.bgSurfaceElevated, color: colors.textSecondary },
  resolved:  { bg: colors.applyTint,         color: colors.apply         },
  held:      { bg: colors.holdTint,           color: colors.hold          },
  escalated: { bg: colors.escalateTint,       color: colors.escalate      },
  pending:   { bg: colors.bgSurfaceElevated,  color: colors.textMuted     },
}
