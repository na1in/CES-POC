/**
 * Chart fill colors.
 *
 * These are hex literals rather than `var(--pw-*)` on purpose: Recharts sets
 * `fill` as an SVG presentation attribute, and CSS custom properties are not
 * resolved there — a `var()` reference renders as black. Keep these in sync
 * with the matching tokens in globals.css.
 */

/**
 * Muted slate for decorative fills (plain volume/confidence bars, the pie's
 * majority slice). Full-saturation --pw-primary stays reserved for actions,
 * navigation and links so those remain the things that read as clickable.
 */
export const CHART_NEUTRAL = "#64748B"

/** Semantic decision colors, matching the apply/hold/escalate vocabulary. */
export const CHART_APPLY = "#047857"
export const CHART_HOLD = "#B45309"
export const CHART_ESCALATE = "#B91C1C"
