const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"

function getToken(): string | null {
  if (typeof window === "undefined") return null
  return localStorage.getItem("ces_token")
}

async function apiFetch<T = unknown>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {
    ...(options.headers as Record<string, string>),
  }
  if (token) headers["Authorization"] = `Bearer ${token}`
  if (options.body && typeof options.body === "string") {
    headers["Content-Type"] = "application/json"
  }

  const res = await fetch(`${BASE}${path}`, { ...options, headers })
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText)
    throw new Error(text || `HTTP ${res.status}`)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

// ── Auth ─────────────────────────────────────────────────────────────────────

export interface LoginResponse {
  access_token: string
  token_type: string
  role: string
  name: string
}

export function login(userId: string): Promise<LoginResponse> {
  const body = new URLSearchParams({ username: userId, password: "x" })
  return apiFetch<LoginResponse>("/api/auth/token", {
    method: "POST",
    body: body.toString(),
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
  })
}

export interface MeResponse {
  user_id: string
  name: string
  role: string
}

export function me(): Promise<MeResponse> {
  return apiFetch<MeResponse>("/api/me")
}

// ── Payments ─────────────────────────────────────────────────────────────────

export interface PaymentRow {
  payment_id: string
  amount: number
  sender_name: string
  sender_account: string
  payment_method: string
  payment_date: string
  status: string
  matched_customer_id: string | null
  matched_policy_id: string | null
  investigation_due_date: string | null
  sla_breached: boolean
  created_timestamp: string
  recommendation: string | null
  confidence_score: number | null
  scenario_route: string | null
  requires_human_approval: boolean | null
  decision_attribution: string | null
  has_risk_flags: boolean | null
}

export interface PaymentsListResponse {
  payments: PaymentRow[]
  total: number
  page: number
  page_size: number
}

export interface PaymentListParams {
  status?: string
  scenario?: string
  search?: string
  sort_by?: string
  page?: number
  page_size?: number
}

export function listPayments(params: PaymentListParams = {}): Promise<PaymentsListResponse> {
  const qs = new URLSearchParams()
  if (params.status) qs.set("status", params.status)
  if (params.scenario) qs.set("scenario", params.scenario)
  if (params.search) qs.set("search", params.search)
  if (params.sort_by) qs.set("sort_by", params.sort_by)
  if (params.page) qs.set("page", String(params.page))
  if (params.page_size) qs.set("page_size", String(params.page_size))
  const q = qs.toString()
  return apiFetch<PaymentsListResponse>(`/api/payments${q ? `?${q}` : ""}`)
}

export function getPayment(id: string): Promise<PaymentDetail> {
  return apiFetch<PaymentDetail>(`/api/payments/${id}`)
}

export interface PaymentDetail {
  payment: Record<string, unknown>
  signals: Record<string, unknown> | null
  recommendation: Record<string, unknown> | null
  audit_trail: AuditEntry[]
  annotations: AnnotationEntry[]
  documents: DocumentEntry[]
}

export interface AuditEntry {
  log_id: string
  payment_id: string
  action_type: string
  actor: string
  actor_user_id: string | null
  details: string | null
  timestamp: string
}

export interface AnnotationEntry {
  annotation_id: string
  payment_id: string
  author_user_id: string
  annotation_type: string
  content: string
  contact_method: string | null
  contact_outcome: string | null
  contacted_party: string | null
  created_at: string
}

export interface DocumentEntry {
  document_id: string
  payment_id: string
  filename: string
  document_type: string
  content_type: string
  file_size_bytes: number
  uploaded_by: string
  created_at: string
  deleted_at: string | null
}

// ── Approval actions ──────────────────────────────────────────────────────────

export function approvePayment(id: string, notes?: string): Promise<unknown> {
  return apiFetch(`/api/payments/${id}/approve`, {
    method: "POST",
    body: JSON.stringify({ notes: notes ?? null }),
  })
}

export function rejectPayment(id: string, notes?: string): Promise<unknown> {
  return apiFetch(`/api/payments/${id}/reject`, {
    method: "POST",
    body: JSON.stringify({ notes: notes ?? null }),
  })
}

export function overridePayment(id: string, action: string, reason: string): Promise<unknown> {
  return apiFetch(`/api/payments/${id}/override`, {
    method: "POST",
    body: JSON.stringify({ override_action: action, reason }),
  })
}

export function returnPayment(id: string, notes?: string): Promise<unknown> {
  return apiFetch(`/api/payments/${id}/return`, {
    method: "POST",
    body: JSON.stringify({ notes: notes ?? null }),
  })
}

export function reprocessPayment(id: string): Promise<unknown> {
  return apiFetch(`/api/payments/${id}/reprocess`, { method: "POST" })
}

// ── Annotations ───────────────────────────────────────────────────────────────

export function addAnnotation(
  id: string,
  body: { annotation_type: string; content: string },
): Promise<unknown> {
  return apiFetch(`/api/payments/${id}/annotations`, {
    method: "POST",
    body: JSON.stringify(body),
  })
}

// ── Settings / thresholds ─────────────────────────────────────────────────────

export interface Threshold {
  parameter_name: string
  parameter_value: number
  description: string
  effective_date: string
  changed_by: string | null
}

export function getThresholds(): Promise<{ thresholds: Threshold[] }> {
  return apiFetch<{ thresholds: Threshold[] }>("/api/settings/thresholds")
}

