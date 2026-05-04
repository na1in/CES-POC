import type { GovernanceReview } from "@/types/governance"

export const mockGovernanceReviews: GovernanceReview[] = [
  {
    review_id: "REV-003",
    period: "April 2026",
    reviewed_by: "Lorraine Chen",
    reviewed_at: "2026-04-29T14:22:00.000Z",
    notes: "All SLA targets met. Override rate within acceptable bounds.",
    export_scope: ["decisions", "override_log", "config_changes"],
  },
  {
    review_id: "REV-002",
    period: "March 2026",
    reviewed_by: "Lorraine Chen",
    reviewed_at: "2026-03-31T09:05:00.000Z",
    notes: "Two anomaly flags raised for review.",
    export_scope: ["decisions", "override_log"],
  },
  {
    review_id: "REV-001",
    period: "February 2026",
    reviewed_by: "Lorraine Chen",
    reviewed_at: "2026-02-28T11:30:00.000Z",
    notes: null,
    export_scope: ["decisions"],
  },
]
