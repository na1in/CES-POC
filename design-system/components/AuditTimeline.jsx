/**
 * PayWise Audit Timeline
 *
 * Vertical dot-and-line timeline for case audit logs.
 *
 * Usage:
 *   <AuditTimeline entries={caseData.auditLog} />
 *
 * Entry shape:
 *   { timestamp: string, user: string, action: string, details: string }
 */

import { colors, typography, radius } from '../tokens.js'

export function AuditTimeline({ entries = [] }) {
  return (
    <div>
      {entries.map((e, i) => (
        <div key={i} style={{ display: 'flex', gap: 12, paddingBottom: i < entries.length - 1 ? 4 : 0 }}>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flexShrink: 0 }}>
            <div style={{ width: 8, height: 8, borderRadius: radius.full, background: colors.primary, marginTop: 4 }} />
            {i < entries.length - 1 && (
              <div style={{ width: 1, flex: 1, background: colors.border, margin: '4px 0' }} />
            )}
          </div>
          <div style={{ flex: 1, paddingBottom: i < entries.length - 1 ? 16 : 0 }}>
            <div style={{ fontSize: typography.textXs, color: colors.textMuted, fontFamily: typography.fontMono, marginBottom: 2 }}>
              {e.timestamp} — <span style={{ color: colors.textSecondary }}>{e.user}</span>
            </div>
            <div style={{ fontSize: typography.textBase, fontWeight: typography.semibold, color: colors.textPrimary, marginBottom: 4 }}>
              {e.action}
            </div>
            <div style={{
              fontSize: typography.textSm,
              color: colors.textSecondary,
              background: colors.bgPrimary,
              border: `1px solid ${colors.bgSurfaceElevated}`,
              borderRadius: radius.md,
              padding: '8px 12px',
              lineHeight: 1.5,
            }}>
              {e.details}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
