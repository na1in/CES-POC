import type { ScenarioRoute } from "@/types/recommendation"

/**
 * Human-readable scenario names. Single source of truth — the queue dashboard,
 * admin analytics, override analysis, case detail and exception dashboard all
 * read from here so a scenario is never rendered as a raw "scenario_4".
 */
export const SCENARIO_LABEL: Record<ScenarioRoute, string> = {
  scenario_1: "Policy Match",
  scenario_2: "Cust. Match",
  scenario_3: "High Variance",
  scenario_4: "No Match",
  scenario_5: "Duplicate",
}

/** Compact form for chart axes and table badges where space is tight. */
export const SCENARIO_SHORT_LABEL: Record<ScenarioRoute, string> = {
  scenario_1: "S1",
  scenario_2: "S2",
  scenario_3: "S3",
  scenario_4: "S4",
  scenario_5: "S5",
}

export const ALL_SCENARIOS: ScenarioRoute[] = [
  "scenario_1", "scenario_2", "scenario_3", "scenario_4", "scenario_5",
]

function isScenarioRoute(route: string): route is ScenarioRoute {
  return route in SCENARIO_LABEL
}

/**
 * Label an arbitrary route string coming off the API, which types it as
 * `string | null`. Falls back to the raw value so an unrecognised scenario
 * is still visible rather than silently blank.
 */
export function scenarioLabel(route: string | null | undefined, fallback = "—"): string {
  if (!route) return fallback
  return isScenarioRoute(route) ? SCENARIO_LABEL[route] : route
}

/** Compact variant of {@link scenarioLabel}. */
export function scenarioShortLabel(route: string | null | undefined, fallback = "—"): string {
  if (!route) return fallback
  return isScenarioRoute(route) ? SCENARIO_SHORT_LABEL[route] : route
}
