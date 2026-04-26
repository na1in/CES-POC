/**
 * PayWise Logo
 *
 * <Logo />          — mark + wordmark (default, horizontal)
 * <Logo markOnly /> — just the icon mark
 * <Avatar initials="PV" size={32} />  — user avatar
 *
 * Mark: dark square (#0F172A) with dual vertical bars (white + purple)
 * Wordmark: "Pay" in textPrimary + "Wise" in primary, DM Sans font
 */

import { colors, radius, typography } from '../tokens.js'

export function LogoMark({ size = 28 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" fill="none">
      <rect width="32" height="32" rx="7" fill="#0F172A" />
      <rect x="9"  y="10" width="5" height="12" rx="2.5" fill="white" />
      <rect x="18" y="10" width="5" height="12" rx="2.5" fill="#7C4DFF" />
      <rect x="14" y="15.5" width="4" height="1.5" rx=".75" fill="rgba(255,255,255,0.4)" />
    </svg>
  )
}

export function Logo({ markOnly = false, size = 28 }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <LogoMark size={size} />
      {!markOnly && (
        <span style={{
          fontFamily: typography.fontDisplay,
          fontWeight: typography.bold,
          fontSize: 15,
          color: colors.textPrimary,
          letterSpacing: '-0.2px',
          lineHeight: 1,
        }}>
          Pay<span style={{ color: colors.primary }}>Wise</span>
        </span>
      )}
    </div>
  )
}

export function Avatar({ initials = 'PV', size = 32, style }) {
  return (
    <div style={{
      width: size,
      height: size,
      borderRadius: radius.full,
      background: '#0F172A',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontFamily: typography.fontSans,
      fontWeight: typography.bold,
      color: '#fff',
      fontSize: Math.round(size * 0.34),
      flexShrink: 0,
      ...style,
    }}>
      {initials}
    </div>
  )
}