export interface ChangeRequest {
  change_id: number
  parameter_name: string
  proposed_value: number
  current_value: number
  rationale: string
  projected_impact: string | null
  status: string
  proposed_by: string
  approved_by: string | null
  review_comment: string | null
  proposed_at: string
  reviewed_at: string | null
  deployed_at: string | null
}

export function getChangeRequests(): Promise<{ change_requests: ChangeRequest[] }> {
  return apiFetch<{ change_requests: ChangeRequest[] }>("/api/settings/change-requests")
}

export function approveChangeRequest(id: number): Promise<unknown> {
  return apiFetch(`/api/settings/change-requests/${id}/approve`, { method: "POST" })
}

export function rejectChangeRequest(id: number, comment: string): Promise<unknown> {
  return apiFetch(`/api/settings/change-requests/${id}/reject`, {
    method: "POST",
    body: JSON.stringify({ comment }),
  })
}

export function deployChangeRequest(id: number): Promise<unknown> {
  return apiFetch(`/api/settings/change-requests/${id}/deploy`, { method: "POST" })
}

// ── Analytics ─────────────────────────────────────────────────────────────────

export interface AnalyticsDecisions {
  summary: {
    auto_applied: number
    applied_human_review: number
    applied_human_override: number
    held_pending_review: number
    escalated_by_ai: number
    escalated_by_human: number
    human_overrides: number
    returned: number
    total_processed: number
    override_rate_pct: number
  }
  by_scenario: Array<{
    scenario_route: string
    volume: number
    avg_confidence: number
    ai_autonomous: number
    human_confirmed: number
    human_override: number
    override_count: number
    apply_count: number
    hold_count: number
    escalate_count: number
  }>
  by_payment_method: Array<{
    payment_method: string
    volume: number
    ai_autonomous: number
    human_confirmed: number
    human_override: number
  }>
  confidence_histogram: Record<string, number>
}

export function getAnalyticsDecisions(params?: {
  from_date?: string
  to_date?: string
  payment_method?: string
}): Promise<AnalyticsDecisions> {
  const qs = new URLSearchParams()
  if (params?.from_date) qs.set("from_date", params.from_date)
  if (params?.to_date) qs.set("to_date", params.to_date)
  if (params?.payment_method) qs.set("payment_method", params.payment_method)
  const q = qs.toString()
  return apiFetch<AnalyticsDecisions>(`/api/analytics/decisions${q ? `?${q}` : ""}`)
}

export interface OverrideRow {
  payment_id: string
  sender_name: string
  amount: number
  payment_method: string
  payment_date: string
  status: string
  scenario_route: string | null
  original_recommendation: string | null
  confidence_score: number | null
  decision_attribution: string | null
  override_reason: string | null
  overridden_by: string | null
  overridden_at: string | null
}

export function getOverrides(params?: {
  scenario?: string
  confidence_band?: string
  from_date?: string
  to_date?: string
  page?: number
  page_size?: number
}): Promise<{ overrides: OverrideRow[]; total: number; page: number; page_size: number }> {
  const qs = new URLSearchParams()
  if (params?.scenario) qs.set("scenario", params.scenario)
  if (params?.confidence_band) qs.set("confidence_band", params.confidence_band)
  if (params?.from_date) qs.set("from_date", params.from_date)
  if (params?.to_date) qs.set("to_date", params.to_date)
  if (params?.page) qs.set("page", String(params.page))
  if (params?.page_size) qs.set("page_size", String(params.page_size))
  const q = qs.toString()
  return apiFetch(`/api/analytics/overrides${q ? `?${q}` : ""}`)
}

export interface ThresholdHistory {
  history_id: number
  parameter_name: string
  old_value: number | null
  new_value: number
  changed_by: string
  effective_from: string
  effective_to: string | null
  change_id: number | null
}

export function getThresholdHistory(param?: string): Promise<{ history: ThresholdHistory[] }> {
  const q = param ? `?parameter_name=${encodeURIComponent(param)}` : ""
  return apiFetch<{ history: ThresholdHistory[] }>(`/api/settings/thresholds/history${q}`)
}

export function createChangeRequest(body: {
  parameter_name: string
  proposed_value: number | string
  rationale: string
  projected_impact?: string
}): Promise<unknown> {
  return apiFetch("/api/settings/change-requests", {
    method: "POST",
    body: JSON.stringify(body),
  })
}

export function rollbackChangeRequest(id: number): Promise<unknown> {
  return apiFetch(`/api/settings/change-requests/${id}/rollback`, { method: "POST" })
}

// ── Governance ────────────────────────────────────────────────────────────────

export interface AnomalyFlag {
  flag_id: number
  metric_name: string
  scenario_type: string | null
  description: string
  period_start: string
  period_end: string
  flagged_by: string
  assigned_to: string | null
  status: string
  resolution_notes: string | null
  flagged_at: string
  resolved_at: string | null
}

export function getAnomalies(status?: string): Promise<{ anomalies: AnomalyFlag[] }> {
  const q = status ? `?status=${encodeURIComponent(status)}` : ""
  return apiFetch<{ anomalies: AnomalyFlag[] }>(`/api/governance/anomalies${q}`)
}

export function updateAnomaly(id: number, body: { status: string; resolution_notes?: string }): Promise<unknown> {
  return apiFetch(`/api/governance/anomalies/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  })
}

export function getGovernanceExport(params: { from_date: string; to_date: string; scope?: string }): Promise<unknown> {
  const qs = new URLSearchParams({ from_date: params.from_date, to_date: params.to_date })
  if (params.scope) qs.set("scope", params.scope)
  return apiFetch(`/api/governance/export?${qs.toString()}`)
}
