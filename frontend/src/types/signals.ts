export type PaymentTimingQuality = "excellent" | "good" | "acceptable" | "poor"
export type AccountStatus = "active" | "inactive" | "closed"
export type PaymentMethodRiskLevel = "low" | "medium" | "high"
export type RiskFlagType = "fraud_history" | "suspended_account" | "chronic_late_payments"

export interface MatchingSignals {
  name_similarity_score: number        // 0–100
  policy_match_confidence: number      // 0–100
  customer_match_confidence: number    // 0–100
  account_match: boolean
  amount_match: boolean
  historical_match: boolean
  jaro_winkler_score: number           // 0–100
  levenshtein_score: number            // 0–100
  soundex_match: boolean
  deterministic_score: number          // 0–100
  used_llm: boolean
  llm_score: number                    // 0–100, 0 if used_llm=false
}

export interface AmountSignals {
  amount_variance_pct: number
  is_overpayment: boolean
  is_underpayment: boolean
  difference_amount: number            // cents
  is_multi_period: boolean
  estimated_periods: number
  historical_consistency_score: number // 0–100
  is_multi_method: boolean
  multi_method_fraction: number
  is_third_party_payment: boolean
  third_party_relationship: string
}

export interface TemporalSignals {
  payment_timing_quality: PaymentTimingQuality
  days_from_due_date: number           // positive = after due date, negative = before
  days_since_last_payment: number
}

export interface RiskSignals {
  has_risk_flags: boolean
  risk_flag_types: RiskFlagType[]
  account_status: AccountStatus
  payment_method_risk_level: PaymentMethodRiskLevel
  outstanding_balance_cents: number
  outstanding_balance_status: "current" | "past_due"
}

export interface DuplicateSignals {
  is_duplicate_match: boolean
  duplicate_payment_id: string
  hours_since_duplicate: number
  outstanding_balance_justifies: boolean
  duplicate_amount_difference: number  // cents; 0=exact, ≤200 = within $2 tolerance
}

export interface PaymentSignals {
  payment_id: string
  computed_at: string                  // ISO 8601
  matching: MatchingSignals
  amount: AmountSignals
  temporal: TemporalSignals
  risk: RiskSignals
  duplicate: DuplicateSignals
}
