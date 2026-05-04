/**
 * CES-35 — Compliance Export tests
 *
 * Covers: page structure, date range inputs, scope checkboxes, Select All,
 * download button disabled state, file download triggered, last export notice,
 * navigation, role switching, footer.
 */

import { render, screen, fireEvent } from "@testing-library/react"
import { useRouter } from "next/navigation"
import ComplianceExportPage from "@/app/governance/export/page"
import { mockGovernanceReviews } from "@/mocks/governance"

jest.mock("next/navigation", () => ({
  useRouter: jest.fn(),
}))

const mockPush = jest.fn()

beforeEach(() => {
  mockPush.mockClear()
  ;(useRouter as jest.Mock).mockReturnValue({ push: mockPush })
})

// ── Page structure ─────────────────────────────────────────────────────────────

describe("Compliance Export — page structure", () => {
  it("renders the page heading", () => {
    render(<ComplianceExportPage />)
    expect(screen.getByRole("heading", { name: /Compliance Export/i })).toBeInTheDocument()
  })

  it("shows the page subtitle", () => {
    render(<ComplianceExportPage />)
    expect(screen.getByText(/Download an audit-ready report/i)).toBeInTheDocument()
  })

  it("shows Export Scope section label", () => {
    render(<ComplianceExportPage />)
    expect(screen.getByText(/Export Scope/i)).toBeInTheDocument()
  })

  it("shows Date Range section label", () => {
    render(<ComplianceExportPage />)
    expect(screen.getByText("Date Range")).toBeInTheDocument()
  })
})

// ── Date range inputs ─────────────────────────────────────────────────────────

describe("Compliance Export — date range inputs", () => {
  it("renders date-from input", () => {
    render(<ComplianceExportPage />)
    expect(screen.getByLabelText("Date from")).toBeInTheDocument()
  })

  it("renders date-to input", () => {
    render(<ComplianceExportPage />)
    expect(screen.getByLabelText("Date to")).toBeInTheDocument()
  })

  it("date-from starts empty", () => {
    render(<ComplianceExportPage />)
    expect(screen.getByLabelText<HTMLInputElement>("Date from").value).toBe("")
  })

  it("date-to starts empty", () => {
    render(<ComplianceExportPage />)
    expect(screen.getByLabelText<HTMLInputElement>("Date to").value).toBe("")
  })

  it("updates date-from on change", () => {
    render(<ComplianceExportPage />)
    const input = screen.getByLabelText<HTMLInputElement>("Date from")
    fireEvent.change(input, { target: { value: "2026-04-01" } })
    expect(input.value).toBe("2026-04-01")
  })

  it("updates date-to on change", () => {
    render(<ComplianceExportPage />)
    const input = screen.getByLabelText<HTMLInputElement>("Date to")
    fireEvent.change(input, { target: { value: "2026-04-30" } })
    expect(input.value).toBe("2026-04-30")
  })
})

// ── Scope checkboxes ───────────────────────────────────────────────────────────

describe("Compliance Export — scope checkboxes", () => {
  it("shows all three scope option labels", () => {
    render(<ComplianceExportPage />)
    expect(screen.getByText("Decisions")).toBeInTheDocument()
    expect(screen.getByText("Override Log")).toBeInTheDocument()
    expect(screen.getByText("Config Changes")).toBeInTheDocument()
  })

  it("shows descriptions for each option", () => {
    render(<ComplianceExportPage />)
    expect(screen.getByText(/All payment decisions with AI reasoning/i)).toBeInTheDocument()
    expect(screen.getByText(/Human overrides with reason codes/i)).toBeInTheDocument()
    expect(screen.getByText(/Threshold change requests/i)).toBeInTheDocument()
  })

  it("all checkboxes start unchecked", () => {
    render(<ComplianceExportPage />)
    screen.getAllByRole("checkbox").forEach(cb => expect(cb).not.toBeChecked())
  })

  it("clicking a checkbox checks it", () => {
    render(<ComplianceExportPage />)
    const first = screen.getAllByRole("checkbox")[0]
    fireEvent.click(first)
    expect(first).toBeChecked()
  })

  it("clicking a checked checkbox unchecks it", () => {
    render(<ComplianceExportPage />)
    const first = screen.getAllByRole("checkbox")[0]
    fireEvent.click(first)
    fireEvent.click(first)
    expect(first).not.toBeChecked()
  })

  it("shows Select All button", () => {
    render(<ComplianceExportPage />)
    expect(screen.getByText("Select All")).toBeInTheDocument()
  })

  it("Select All checks all three checkboxes", () => {
    render(<ComplianceExportPage />)
    fireEvent.click(screen.getByText("Select All"))
    screen.getAllByRole("checkbox").forEach(cb => expect(cb).toBeChecked())
  })
})

