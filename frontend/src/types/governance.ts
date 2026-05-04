export type AnomalyStatus = "open" | "investigating" | "resolved"

export interface AnomalyFlag {
  anomaly_id: string
  metric: string
  description: string
  period: string
  flagged_by: string
  status: AnomalyStatus
  resolution_notes: string | null
  created_at: string
}

export type ChangeRequestStatus = "pending" | "approved" | "rejected" | "deployed"

export interface ConfigChangeRequest {
  request_id: string
  parameter_name: string
  current_value: string
  proposed_value: string
  proposed_by: string
  proposed_at: string
  status: ChangeRequestStatus
  review_comment: string | null
  rationale?: string
  projected_impact?: string | null
  reviewed_by?: string | null
  reviewed_at?: string | null
  deployed_at?: string | null
  deployed_by?: string | null
}

export interface ThresholdVersionEntry {
  version_id: string
  parameter_name: string
  old_value: string
  new_value: string
  changed_by: string
  changed_at: string
  change_request_id: string | null
}

export interface SlaBreachedPayment {
  payment_id: string
  sender_name: string
  amount: number
  scenario: string
  investigation_due_date: string
  investigator: string
}

export interface GovernanceReview {
  review_id: string
  period: string
  reviewed_by: string
  reviewed_at: string
  notes: string | null
  export_scope: string[]
}
