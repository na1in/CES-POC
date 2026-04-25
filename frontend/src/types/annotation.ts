export type AnnotationType =
  | "case_note"
  | "override_reason"
  | "contact_record"
  | "investigation_note"

export interface CaseAnnotation {
  annotation_id: number
  payment_id: string
  author_user_id: string
  annotation_type: AnnotationType
  content: string
  // Populated only when annotation_type = "contact_record"
  contact_method: string               // phone, email, letter
  contact_outcome: string              // reached, no_answer, voicemail, bounced
  contacted_party: string              // sender, bank, third party name
  created_at: string                   // ISO 8601
}