// ── Download button disabled state ─────────────────────────────────────────────

describe("Compliance Export — download button disabled state", () => {
  it("is disabled with empty form", () => {
    render(<ComplianceExportPage />)
    expect(screen.getByRole("button", { name: /Download Report/i })).toBeDisabled()
  })

  it("is disabled when only dates are set", () => {
    render(<ComplianceExportPage />)
    fireEvent.change(screen.getByLabelText("Date from"), { target: { value: "2026-04-01" } })
    fireEvent.change(screen.getByLabelText("Date to"), { target: { value: "2026-04-30" } })
    expect(screen.getByRole("button", { name: /Download Report/i })).toBeDisabled()
  })

  it("is disabled when only scope is set", () => {
    render(<ComplianceExportPage />)
    fireEvent.click(screen.getAllByRole("checkbox")[0])
    expect(screen.getByRole("button", { name: /Download Report/i })).toBeDisabled()
  })

  it("is disabled when date-from is missing", () => {
    render(<ComplianceExportPage />)
    fireEvent.change(screen.getByLabelText("Date to"), { target: { value: "2026-04-30" } })
    fireEvent.click(screen.getAllByRole("checkbox")[0])
    expect(screen.getByRole("button", { name: /Download Report/i })).toBeDisabled()
  })

  it("is disabled when date-to is missing", () => {
    render(<ComplianceExportPage />)
    fireEvent.change(screen.getByLabelText("Date from"), { target: { value: "2026-04-01" } })
    fireEvent.click(screen.getAllByRole("checkbox")[0])
    expect(screen.getByRole("button", { name: /Download Report/i })).toBeDisabled()
  })

  it("is enabled when both dates and at least one scope are set", () => {
    render(<ComplianceExportPage />)
    fireEvent.change(screen.getByLabelText("Date from"), { target: { value: "2026-04-01" } })
    fireEvent.change(screen.getByLabelText("Date to"), { target: { value: "2026-04-30" } })
    fireEvent.click(screen.getAllByRole("checkbox")[0])
    expect(screen.getByRole("button", { name: /Download Report/i })).not.toBeDisabled()
  })

  it("has opacity 0.5 when disabled", () => {
    render(<ComplianceExportPage />)
    expect(screen.getByRole("button", { name: /Download Report/i })).toHaveStyle("opacity: 0.5")
  })

  it("has opacity 1 when enabled", () => {
    render(<ComplianceExportPage />)
    fireEvent.change(screen.getByLabelText("Date from"), { target: { value: "2026-04-01" } })
    fireEvent.change(screen.getByLabelText("Date to"), { target: { value: "2026-04-30" } })
    fireEvent.click(screen.getAllByRole("checkbox")[0])
    expect(screen.getByRole("button", { name: /Download Report/i })).toHaveStyle("opacity: 1")
  })
})

// ── File download ──────────────────────────────────────────────────────────────

