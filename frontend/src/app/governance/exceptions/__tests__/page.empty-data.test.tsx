/**
 * CES-36 — Exception Dashboard: empty data tests
 *
 * Verifies each section renders its empty state message when the API
 * returns no SLA breaches, no anomaly flags, and no pending change requests.
 */

import { render, screen } from "@testing-library/react"
import { useRouter } from "next/navigation"

jest.mock("../../../../mocks/exceptions", () => ({
  mockSlaBreachedPayments: [],
  mockAnomalyFlags: [],
  mockPendingChangeRequests: [],
}))

jest.mock("next/navigation", () => ({
  useRouter: jest.fn(),
}))

beforeEach(() => {
  ;(useRouter as jest.Mock).mockReturnValue({ push: jest.fn() })
})

import ExceptionDashboardPage from "@/app/governance/exceptions/page"

// ── Empty states ───────────────────────────────────────────────────────────────

describe("Exception Dashboard — empty data", () => {
  it("renders without crashing when all sections are empty", () => {
    expect(() => render(<ExceptionDashboardPage />)).not.toThrow()
  })

  it("shows SLA empty state when no breached payments", () => {
    render(<ExceptionDashboardPage />)
    expect(screen.getByText(/No SLA breaches — all escalations resolved within deadline/i)).toBeInTheDocument()
  })

  it("shows anomaly empty state when no anomaly flags", () => {
    render(<ExceptionDashboardPage />)
    expect(screen.getByText(/No anomaly flags for this period/i)).toBeInTheDocument()
  })

  it("shows config change empty state when no pending requests", () => {
    render(<ExceptionDashboardPage />)
    expect(screen.getByText(/No config changes pending approval/i)).toBeInTheDocument()
  })

  it("does not render SLA table headers when section is empty", () => {
    render(<ExceptionDashboardPage />)
    expect(screen.queryByText("Time Since Breach")).not.toBeInTheDocument()
  })

  it("does not render anomaly table headers when section is empty", () => {
    render(<ExceptionDashboardPage />)
    expect(screen.queryByText("Flagged By")).not.toBeInTheDocument()
  })

  it("does not render config change table headers when section is empty", () => {
    render(<ExceptionDashboardPage />)
    expect(screen.queryByText("Proposed Value")).not.toBeInTheDocument()
  })

  it("still shows all three section headings", () => {
    render(<ExceptionDashboardPage />)
    expect(screen.getByText("SLA Breached Cases")).toBeInTheDocument()
    expect(screen.getByText("Anomaly Flags")).toBeInTheDocument()
    expect(screen.getByText("Config Changes Pending Approval")).toBeInTheDocument()
  })

  it("shows zero count badge on SLA section", () => {
    render(<ExceptionDashboardPage />)
    const badges = screen.getAllByText("0")
    expect(badges.length).toBeGreaterThanOrEqual(1)
  })

  it("still shows the page heading", () => {
    render(<ExceptionDashboardPage />)
    expect(screen.getByRole("heading", { name: /Exception Dashboard/i })).toBeInTheDocument()
  })

  it("still shows footer with Audit Active", () => {
    render(<ExceptionDashboardPage />)
    expect(screen.getByText(/Audit Active/i)).toBeInTheDocument()
  })
})
