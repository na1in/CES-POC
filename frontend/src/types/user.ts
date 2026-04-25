export type UserRole = "analyst" | "investigator" | "director" | "admin"

export interface User {
  user_id: string                      // e.g. "USR-001"
  name: string
  email: string
  role: UserRole
  is_active: boolean
  created_date: string                 // ISO 8601
  last_login: string                   // ISO 8601
}

export type AuditActionType =
  | "received"
  | "signals_computed"
  | "recommendation_made"
  | "approved"
  | "applied"
  | "escalated"
  | "held"
  | "overridden"
  | "annotated"
  | "document_uploaded"
  | "contact_logged"
  | "returned"
  | "governance_review_recorded"
  | "anomaly_flagged"
  | "config_change_proposed"
  | "config_change_approved"
  | "config_change_rejected"
  | "config_change_deployed"
  | "config_change_rolled_back"
  | "sla_breached"

export interface AuditLogEntry {
  log_id: number
  payment_id: string
  action_type: AuditActionType
  actor: string                        // display name; "system" for automated actions
  actor_user_id: string                // empty for system-generated actions
  details: Record<string, unknown> | null
  timestamp: string                    // ISO 8601
}

export interface ConfigurationThreshold {
  parameter_name: string
  parameter_value: string
  description: string
  effective_date: string               // ISO 8601
}
