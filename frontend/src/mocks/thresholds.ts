import type { ConfigurationThreshold } from "@/types/user"

export const mockThresholds: ConfigurationThreshold[] = [
  {
    parameter_name: "name_match_auto_apply",
    parameter_value: "90%",
    description: "Min name similarity for Scenario 1 auto-apply",
    effective_date: "2026-01-15T00:00:00.000Z",
  },
  {
    parameter_name: "name_match_hold",
    parameter_value: "75%",
    description: "Hold vs escalate boundary for name matching",
    effective_date: "2026-01-15T00:00:00.000Z",
  },
  {
    parameter_name: "name_gray_zone_lower",
    parameter_value: "70%",
    description: "Below this score: skip LLM, treat as clear mismatch",
    effective_date: "2026-01-15T00:00:00.000Z",
  },
  {
    parameter_name: "name_gray_zone_upper",
    parameter_value: "92%",
    description: "Above this score: skip LLM, treat as clear match",
    effective_date: "2026-02-03T00:00:00.000Z",
  },
  {
    parameter_name: "amount_tolerance_auto",
    parameter_value: "2%",
    description: "Max variance for Scenario 1 auto-apply",
    effective_date: "2026-01-15T00:00:00.000Z",
  },
  {
    parameter_name: "duplicate_window_hours",
    parameter_value: "72h",
    description: "Lookback window for duplicate payment detection",
    effective_date: "2026-01-15T00:00:00.000Z",
  },
  {
    parameter_name: "duplicate_amount_tolerance_cents",
    parameter_value: "$2.00",
    description: "Max amount difference to still classify as a duplicate",
    effective_date: "2026-03-10T00:00:00.000Z",
  },
  {
    parameter_name: "multi_period_tolerance",
    parameter_value: "5%",
    description: "Tolerance when detecting multi-period bundled payments",
    effective_date: "2026-01-15T00:00:00.000Z",
  },
]

export const mockUsers = [
  { user_id: "USR-001", name: "Priya Venkataraman", role: "analyst" as const },
  { user_id: "USR-002", name: "Damien Okafor", role: "investigator" as const },
  { user_id: "USR-003", name: "Lorraine Chen", role: "director" as const },
  { user_id: "USR-004", name: "Marcus Webb", role: "admin" as const },
]
