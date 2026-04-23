/**
 * PayWise Card primitives
 *
 * <Card>            — white card with border + shadow-sm
 * <StatCard>        — dashboard KPI tile (icon + label + value)
 * <SectionCard>     — collapsible section card used in case detail
 *
 * Usage:
 *   <Card>…</Card>
 *
 *   <StatCard
 *     label="Cases Closed Today"
 *     value={67}
 *     icon={<Clock size={18} />}
 *     iconColor="#3B82F6"
 *     iconBg="rgba(59,130,246,.1)"
 *   />
 *
 *   <SectionCard title="Audit Trail" collapsible>
 *     <AuditTimeline … />
 *   </SectionCard>
 */

import { useState } from 'react'
import { colors, radius, shadows, typography, transition } from '../tokens.js'

/* ── Card ───────────────────────────────────────────────────── */
export function Card({ children, style, ...props }) {
  return (
    <div style={{
      background: colors.bgSurface,
      border: `1px solid ${colors.border}`,
      borderRadius: radius.lg,
      boxShadow: shadows.sm,
      overflow: 'hidden',
      ...style,
    }} {...props}>
      {children}
    </div>
  )
}

/* ── StatCard ───────────────────────────────────────────────── */
export function StatCard({ label, value, sub, icon, iconColor, iconBg }) {
  return (
    <div style={{
      flex: 1,
      background: colors.bgSurface,
      borderRadius: radius.lg,
      padding: '12px 16px',
      display: 'flex',
      alignItems: 'center',
      gap: 12,
    }}>
      {icon && (
        <div style={{
          width: 38,
          height: 38,
          borderRadius: radius.full,
          background: iconBg || colors.bgSurfaceElevated,
          color: iconColor || colors.textSecondary,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
          fontSize: 17,
        }}>
          {icon}
        </div>
      )}
      <div>
        <div style={{
          fontSize: typography.textXs,
          fontWeight: typography.semibold,
          textTransform: 'uppercase',
          letterSpacing: '0.05em',
          color: colors.textSecondary,
          marginBottom: 2,
        }}>
          {label}
        </div>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 5 }}>
          <span style={{ fontSize: 22, fontWeight: typography.bold, color: colors.textPrimary, lineHeight: 1.2 }}>
            {value}
          </span>
          {sub && <span style={{ fontSize: typography.textXs, color: colors.textSecondary }}>{sub}</span>}
        </div>
      </div>
    </div>
  )
}

/* ── StatCardRow ────────────────────────────────────────────── */
export function StatCardRow({ stats }) {
  return (
    <div style={{ display: 'flex', gap: 12 }}>
      {stats.map((s, i) => <StatCard key={i} {...s} />)}
    </div>
  )
}

/* ── SectionCard ────────────────────────────────────────────── */
export function SectionCard({ title, children, collapsible = false, defaultOpen = true, style }) {
  const [open, setOpen] = useState(defaultOpen)

  return (
    <div style={{
      background: colors.bgSurface,
      border: `1px solid ${colors.border}`,
      borderRadius: radius.lg,
      overflow: 'hidden',
      ...style,
    }}>
      <div
        style={{
          padding: '16px 20px',
          borderBottom: (open || !collapsible) ? `1px solid ${colors.border}` : 'none',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          cursor: collapsible ? 'pointer' : 'default',
        }}
        onClick={() => collapsible && setOpen(o => !o)}
      >
        <span style={{ fontSize: typography.textMd, fontWeight: typography.semibold, color: colors.textPrimary }}>
          {title}
        </span>
        {collapsible && (
          <svg
            width="16" height="16" viewBox="0 0 24 24"
            fill="none" stroke={colors.textSecondary} strokeWidth="2"
            strokeLinecap="round" strokeLinejoin="round"
            style={{ transform: open ? 'rotate(180deg)' : 'rotate(0deg)', transition }}
          >
            <polyline points="18 15 12 9 6 15" />
          </svg>
        )}
      </div>
      {open && <div style={{ padding: '16px 20px' }}>{children}</div>}
    </div>
  )
}
