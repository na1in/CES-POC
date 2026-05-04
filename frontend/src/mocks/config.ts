import type { ConfigChangeRequest, ThresholdVersionEntry } from "@/types/governance"

// ── Change requests ────────────────────────────────────────────────────────────

export const mockChangeRequests: ConfigChangeRequest[] = [
  {
    request_id: "CR-005",
    parameter_name: "name_match_auto_apply",
    current_value: "90%",
    proposed_value: "93%",
    rationale: "Override rate in 90–92% band has dropped from 3% to 11% over 4 weeks. Raising threshold reduces false auto-applies.",
    projected_impact: "Est. 8% reduction in auto-apply volume, 2% increase in HOLD queue.",
    proposed_by: "Marcus Webb",
    proposed_at: "2026-04-28T09:00:00.000Z",
    status: "pending",
    reviewed_by: null,
    reviewed_at: null,
    review_comment: null,
    deployed_at: null,
    deployed_by: null,
  },
  {
    request_id: "CR-004",
    parameter_name: "duplicate_window_hours",
    current_value: "72h",
    proposed_value: "96h",
    rationale: "4 duplicate payments occurred just outside the 72-hour window last quarter. Extending prevents missed duplicates.",
    projected_impact: "Est. 12% increase in duplicate detection rate.",
    proposed_by: "Marcus Webb",
    proposed_at: "2026-04-20T14:30:00.000Z",
    status: "approved",
    reviewed_by: "Lorraine Chen",
    reviewed_at: "2026-04-22T10:00:00.000Z",
    review_comment: "Approved — risk analysis confirms wider window is safe.",
    deployed_at: null,
    deployed_by: null,
  },
  {
    request_id: "CR-003",
    parameter_name: "amount_tolerance_auto",
    current_value: "2%",
    proposed_value: "3%",
    rationale: "Rounding differences in ACH batch processing cause borderline rejections. 3% better matches real-world variance.",
    projected_impact: null,
    proposed_by: "Marcus Webb",
    proposed_at: "2026-03-15T11:00:00.000Z",
    status: "deployed",
    reviewed_by: "Lorraine Chen",
    reviewed_at: "2026-03-17T09:00:00.000Z",
    review_comment: "Approved with monitoring requirement.",
    deployed_at: "2026-03-18T08:00:00.000Z",
    deployed_by: "Marcus Webb",
  },
  {
    request_id: "CR-002",
    parameter_name: "name_gray_zone_upper",
    current_value: "95%",
    proposed_value: "92%",
    rationale: "Lowering upper boundary reduces unnecessary LLM calls for obvious matches and cuts latency.",
    projected_impact: "Est. 15% reduction in LLM calls.",
    proposed_by: "Marcus Webb",
    proposed_at: "2026-02-01T10:00:00.000Z",
    status: "rejected",
    reviewed_by: "Lorraine Chen",
    reviewed_at: "2026-02-03T14:00:00.000Z",
    review_comment: "Rejected — 92% boundary needs further validation with compliance team before deployment.",
    deployed_at: null,
    deployed_by: null,
  },
  {
    request_id: "CR-001",
    parameter_name: "name_gray_zone_upper",
    current_value: "95%",
    proposed_value: "92%",
    rationale: "Initial proposal to lower upper gray zone boundary after audit findings showed excessive LLM usage.",
    projected_impact: null,
    proposed_by: "Marcus Webb",
    proposed_at: "2026-01-20T09:00:00.000Z",
    status: "deployed",
    reviewed_by: "Lorraine Chen",
    reviewed_at: "2026-01-22T11:00:00.000Z",
    review_comment: "Approved for initial deployment.",
    deployed_at: "2026-02-03T00:00:00.000Z",
    deployed_by: "Marcus Webb",
  },
]

// ── Version history ────────────────────────────────────────────────────────────

export const mockVersionHistory: Record<string, ThresholdVersionEntry[]> = {
  name_match_auto_apply: [
    { version_id: "VH-003", parameter_name: "name_match_auto_apply", old_value: "88%", new_value: "90%", changed_by: "Marcus Webb", changed_at: "2026-01-15T00:00:00.000Z", change_request_id: null },
  ],
  name_match_hold: [
    { version_id: "VH-002", parameter_name: "name_match_hold", old_value: "70%", new_value: "75%", changed_by: "Marcus Webb", changed_at: "2026-01-15T00:00:00.000Z", change_request_id: null },
  ],
  name_gray_zone_lower: [
    { version_id: "VH-001", parameter_name: "name_gray_zone_lower", old_value: "65%", new_value: "70%", changed_by: "Marcus Webb", changed_at: "2026-01-15T00:00:00.000Z", change_request_id: null },
  ],
  name_gray_zone_upper: [
    { version_id: "VH-006", parameter_name: "name_gray_zone_upper", old_value: "95%", new_value: "92%", changed_by: "Marcus Webb", changed_at: "2026-02-03T00:00:00.000Z", change_request_id: "CR-001" },
    { version_id: "VH-005", parameter_name: "name_gray_zone_upper", old_value: "92%", new_value: "95%", changed_by: "Marcus Webb", changed_at: "2026-01-15T00:00:00.000Z", change_request_id: null },
  ],
  amount_tolerance_auto: [
    { version_id: "VH-008", parameter_name: "amount_tolerance_auto", old_value: "2%", new_value: "3%", changed_by: "Marcus Webb", changed_at: "2026-03-18T08:00:00.000Z", change_request_id: "CR-003" },
    { version_id: "VH-007", parameter_name: "amount_tolerance_auto", old_value: "1%", new_value: "2%", changed_by: "Marcus Webb", changed_at: "2026-01-15T00:00:00.000Z", change_request_id: null },
  ],
  duplicate_window_hours: [
    { version_id: "VH-004", parameter_name: "duplicate_window_hours", old_value: "48h", new_value: "72h", changed_by: "Marcus Webb", changed_at: "2026-01-15T00:00:00.000Z", change_request_id: null },
  ],
  duplicate_amount_tolerance_cents: [
    { version_id: "VH-009", parameter_name: "duplicate_amount_tolerance_cents", old_value: "$1.00", new_value: "$2.00", changed_by: "Marcus Webb", changed_at: "2026-03-10T00:00:00.000Z", change_request_id: null },
  ],
  multi_period_tolerance: [
    { version_id: "VH-010", parameter_name: "multi_period_tolerance", old_value: "3%", new_value: "5%", changed_by: "Marcus Webb", changed_at: "2026-01-15T00:00:00.000Z", change_request_id: null },
  ],
}

// ── Changed-by map (augments mockThresholds which lacks this field) ────────────

export const thresholdChangedBy: Record<string, string> = {
  name_match_auto_apply:           "Marcus Webb",
  name_match_hold:                 "Marcus Webb",
  name_gray_zone_lower:            "Marcus Webb",
  name_gray_zone_upper:            "Marcus Webb",
  amount_tolerance_auto:           "Marcus Webb",
  duplicate_window_hours:          "Marcus Webb",
  duplicate_amount_tolerance_cents: "Marcus Webb",
  multi_period_tolerance:          "Marcus Webb",
}
