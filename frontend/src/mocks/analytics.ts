import type { AnalyticsDecisionsResponse } from "@/types/analytics"

export const mockAnalyticsDecisions: AnalyticsDecisionsResponse = {
  date_from: "2026-03-30",
  date_to: "2026-04-29",
  summary: {
    auto_applied_by_ai: 214,
    applied_after_human_review: 89,
    held_pending_review: 34,
    escalated_by_ai: 47,
    escalated_by_human: 28,
    human_overrides: 19,
    override_rate_pct: 7.2,
    total_payments: 431,
  },
  by_payment_method: [
    { method: "ACH",         count: 178, auto_apply_rate_pct: 72 },
    { method: "Check",       count: 103, auto_apply_rate_pct: 41 },
    { method: "Wire",        count:  89, auto_apply_rate_pct: 38 },
    { method: "Credit Card", count:  61, auto_apply_rate_pct: 55 },
  ],
  override_rate_trend: [
    { date: "2026-03-30", override_rate_pct: 8.1 },
    { date: "2026-04-06", override_rate_pct: 7.8 },
    { date: "2026-04-13", override_rate_pct: 7.5 },
    { date: "2026-04-20", override_rate_pct: 7.2 },
    { date: "2026-04-27", override_rate_pct: 6.9 },
  ],
  confidence_histogram: [
    { bucket: "0–20",  count:  12 },
    { bucket: "21–40", count:  28 },
    { bucket: "41–60", count:  55 },
    { bucket: "61–80", count:  97 },
    { bucket: "81–100", count: 239 },
  ],
  sla_adherence: {
    resolved_before_breach: 69,
    total_escalations: 75,
    adherence_pct: 92,
  },
}
