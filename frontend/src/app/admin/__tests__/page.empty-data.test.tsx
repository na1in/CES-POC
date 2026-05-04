/**
 * CES-37 — Admin Dashboard: empty data tests
 *
 * Verifies charts render gracefully when a scenario has 0 payments,
 * showing "No data for this scenario" instead of broken chart renders.
 */

import { render, screen, fireEvent } from "@testing-library/react"
import { useRouter } from "next/navigation"

jest.mock("recharts", () => {
  const React = require("react")
  const Passthrough = ({ children }: { children?: React.ReactNode }) => React.createElement("div", null, children)
  return {
    LineChart: Passthrough,
    BarChart: Passthrough,
    PieChart: Passthrough,
    Line: () => null,
    Bar: () => null,
    Pie: () => null,
    Cell: () => null,
    XAxis: () => null,
    YAxis: () => null,
    CartesianGrid: () => null,
    Tooltip: () => null,
    Legend: () => null,
    ResponsiveContainer: Passthrough,
  }
})

// Scenario 4 has volume=37 in real data — override to 0 for this suite
jest.mock("../../../mocks/analytics", () => {
  const actual = jest.requireActual("../../../mocks/analytics")
  return {
    ...actual,
    mockAdminAnalytics: {
      ...actual.mockAdminAnalytics,
      scenario_4: {
        ...actual.mockAdminAnalytics.scenario_4,
        volume: 0,
        override_count: 0,
      },
    },
  }
})

jest.mock("next/navigation", () => ({
  useRouter: jest.fn(),
}))

beforeEach(() => {
  ;(useRouter as jest.Mock).mockReturnValue({ push: jest.fn() })
})

import AdminDashboardPage from "@/app/admin/page"

// ── Zero-volume scenario ───────────────────────────────────────────────────────

describe("Admin Dashboard — zero-volume scenario", () => {
  function renderOnScenario4() {
    render(<AdminDashboardPage />)
    fireEvent.click(screen.getByRole("button", { name: "Scenario 4" }))
  }

  it("renders without crashing on a 0-volume scenario", () => {
    expect(() => renderOnScenario4()).not.toThrow()
  })

  it("shows 'No data for this scenario' for each of the 4 charts", () => {
    renderOnScenario4()
    const messages = screen.getAllByText("No data for this scenario")
    expect(messages).toHaveLength(4)
  })

  it("shows 0 for both volume and override count tiles", () => {
    renderOnScenario4()
    // volume=0 and override_count=0 in this mock — both stat tiles show "0"
    expect(screen.getAllByText("0").length).toBeGreaterThanOrEqual(2)
  })

  it("still shows all chart titles", () => {
    renderOnScenario4()
    expect(screen.getByText("Case Volume Trend")).toBeInTheDocument()
    expect(screen.getByText("Decision Distribution")).toBeInTheDocument()
    expect(screen.getByText("Override Rate by Confidence Band")).toBeInTheDocument()
    expect(screen.getByText("Confidence Score Histogram")).toBeInTheDocument()
  })

  it("still shows all tabs", () => {
    renderOnScenario4()
    expect(screen.getByRole("button", { name: "All" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Scenario 4" })).toBeInTheDocument()
  })

  it("switching back to All removes the empty-state messages", () => {
    renderOnScenario4()
    fireEvent.click(screen.getByRole("button", { name: "All" }))
    expect(screen.queryByText("No data for this scenario")).not.toBeInTheDocument()
  })
})