describe("Compliance Export — file download", () => {
  const mockCreateObjectURL = jest.fn(() => "blob:mock-url")
  const mockRevokeObjectURL = jest.fn()

  beforeAll(() => {
    global.URL.createObjectURL = mockCreateObjectURL
    global.URL.revokeObjectURL = mockRevokeObjectURL
  })

  beforeEach(() => {
    mockCreateObjectURL.mockClear()
    mockRevokeObjectURL.mockClear()
  })

  function fillAndDownload() {
    render(<ComplianceExportPage />)
    fireEvent.change(screen.getByLabelText("Date from"), { target: { value: "2026-04-01" } })
    fireEvent.change(screen.getByLabelText("Date to"), { target: { value: "2026-04-30" } })
    fireEvent.click(screen.getAllByRole("checkbox")[0])
    fireEvent.click(screen.getByRole("button", { name: /Download Report/i }))
  }

  it("calls URL.createObjectURL with a Blob when download is triggered", () => {
    fillAndDownload()
    expect(mockCreateObjectURL).toHaveBeenCalledTimes(1)
    expect(mockCreateObjectURL).toHaveBeenCalledWith(expect.any(Blob))
  })

  it("calls URL.revokeObjectURL to clean up after download", () => {
    fillAndDownload()
    expect(mockRevokeObjectURL).toHaveBeenCalledWith("blob:mock-url")
  })

  it("does not call URL.createObjectURL when form is incomplete", () => {
    render(<ComplianceExportPage />)
    fireEvent.click(screen.getByRole("button", { name: /Download Report/i }))
    expect(mockCreateObjectURL).not.toHaveBeenCalled()
  })

  it("sets filename to include the selected date range", () => {
    const mockAnchor = { href: "", download: "", click: jest.fn() }
    const realCreate = document.createElement.bind(document)
    const spy = jest.spyOn(document, "createElement").mockImplementation(
      (tag: string, options?: ElementCreationOptions) =>
        tag === "a" ? (mockAnchor as unknown as HTMLAnchorElement) : realCreate(tag, options)
    )

    render(<ComplianceExportPage />)
    fireEvent.change(screen.getByLabelText("Date from"), { target: { value: "2026-04-01" } })
    fireEvent.change(screen.getByLabelText("Date to"), { target: { value: "2026-04-30" } })
    fireEvent.click(screen.getAllByRole("checkbox")[0])
    fireEvent.click(screen.getByRole("button", { name: /Download Report/i }))

    expect(mockAnchor.download).toBe("ces-compliance-2026-04-01-to-2026-04-30.csv")
    spy.mockRestore()
  })
})

// ── Last export notice ─────────────────────────────────────────────────────────

describe("Compliance Export — last export notice", () => {
  it("shows the most recent review period", () => {
    render(<ComplianceExportPage />)
    // Period "April 2026" appears only in the last export notice
    expect(screen.getByText(mockGovernanceReviews[0].period)).toBeInTheDocument()
  })

  it("shows the export scope from the last review", () => {
    render(<ComplianceExportPage />)
    // The italic span contains exactly the joined scope string
    expect(screen.getByText(mockGovernanceReviews[0].export_scope.join(", "))).toBeInTheDocument()
  })

  it("shows the reviewer name inside the last export notice", () => {
    render(<ComplianceExportPage />)
    // The notice <p> textContent contains the reviewer name
    const period = screen.getByText(mockGovernanceReviews[0].period)
    const noticeText = period.closest("p")?.textContent ?? ""
    expect(noticeText).toContain(mockGovernanceReviews[0].reviewed_by)
  })
})

// ── Navigation ─────────────────────────────────────────────────────────────────

describe("Compliance Export — navigation", () => {
  it("clicking PayWise logo navigates home", () => {
    render(<ComplianceExportPage />)
    fireEvent.click(screen.getByText("PayWise"))
    expect(mockPush).toHaveBeenCalledWith("/")
  })

  it("clicking back button navigates to /governance", () => {
    render(<ComplianceExportPage />)
    fireEvent.click(screen.getByRole("button", { name: /Back to Governance/i }))
    expect(mockPush).toHaveBeenCalledWith("/governance")
  })
})

// ── Role switching ─────────────────────────────────────────────────────────────

describe("Compliance Export — role switching", () => {
  it("defaults to director role (Lorraine)", () => {
    render(<ComplianceExportPage />)
    expect(screen.getByText(/User: Lorraine Chen/)).toBeInTheDocument()
  })

  it("opens role menu on click", () => {
    render(<ComplianceExportPage />)
    fireEvent.click(screen.getByRole("button", { name: /Switch role/i }))
    expect(screen.getByText(/Priya Venkataraman/)).toBeInTheDocument()
    expect(screen.getByText(/Damien Okafor/)).toBeInTheDocument()
    expect(screen.getByText(/Marcus Webb/)).toBeInTheDocument()
  })

  it("switches role and updates footer", () => {
    render(<ComplianceExportPage />)
    fireEvent.click(screen.getByRole("button", { name: /Switch role/i }))
    fireEvent.click(screen.getAllByText(/Marcus Webb/)[0])
    expect(screen.getByText(/User: Marcus Webb/)).toBeInTheDocument()
  })
})

// ── Footer ─────────────────────────────────────────────────────────────────────

describe("Compliance Export — footer", () => {
  it("shows Audit Active", () => {
    render(<ComplianceExportPage />)
    expect(screen.getByText(/Audit Active/i)).toBeInTheDocument()
  })

  it("shows current role in footer", () => {
    render(<ComplianceExportPage />)
    expect(screen.getByText(/Role: director/i)).toBeInTheDocument()
  })
})
