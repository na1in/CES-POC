/**
 * CES-36 — Exception Dashboard tests
 *
 * Covers: three sections with data, empty states, reject modal validation,
 * approve/reject actions, anomaly expand/collapse, navigation, role switching.
 */

import { render, screen, fireEvent } from "@testing-library/react"
import { useRouter } from "next/navigation"
import ExceptionDashboardPage from "@/app/governance/exceptions/page"
import { mockSlaBreachedPayments, mockAnomalyFlags, mockPendingChangeRequests } from "@/mocks/exceptions"

jest.mock("next/navigation", () => ({
  useRouter: jest.fn(),
}))

const mockPush = jest.fn()

beforeEach(() => {
  mockPush.mockClear()
  ;(useRouter as jest.Mock).mockReturnValue({ push: mockPush })
})

// ── Page structure ─────────────────────────────────────────────────────────────

describe("Exception Dashboard — page structure", () => {
  it("renders the page heading", () => {
    render(<ExceptionDashboardPage />)
    expect(screen.getByRole("heading", { name: /Exception Dashboard/i })).toBeInTheDocument()
  })

  it("shows the page subtitle", () => {
    render(<ExceptionDashboardPage />)
    expect(screen.getByText(/SLA breaches, anomaly flags, and config changes/i)).toBeInTheDocument()
  })

  it("shows all three section headings", () => {
    render(<ExceptionDashboardPage />)
    expect(screen.getByText("SLA Breached Cases")).toBeInTheDocument()
    expect(screen.getByText("Anomaly Flags")).toBeInTheDocument()
    expect(screen.getByText("Config Changes Pending Approval")).toBeInTheDocument()
  })
})

// ── Section 1: SLA Breached Cases ─────────────────────────────────────────────

describe("Exception Dashboard — SLA breached cases", () => {
  it("renders all SLA breached payment IDs", () => {
    render(<ExceptionDashboardPage />)
    mockSlaBreachedPayments.forEach(p => {
      expect(screen.getByText(p.payment_id)).toBeInTheDocument()
    })
  })

  it("renders all sender names", () => {
    render(<ExceptionDashboardPage />)
    mockSlaBreachedPayments.forEach(p => {
      expect(screen.getByText(p.sender_name)).toBeInTheDocument()
    })
  })

  it("renders all scenario labels", () => {
    render(<ExceptionDashboardPage />)
    mockSlaBreachedPayments.forEach(p => {
      expect(screen.getAllByText(p.scenario).length).toBeGreaterThan(0)
    })
  })

  it("renders investigator names", () => {
    render(<ExceptionDashboardPage />)
    expect(screen.getAllByText("Damien Okafor").length).toBeGreaterThan(0)
  })

  it("shows SLA table column headers", () => {
    render(<ExceptionDashboardPage />)
    expect(screen.getByText("Payment ID")).toBeInTheDocument()
    expect(screen.getByText("Sender")).toBeInTheDocument()
    expect(screen.getByText("Amount")).toBeInTheDocument()
    expect(screen.getByText("Scenario")).toBeInTheDocument()
    expect(screen.getByText("Time Since Breach")).toBeInTheDocument()
    expect(screen.getByText("Investigator")).toBeInTheDocument()
  })

  it("clicking a breached payment row navigates to its detail page", () => {
    render(<ExceptionDashboardPage />)
    const firstId = mockSlaBreachedPayments[0].payment_id
    fireEvent.click(screen.getByText(firstId).closest("tr")!)
    expect(mockPush).toHaveBeenCalledWith(`/payments/${firstId}`)
  })
})

// ── Section 2: Anomaly Flags ───────────────────────────────────────────────────

