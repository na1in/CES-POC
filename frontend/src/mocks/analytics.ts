import type { AnalyticsDecisionsResponse, AdminAnalyticsData, AdminScenarioData } from "@/types/analytics"

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

// ── Admin Analytics ────────────────────────────────────────────────────────────

function makeScenarioData(
  volume: number,
  avg_confidence: number,
  override_count: number,
  aiAuto: number,
  humanConfirmed: number,
  humanOverride: number,
  bandOverrides: [number, number, number],
  histCounts: [number, number, number, number, number],
): AdminScenarioData {
  return {
    volume,
    avg_confidence,
    override_count,
    case_volume_trend: [
      { week: "Mar 30", count: Math.round(volume * 0.16) },
      { week: "Apr 6",  count: Math.round(volume * 0.19) },
      { week: "Apr 13", count: Math.round(volume * 0.22) },
      { week: "Apr 20", count: Math.round(volume * 0.21) },
      { week: "Apr 27", count: Math.round(volume * 0.22) },
    ],
    decision_distribution: [
      { label: "AI Autonomous",   value: aiAuto },
      { label: "Human Confirmed", value: humanConfirmed },
      { label: "Human Override",  value: humanOverride },
    ],
    override_by_band: [
      { band: "Low",    override_rate_pct: bandOverrides[0] },
      { band: "Medium", override_rate_pct: bandOverrides[1] },
      { band: "High",   override_rate_pct: bandOverrides[2] },
    ],
    confidence_histogram: [
      { bucket: "0–20",   count: histCounts[0] },
      { bucket: "21–40",  count: histCounts[1] },
      { bucket: "41–60",  count: histCounts[2] },
      { bucket: "61–80",  count: histCounts[3] },
      { bucket: "81–100", count: histCounts[4] },
    ],
  }
}

export const mockAdminAnalytics: AdminAnalyticsData = {
  all:        makeScenarioData(431, 78, 19, 214, 198, 19, [18, 9, 3],  [12, 28, 55, 97, 239]),
  scenario_1: makeScenarioData(187, 91,  4, 142,  41,  4, [ 6, 4, 1],  [ 0,  4, 18, 48, 117]),
  scenario_2: makeScenarioData( 89, 74,  7,   0,  82,  7, [22, 11, 0], [ 2, 12, 31, 28,  16]),
  scenario_3: makeScenarioData(103, 68,  5,  32,  66,  5, [25, 13, 2], [ 4,  9, 19, 47,  24]),
  scenario_4: makeScenarioData( 37, 42,  2,   0,  35,  2, [30, 0,  0], [ 6,  3,  7,  9,  12]),
  scenario_5: makeScenarioData( 15, 88,  1,  11,   3,  1, [ 0, 5,  2], [ 0,  0,  0,  6,   9]),
}
