export type Recommendation = "apply" | "hold" | "escalate"

export type ScenarioRoute =
  | "scenario_1"
  | "scenario_2"
  | "scenario_3"
  | "scenario_4"
  | "scenario_5"

export type DecisionAttribution =
  | "ai_autonomous"
  | "human_confirmed"
  | "human_override"

export interface PaymentRecommendation {
  payment_id: string
  recommendation: Recommendation
  confidence_score: number             // 0–100
  scenario_route: ScenarioRoute
  decision_path: string | null
  requires_human_approval: boolean
  approval_reason: string | null
  reasoning: string[]
  suggested_action: string | null
  processing_time_ms: number | null
  decision_attribution: DecisionAttribution | null
  created_at: string                   // ISO 8601
}
