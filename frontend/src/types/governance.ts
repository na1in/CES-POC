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
}

export interface SlaBreachedPayment {
  payment_id: string
  sender_name: string
  amount: number
  scenario: string
  investigation_due_date: string
  investigator: string
}
