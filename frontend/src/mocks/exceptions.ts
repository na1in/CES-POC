import type { SlaBreachedPayment, AnomalyFlag, ConfigChangeRequest } from "@/types/governance"

export const mockSlaBreachedPayments: SlaBreachedPayment[] = [
  {
    payment_id: "PMT-008",
    sender_name: "Summit Risk Advisors",
    amount: 1200000,
    scenario: "Scenario 3",
    investigation_due_date: "2026-04-17T23:59:59.000Z",
    investigator: "Damien Okafor",
  },
  {
    payment_id: "PMT-011",
    sender_name: "Crestwood Capital LLC",
    amount: 875000,
    scenario: "Scenario 4",
    investigation_due_date: "2026-04-20T23:59:59.000Z",
    investigator: "Damien Okafor",
  },
  {
    payment_id: "PMT-014",
    sender_name: "Horizon Benefits Group",
    amount: 320000,
    scenario: "Scenario 2",
    investigation_due_date: "2026-04-22T23:59:59.000Z",
    investigator: "Unassigned",
  },
]

export const mockAnomalyFlags: AnomalyFlag[] = [
  {
    anomaly_id: "ANO-001",
    metric: "Override Rate",
    description: "Override rate spiked to 14.2% on 2026-04-24, more than 2× the 30-day average of 6.8%.",
    period: "2026-04-24",
    flagged_by: "Lorraine Chen",
    status: "investigating",
    resolution_notes: "Marcus reviewing scenario 3 override patterns. Preliminary finding: 3 large wires from new corporate clients triggered analyst overrides due to unfamiliar entity names.",
    created_at: "2026-04-25T08:30:00.000Z",
  },
  {
    anomaly_id: "ANO-002",
    metric: "Auto-Apply Rate",
    description: "Auto-apply rate dropped to 38% week of 2026-04-14, against baseline of 62%.",
    period: "2026-04-14 – 2026-04-20",
    flagged_by: "Lorraine Chen",
    status: "open",
    resolution_notes: null,
    created_at: "2026-04-21T09:00:00.000Z",
  },
  {
    anomaly_id: "ANO-003",
    metric: "SLA Breach Count",
    description: "3 SLA breaches in 7 days — above the threshold of 1 per week.",
    period: "2026-04-18 – 2026-04-24",
    flagged_by: "System",
    status: "open",
    resolution_notes: null,
    created_at: "2026-04-24T23:00:00.000Z",
  },
]

export const mockPendingChangeRequests: ConfigChangeRequest[] = [
  {
    request_id: "CHG-007",
    parameter_name: "name_match_auto_apply",
    current_value: "90%",
    proposed_value: "93%",
    proposed_by: "Marcus Webb",
    proposed_at: "2026-04-26T10:15:00.000Z",
    status: "pending",
    review_comment: null,
  },
  {
    request_id: "CHG-008",
    parameter_name: "duplicate_window_hours",
    current_value: "72h",
    proposed_value: "48h",
    proposed_by: "Marcus Webb",
    proposed_at: "2026-04-27T14:00:00.000Z",
    status: "pending",
    review_comment: null,
  },
]
