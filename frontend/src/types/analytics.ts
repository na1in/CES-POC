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
