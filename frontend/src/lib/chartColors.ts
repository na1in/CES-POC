/**
 * Chart fill colors.
 *
 * Hex literals rather than `var(--pw-*)` on purpose: Recharts sets `fill` as an
 * SVG presentation attribute, and CSS custom properties are not resolved there —
 * a `var()` reference renders as black.
 *
 * These are deliberately NOT the same values as the --pw-apply/hold/escalate UI
 * tokens. Those tokens carry white button text and badge text, so they are
 * darkened to clear 4.5:1 for *text*. A chart fill is a non-text graphical
 * object: WCAG 1.4.11 asks 3:1 against the surface, not 4.5:1. Reusing the
 * text-grade values here over-constrained the palette into olive/brick/mustard
 * that measured ΔE 9.1 apart — below the 15 floor, meaning full-colour readers
 * could not reliably tell the red from the amber.
 *
 * Validated as a categorical set against a white chart surface: lightness band,
 * chroma floor, protan/deutan/tritan separation, normal-vision floor (worst
 * adjacent pair ΔE 16.6) and 3:1 contrast all pass.
 */

/** Contrast vs white, measured: emerald 3.25:1 */
export const CHART_APPLY = "#0CA36B"
/** True amber, not mustard: 3.19:1 — the lightest amber that still clears 3:1 */
export const CHART_HOLD = "#D97706"
/** Crimson rather than brick: 4.70:1, and far enough from amber to separate */
export const CHART_ESCALATE = "#E11D48"

/**
 * Muted slate for decorative fills (plain volume/confidence bars, the pie's
 * majority slice), so full-saturation --pw-primary stays reserved for actions,
 * navigation and links.
 *
 * Reads as a near-neutral by design — that is the point of the slot, and it is
 * why it sits under the categorical chroma floor. It still clears 3:1 on white
 * and separates from every hue above (worst pair ΔE 15.9 simulated).
 */
export const CHART_NEUTRAL = "#55657F"