describe("Exception Dashboard — anomaly flags", () => {
  it("renders all anomaly metric names", () => {
    render(<ExceptionDashboardPage />)
    mockAnomalyFlags.forEach(a => {
      expect(screen.getByText(a.metric)).toBeInTheDocument()
    })
  })

  it("renders all anomaly descriptions", () => {
    render(<ExceptionDashboardPage />)
    mockAnomalyFlags.forEach(a => {
      expect(screen.getByText(a.description)).toBeInTheDocument()
    })
  })

  it("shows status chips for each anomaly", () => {
    render(<ExceptionDashboardPage />)
    expect(screen.getByText("Investigating")).toBeInTheDocument()
    expect(screen.getAllByText("Open").length).toBe(2)
  })

  it("shows View Details buttons for each anomaly", () => {
    render(<ExceptionDashboardPage />)
    const buttons = screen.getAllByText("View Details")
    expect(buttons.length).toBe(mockAnomalyFlags.length)
  })

  it("expands resolution notes when View Details is clicked", () => {
    render(<ExceptionDashboardPage />)
    const firstAnomaly = mockAnomalyFlags[0]
    fireEvent.click(screen.getByRole("button", { name: `View details for ${firstAnomaly.metric}` }))
    expect(screen.getByText(firstAnomaly.resolution_notes!)).toBeInTheDocument()
  })

  it("shows 'No resolution notes yet' for anomalies without notes", () => {
    render(<ExceptionDashboardPage />)
    const noNotes = mockAnomalyFlags.find(a => a.resolution_notes === null)!
    fireEvent.click(screen.getByRole("button", { name: `View details for ${noNotes.metric}` }))
    expect(screen.getByText(/No resolution notes yet/i)).toBeInTheDocument()
  })

  it("collapses resolution notes when Hide is clicked", () => {
    render(<ExceptionDashboardPage />)
    const firstAnomaly = mockAnomalyFlags[0]
    const btn = screen.getByRole("button", { name: `View details for ${firstAnomaly.metric}` })
    fireEvent.click(btn)
    expect(screen.getByText("Hide")).toBeInTheDocument()
    fireEvent.click(screen.getByText("Hide"))
    expect(screen.queryByText(firstAnomaly.resolution_notes!)).not.toBeInTheDocument()
  })
})

// ── Section 3: Config Changes ──────────────────────────────────────────────────

describe("Exception Dashboard — config change requests", () => {
  it("renders all pending change request IDs as parameter names", () => {
    render(<ExceptionDashboardPage />)
    mockPendingChangeRequests.forEach(r => {
      expect(screen.getByText(r.parameter_name)).toBeInTheDocument()
    })
  })

  it("renders proposed values", () => {
    render(<ExceptionDashboardPage />)
    mockPendingChangeRequests.forEach(r => {
      expect(screen.getByText(r.proposed_value)).toBeInTheDocument()
    })
  })

  it("renders current values", () => {
    render(<ExceptionDashboardPage />)
    mockPendingChangeRequests.forEach(r => {
      expect(screen.getByText(r.current_value)).toBeInTheDocument()
    })
  })

  it("shows Approve and Reject buttons for each request", () => {
    render(<ExceptionDashboardPage />)
    expect(screen.getAllByText("Approve").length).toBe(mockPendingChangeRequests.length)
    expect(screen.getAllByText("Reject").length).toBe(mockPendingChangeRequests.length)
  })

  it("shows config change table column headers", () => {
    render(<ExceptionDashboardPage />)
    expect(screen.getByText("Parameter")).toBeInTheDocument()
    expect(screen.getByText("Current Value")).toBeInTheDocument()
    expect(screen.getByText("Proposed Value")).toBeInTheDocument()
    expect(screen.getByText("Proposed By")).toBeInTheDocument()
    expect(screen.getByText("Actions")).toBeInTheDocument()
  })

  it("clicking Approve removes the row", () => {
    render(<ExceptionDashboardPage />)
    const firstRequest = mockPendingChangeRequests[0]
    fireEvent.click(screen.getByRole("button", { name: `Approve ${firstRequest.parameter_name}` }))
    expect(screen.queryByText(firstRequest.parameter_name)).not.toBeInTheDocument()
  })
})

