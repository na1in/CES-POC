import type { Payment } from "@/types/payment"
import type { PaymentRecommendation } from "@/types/recommendation"
import type { PaymentSignals } from "@/types/signals"
import type { AuditLogEntry, ConfigurationThreshold } from "@/types/user"
import type { CaseAnnotation } from "@/types/annotation"

export interface PaymentListItem {
  payment: Payment
  recommendation: PaymentRecommendation | null
  signals: PaymentSignals | null
}

export interface PaymentListResponse {
  data: PaymentListItem[]
  total: number
  page: number
  page_size: number
}

export interface PaymentDetailResponse {
  payment: Payment
  recommendation: PaymentRecommendation | null
  signals: PaymentSignals | null
  audit_logs: AuditLogEntry[]
  annotations: CaseAnnotation[]
}

export interface ThresholdsResponse {
  thresholds: ConfigurationThreshold[]
}
