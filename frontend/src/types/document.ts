export type DocumentType =
  | "supporting_evidence"
  | "sender_correspondence"
  | "bank_statement"
  | "fraud_report"
  | "policy_document"
  | "other"

export interface CaseDocument {
  document_id: number
  payment_id: string
  uploaded_by: string                  // user_id
  file_name: string
  file_type: string                    // MIME type e.g. "application/pdf"
  file_size_bytes: number
  storage_path: string
  document_type: DocumentType
  description: string
  uploaded_at: string                  // ISO 8601
  is_deleted: boolean
}
