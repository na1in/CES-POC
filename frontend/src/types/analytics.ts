export interface DecisionSummary {
  auto_applied_by_ai: number
  applied_after_human_review: number
  held_pending_review: number
  escalated_by_ai: number
  escalated_by_human: number
  human_overrides: number
  override_rate_pct: number
  total_payments: number
}

export interface PaymentMethodBreakdown {
  method: string
  count: number
  auto_apply_rate_pct: number
}

export interface OverrideRateTrend {
  date: string
  override_rate_pct: number
}

export interface ConfidenceBucket {
  bucket: string
  count: number
}

export interface SlaAdherence {
  resolved_before_breach: number
  total_escalations: number
  adherence_pct: number
}

export interface AnalyticsDecisionsResponse {
  date_from: string
  date_to: string
  summary: DecisionSummary
  by_payment_method: PaymentMethodBreakdown[]
  override_rate_trend: OverrideRateTrend[]
  confidence_histogram: ConfidenceBucket[]
  sla_adherence: SlaAdherence
}

export interface CaseVolumeTrend {
  week: string
  count: number
}

export interface DecisionDistributionItem {
  label: string
  value: number
}

export interface OverrideByBand {
  band: string
  override_rate_pct: number
}

export interface AdminScenarioData {
  volume: number
  avg_confidence: number
  override_count: number
  case_volume_trend: CaseVolumeTrend[]
  decision_distribution: DecisionDistributionItem[]
  override_by_band: OverrideByBand[]
  confidence_histogram: ConfidenceBucket[]
}

export interface AdminAnalyticsData {
  all: AdminScenarioData
  scenario_1: AdminScenarioData
  scenario_2: AdminScenarioData
  scenario_3: AdminScenarioData
  scenario_4: AdminScenarioData
  scenario_5: AdminScenarioData
}

export type ConfidenceBand = "Low" | "Medium" | "High"
export type PaymentDecision = "APPLY" | "HOLD" | "ESCALATE"

export interface OverrideEntry {
  payment_id: string
  scenario: string
  ai_recommendation: PaymentDecision
  human_decision: PaymentDecision
  confidence_score: number
  confidence_band: ConfidenceBand
  override_reason: string
  override_date: string
  analyst_name: string
}
