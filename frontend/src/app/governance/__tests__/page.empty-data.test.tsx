/**
 * CES-34 — Governance Dashboard: empty data tests
 *
 * Verifies charts render without errors when API returns empty arrays
 * for payment method breakdown, override trend, and confidence histogram.
 */

import { render, screen } from "@testing-library/react"
import { useRouter } from "next/navigation"

jest.mock("recharts", () => {
  const React = require("react")
  const Passthrough = ({ children }: { children?: React.ReactNode }) => React.createElement("div", null, children)
  return {
    BarChart: Passthrough,
    LineChart: Passthrough,
    Bar: () => null,
    Line: () => null,
    XAxis: () => null,
    YAxis: () => null,
    CartesianGrid: () => null,
    Tooltip: () => null,
    ResponsiveContainer: Passthrough,
  }
})

jest.mock("../../../mocks/analytics", () => ({
  mockAnalyticsDecisions: {
    date_from: "2026-04-01",
    date_to: "2026-04-29",
    summary: {
      auto_applied_by_ai: 0,
      applied_after_human_review: 0,
      held_pending_review: 0,
      escalated_by_ai: 0,
      escalated_by_human: 0,
      human_overrides: 0,
      override_rate_pct: 0,
      total_payments: 0,
    },
    by_payment_method: [],
    override_rate_trend: [],
    confidence_histogram: [],
    sla_adherence: {
      resolved_before_breach: 0,
      total_escalations: 0,
      adherence_pct: 0,
    },
  },
}))

jest.mock("next/navigation", () => ({
  useRouter: jest.fn(),
}))

beforeEach(() => {
  ;(useRouter as jest.Mock).mockReturnValue({ push: jest.fn() })
})

import GovernancePage from "@/app/governance/page"

// ── Empty data rendering ───────────────────────────────────────────────────────

describe("Governance — empty data", () => {
  it("renders without crashing when all chart arrays are empty", () => {
    expect(() => render(<GovernancePage />)).not.toThrow()
  })

  it("still shows all 6 metric card labels", () => {
    render(<GovernancePage />)
    expect(screen.getByText("Auto-Applied by AI")).toBeInTheDocument()
    expect(screen.getByText("Applied after Human Review")).toBeInTheDocument()
    expect(screen.getByText("Held Pending Review")).toBeInTheDocument()
    expect(screen.getByText("Escalated by AI")).toBeInTheDocument()
    expect(screen.getByText("Escalated by Human")).toBeInTheDocument()
    expect(screen.getByText("Human Overrides")).toBeInTheDocument()
  })

  it("shows zero values for all metric cards", () => {
    render(<GovernancePage />)
    const zeros = screen.getAllByText("0")
    expect(zeros.length).toBeGreaterThanOrEqual(6)
  })

  it("still renders Payment Method Breakdown section with empty data", () => {
    render(<GovernancePage />)
    expect(screen.getByText("Payment Method Breakdown")).toBeInTheDocument()
  })

  it("still renders Override Rate Trend section with empty data", () => {
    render(<GovernancePage />)
    expect(screen.getByText("Override Rate Trend")).toBeInTheDocument()
  })

  it("still renders Confidence Score Histogram section with empty data", () => {
    render(<GovernancePage />)
    expect(screen.getByText("Confidence Score Histogram")).toBeInTheDocument()
  })

  it("shows SLA Adherence with 0% when no escalations", () => {
    render(<GovernancePage />)
    expect(screen.getByText("0%")).toBeInTheDocument()
  })

  it("shows 0 of 0 cases for SLA adherence", () => {
    render(<GovernancePage />)
    expect(screen.getByText("0 of 0 cases")).toBeInTheDocument()
  })

  it("still shows page heading", () => {
    render(<GovernancePage />)
    expect(screen.getByRole("heading", { name: /Governance Dashboard/i })).toBeInTheDocument()
  })

  it("still shows footer with Audit Active", () => {
    render(<GovernancePage />)
    expect(screen.getByText(/Audit Active/i)).toBeInTheDocument()
  })
})
