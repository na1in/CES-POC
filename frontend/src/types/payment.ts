export type PaymentStatus =
  | "received"
  | "processing"
  | "applied"
  | "held"
  | "escalated"
  | "processing_failed"
  | "pending_sender_response"
  | "returned"

export type PaymentMethod = "ACH" | "Check" | "Credit Card" | "Wire"

export interface Payment {
  payment_id: string               // e.g. "PMT-001"
  amount: number                   // cents, integer
  sender_name: string
  sender_account: string | null
  beneficiary_name: string | null
  payment_method: PaymentMethod
  payment_date: string             // ISO 8601
  reference_field_1: string | null
  reference_field_2: string | null
  status: PaymentStatus
  matched_customer_id: string | null
  matched_policy_id: string | null
  investigation_due_date: string | null
  sla_breached: boolean
  created_timestamp: string        // ISO 8601
}
