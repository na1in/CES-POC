/**
 * CES-35 — Compliance Export: empty data tests
 *
 * Verifies the page renders without crash when there are no governance reviews
 * (no last export notice to display).
 */

import { render, screen } from "@testing-library/react"
import { useRouter } from "next/navigation"

jest.mock("../../../../mocks/governance", () => ({
  mockGovernanceReviews: [],
}))

jest.mock("next/navigation", () => ({
  useRouter: jest.fn(),
}))

beforeEach(() => {
  ;(useRouter as jest.Mock).mockReturnValue({ push: jest.fn() })
})

import ComplianceExportPage from "@/app/governance/export/page"

// ── Empty governance reviews ───────────────────────────────────────────────────

describe("Compliance Export — no prior exports", () => {
  it("renders without crashing when governance reviews list is empty", () => {
    expect(() => render(<ComplianceExportPage />)).not.toThrow()
  })

  it("still shows the page heading", () => {
    render(<ComplianceExportPage />)
    expect(screen.getByRole("heading", { name: /Compliance Export/i })).toBeInTheDocument()
  })

  it("still shows all three scope options", () => {
    render(<ComplianceExportPage />)
    expect(screen.getByText("Decisions")).toBeInTheDocument()
    expect(screen.getByText("Override Log")).toBeInTheDocument()
    expect(screen.getByText("Config Changes")).toBeInTheDocument()
  })

  it("does not render the last export notice", () => {
    render(<ComplianceExportPage />)
    expect(screen.queryByText(/Last export/i)).not.toBeInTheDocument()
  })

  it("still renders the download button", () => {
    render(<ComplianceExportPage />)
    expect(screen.getByRole("button", { name: /Download Report/i })).toBeInTheDocument()
  })

  it("download button is still disabled with empty form", () => {
    render(<ComplianceExportPage />)
    expect(screen.getByRole("button", { name: /Download Report/i })).toBeDisabled()
  })

  it("still shows footer with Audit Active", () => {
    render(<ComplianceExportPage />)
    expect(screen.getByText(/Audit Active/i)).toBeInTheDocument()
  })
})