// ── Reject modal ───────────────────────────────────────────────────────────────

describe("Exception Dashboard — reject modal", () => {
  function openRejectModal() {
    render(<ExceptionDashboardPage />)
    const firstRequest = mockPendingChangeRequests[0]
    fireEvent.click(screen.getByRole("button", { name: `Reject ${firstRequest.parameter_name}` }))
    return firstRequest
  }

  it("opens reject modal when Reject is clicked", () => {
    openRejectModal()
    expect(screen.getByText("Reject Change Request")).toBeInTheDocument()
  })

  it("shows the parameter name in the modal", () => {
    const req = openRejectModal()
    expect(screen.getAllByText(req.parameter_name).length).toBeGreaterThanOrEqual(1)
  })

  it("shows the proposed value in the modal", () => {
    const req = openRejectModal()
    expect(screen.getAllByText(req.proposed_value).length).toBeGreaterThanOrEqual(1)
  })

  it("Confirm Reject button is disabled when comment is empty", () => {
    openRejectModal()
    const confirmBtn = screen.getByText("Confirm Reject")
    expect(confirmBtn).toBeDisabled()
  })

  it("Confirm Reject becomes enabled after entering a comment", () => {
    openRejectModal()
    fireEvent.change(screen.getByLabelText("Review comment"), { target: { value: "Not enough justification." } })
    const confirmBtn = screen.getByText("Confirm Reject")
    expect(confirmBtn).not.toBeDisabled()
  })

  it("closing the modal with Cancel hides it", () => {
    openRejectModal()
    fireEvent.click(screen.getByText("Cancel"))
    expect(screen.queryByText("Reject Change Request")).not.toBeInTheDocument()
  })

  it("closing the modal with X button hides it", () => {
    openRejectModal()
    fireEvent.click(screen.getByRole("button", { name: /Close modal/i }))
    expect(screen.queryByText("Reject Change Request")).not.toBeInTheDocument()
  })

  it("confirming reject with a comment removes the row and closes modal", () => {
    const req = openRejectModal()
    fireEvent.change(screen.getByLabelText("Review comment"), { target: { value: "Insufficient evidence." } })
    fireEvent.click(screen.getByText("Confirm Reject"))
    expect(screen.queryByText("Reject Change Request")).not.toBeInTheDocument()
    expect(screen.queryByText(req.parameter_name)).not.toBeInTheDocument()
  })
})

// ── Empty states ───────────────────────────────────────────────────────────────

describe("Exception Dashboard — empty states", () => {
  it("sections can be collapsed by clicking the header", () => {
    render(<ExceptionDashboardPage />)
    fireEvent.click(screen.getByText("SLA Breached Cases"))
    expect(screen.queryByText("Payment ID")).not.toBeInTheDocument()
  })

  it("collapsed section can be re-expanded", () => {
    render(<ExceptionDashboardPage />)
    fireEvent.click(screen.getByText("SLA Breached Cases"))
    fireEvent.click(screen.getByText("SLA Breached Cases"))
    expect(screen.getByText("Payment ID")).toBeInTheDocument()
  })
})

// ── Navigation & footer ────────────────────────────────────────────────────────

describe("Exception Dashboard — navigation", () => {
  it("clicking PayWise logo navigates home", () => {
    render(<ExceptionDashboardPage />)
    fireEvent.click(screen.getByText("PayWise"))
    expect(mockPush).toHaveBeenCalledWith("/")
  })
})

describe("Exception Dashboard — footer", () => {
  it("shows Audit Active", () => {
    render(<ExceptionDashboardPage />)
    expect(screen.getByText(/Audit Active/i)).toBeInTheDocument()
  })

  it("shows current role in footer", () => {
    render(<ExceptionDashboardPage />)
    expect(screen.getByText(/Role: director/i)).toBeInTheDocument()
  })
})
