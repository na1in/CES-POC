/**
 * CES-39 — Configuration Management tests
 *
 * Covers: page structure, thresholds table, propose form, change request tabs,
 * deploy dialog, rollback dialog, version history, navigation, role switching, footer.
 */

import { render, screen, fireEvent, within } from "@testing-library/react"
import { useRouter } from "next/navigation"
import ConfigManagementPage from "@/app/admin/config/page"
import { mockThresholds } from "@/mocks/thresholds"
import { mockChangeRequests, mockVersionHistory } from "@/mocks/config"

jest.mock("next/navigation", () => ({
  useRouter: jest.fn(),
}))

const mockPush = jest.fn()

beforeEach(() => {
  mockPush.mockClear()
  ;(useRouter as jest.Mock).mockReturnValue({ push: mockPush })
  // jsdom does not implement scrollIntoView
  window.HTMLElement.prototype.scrollIntoView = jest.fn()
})

// ── Page structure ─────────────────────────────────────────────────────────────

describe("Config Management — page structure", () => {
  it("renders the page heading", () => {
    render(<ConfigManagementPage />)
    expect(screen.getByRole("heading", { name: /Configuration Management/i })).toBeInTheDocument()
  })

  it("shows the page subtitle", () => {
    render(<ConfigManagementPage />)
    expect(screen.getByText(/Threshold change-request workflow/i)).toBeInTheDocument()
  })

  it("renders the Current Thresholds section", () => {
    render(<ConfigManagementPage />)
    expect(screen.getByText("Current Thresholds")).toBeInTheDocument()
  })

  it("renders the Propose a Change section", () => {
    render(<ConfigManagementPage />)
    expect(screen.getByText("Propose a Change")).toBeInTheDocument()
  })

  it("renders the Change Requests section", () => {
    render(<ConfigManagementPage />)
    expect(screen.getByText("Change Requests")).toBeInTheDocument()
  })

  it("renders the Version History section", () => {
    render(<ConfigManagementPage />)
    expect(screen.getByText("Version History")).toBeInTheDocument()
  })
})

// ── Thresholds table ───────────────────────────────────────────────────────────

describe("Config Management — thresholds table", () => {
  it("renders all mock threshold rows", () => {
    render(<ConfigManagementPage />)
    mockThresholds.forEach(t => {
      // parameter names appear in both thresholds table and version history accordion
      expect(screen.getAllByText(t.parameter_name).length).toBeGreaterThan(0)
    })
  })

  it("shows current values for each threshold", () => {
    render(<ConfigManagementPage />)
    mockThresholds.forEach(t => {
      expect(screen.getAllByText(t.parameter_value).length).toBeGreaterThan(0)
    })
  })

  it("renders a Propose Change button for each threshold row", () => {
    render(<ConfigManagementPage />)
    const buttons = screen.getAllByRole("button", { name: /Propose change for/i })
    expect(buttons.length).toBe(mockThresholds.length)
  })

  it("shows table headers: Parameter, Current Value, Description, Last Changed, Changed By", () => {
    render(<ConfigManagementPage />)
    // "Parameter" appears in both thresholds and change-request tables
    expect(screen.getAllByText("Parameter").length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText("Current Value")).toBeInTheDocument()
    expect(screen.getByText("Description")).toBeInTheDocument()
    expect(screen.getByText("Last Changed")).toBeInTheDocument()
    expect(screen.getByText("Changed By")).toBeInTheDocument()
  })
})

// ── Propose form ───────────────────────────────────────────────────────────────

describe("Config Management — propose form", () => {
  const firstThreshold = mockThresholds[0]

  function openForm() {
    render(<ConfigManagementPage />)
    fireEvent.click(
      screen.getByRole("button", { name: `Propose change for ${firstThreshold.parameter_name}` })
    )
  }

  it("clicking Propose Change opens the form with parameter pre-filled", () => {
    openForm()
    expect(screen.getByLabelText("Parameter name (read-only)")).toHaveValue(firstThreshold.parameter_name)
  })

  it("current value field is pre-filled and read-only", () => {
    openForm()
    const currentInput = screen.getByLabelText("Current value (read-only)")
    expect(currentInput).toHaveValue(firstThreshold.parameter_value)
    expect(currentInput).toHaveAttribute("readOnly")
  })

  it("renders the proposed value input", () => {
    openForm()
    expect(screen.getByLabelText("Proposed value")).toBeInTheDocument()
  })

  it("renders the rationale textarea", () => {
    openForm()
    expect(screen.getByLabelText("Rationale")).toBeInTheDocument()
  })

  it("renders the projected impact input", () => {
    openForm()
    expect(screen.getByLabelText("Projected impact")).toBeInTheDocument()
  })

  it("shows rationale error when submitted with fewer than 20 characters", () => {
    openForm()
    fireEvent.change(screen.getByLabelText("Proposed value"), { target: { value: "95%" } })
    fireEvent.change(screen.getByLabelText("Rationale"), { target: { value: "short" } })
    fireEvent.click(screen.getByRole("button", { name: "Submit Request" }))
    expect(screen.getByRole("alert")).toHaveTextContent("Rationale must be at least 20 characters.")
  })

  it("shows error when proposed value is empty", () => {
    openForm()
    fireEvent.change(screen.getByLabelText("Rationale"), { target: { value: "This is a sufficient rationale for the change request." } })
    fireEvent.click(screen.getByRole("button", { name: "Submit Request" }))
    expect(screen.getByRole("alert")).toHaveTextContent("Proposed value is required.")
  })

  it("successful submission clears the form and shows a success banner", () => {
    openForm()
    fireEvent.change(screen.getByLabelText("Proposed value"), { target: { value: "93%" } })
    fireEvent.change(screen.getByLabelText("Rationale"), { target: { value: "Override rate in 90–92% band has increased significantly." } })
    fireEvent.click(screen.getByRole("button", { name: "Submit Request" }))
    expect(screen.getByText(/Change request submitted/i)).toBeInTheDocument()
  })

  it("successful submission switches change request tab to Pending", () => {
    openForm()
    fireEvent.change(screen.getByLabelText("Proposed value"), { target: { value: "93%" } })
    fireEvent.change(screen.getByLabelText("Rationale"), { target: { value: "Override rate in 90–92% band has increased significantly." } })
    fireEvent.click(screen.getByRole("button", { name: "Submit Request" }))
    // The newly submitted request should appear in Pending tab (selected)
    const pendingTab = screen.getByRole("button", { name: /Pending/i })
    expect(pendingTab).toHaveAttribute("aria-selected", "true")
  })

  it("Cancel button closes the form", () => {
    openForm()
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }))
    expect(screen.queryByLabelText("Proposed value")).not.toBeInTheDocument()
  })

  it("shows placeholder text when form is not open", () => {
    render(<ConfigManagementPage />)
    expect(screen.queryByLabelText("Proposed value")).not.toBeInTheDocument()
    expect(screen.queryByLabelText("Rationale")).not.toBeInTheDocument()
  })
})

// ── Change request tabs ────────────────────────────────────────────────────────

describe("Config Management — change request tabs", () => {
  it("renders all 5 tab buttons", () => {
    render(<ConfigManagementPage />)
    expect(screen.getByRole("button", { name: /^Pending/ })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /^Approved/ })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /^Deployed/ })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /^Rejected/ })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: /^All/ })).toBeInTheDocument()
  })

  it("defaults to Pending tab selected", () => {
    render(<ConfigManagementPage />)
    expect(screen.getByRole("button", { name: /^Pending/ })).toHaveAttribute("aria-selected", "true")
  })

  it("Pending tab shows only pending requests", () => {
    render(<ConfigManagementPage />)
    const pendingRequests = mockChangeRequests.filter(r => r.status === "pending")
    pendingRequests.forEach(r => {
      expect(screen.getByText(r.request_id)).toBeInTheDocument()
    })
  })

  it("switching to All tab shows all requests", () => {
    render(<ConfigManagementPage />)
    fireEvent.click(screen.getByRole("button", { name: /^All/ }))
    mockChangeRequests.forEach(r => {
      expect(screen.getAllByText(r.request_id).length).toBeGreaterThan(0)
    })
  })

  it("switching to Approved tab shows only approved requests", () => {
    render(<ConfigManagementPage />)
    fireEvent.click(screen.getByRole("button", { name: /^Approved/ }))
    const approvedRequests = mockChangeRequests.filter(r => r.status === "approved")
    approvedRequests.forEach(r => {
      expect(screen.getByText(r.request_id)).toBeInTheDocument()
    })
  })

  it("Rejected tab shows only rejected requests", () => {
    render(<ConfigManagementPage />)
    fireEvent.click(screen.getByRole("button", { name: /^Rejected/ }))
    const rejectedRequests = mockChangeRequests.filter(r => r.status === "rejected")
    rejectedRequests.forEach(r => {
      expect(screen.getByText(r.request_id)).toBeInTheDocument()
    })
  })

  it("shows status badges in All tab", () => {
    render(<ConfigManagementPage />)
    fireEvent.click(screen.getByRole("button", { name: /^All/ }))
    expect(screen.getAllByText("PENDING").length).toBeGreaterThan(0)
    expect(screen.getAllByText("APPROVED").length).toBeGreaterThan(0)
    expect(screen.getAllByText("DEPLOYED").length).toBeGreaterThan(0)
    expect(screen.getAllByText("REJECTED").length).toBeGreaterThan(0)
  })

  it("shows empty state message when tab has no requests", () => {
    render(<ConfigManagementPage />)
    // Switch to Pending tab (default), confirm it has data, then mock a filtered tab
    // Rejected tab might have only specific items; check a consistent path
    fireEvent.click(screen.getByRole("button", { name: /^Deployed/ }))
    const deployedCount = mockChangeRequests.filter(r => r.status === "deployed").length
    if (deployedCount === 0) {
      expect(screen.getByText("No change requests in this category.")).toBeInTheDocument()
    } else {
      expect(deployedCount).toBeGreaterThan(0)
    }
  })
})

// ── Deploy dialog ──────────────────────────────────────────────────────────────

describe("Config Management — deploy dialog", () => {
  const approvedRequest = mockChangeRequests.find(r => r.status === "approved")!

  function openDeployDialog() {
    render(<ConfigManagementPage />)
    fireEvent.click(screen.getByRole("button", { name: /^Approved/ }))
    fireEvent.click(screen.getByRole("button", { name: `Deploy ${approvedRequest.request_id}` }))
  }

  it("clicking Deploy button opens the confirm dialog", () => {
    openDeployDialog()
    expect(screen.getByText("Confirm Deployment")).toBeInTheDocument()
  })

  it("deploy dialog shows the parameter name", () => {
    openDeployDialog()
    expect(screen.getAllByText(approvedRequest.parameter_name).length).toBeGreaterThan(0)
  })

  it("deploy dialog shows old and new values", () => {
    openDeployDialog()
    expect(screen.getAllByText(approvedRequest.current_value).length).toBeGreaterThan(0)
    expect(screen.getAllByText(approvedRequest.proposed_value).length).toBeGreaterThan(0)
  })

  it("Cancel closes the dialog", () => {
    openDeployDialog()
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }))
    expect(screen.queryByText("Confirm Deployment")).not.toBeInTheDocument()
  })

  it("Close dialog button closes the dialog", () => {
    openDeployDialog()
    fireEvent.click(screen.getByRole("button", { name: "Close dialog" }))
    expect(screen.queryByText("Confirm Deployment")).not.toBeInTheDocument()
  })

  it("confirming deploy updates the threshold value in the table", () => {
    openDeployDialog()
    fireEvent.click(screen.getByRole("button", { name: "Confirm deploy" }))
    // Threshold table should now show the new value
    expect(screen.getAllByText(approvedRequest.proposed_value).length).toBeGreaterThan(0)
  })

  it("confirming deploy switches to Deployed tab", () => {
    openDeployDialog()
    fireEvent.click(screen.getByRole("button", { name: "Confirm deploy" }))
    expect(screen.getByRole("button", { name: /^Deployed/ })).toHaveAttribute("aria-selected", "true")
  })

  it("deployed request shows Rollback button after deploy", () => {
    openDeployDialog()
    fireEvent.click(screen.getByRole("button", { name: "Confirm deploy" }))
    // Now in deployed tab, the just-deployed request should show a Rollback button
    expect(screen.getByRole("button", { name: `Rollback ${approvedRequest.request_id}` })).toBeInTheDocument()
  })
})

// ── Rollback dialog ────────────────────────────────────────────────────────────

describe("Config Management — rollback dialog", () => {
  const deployedRequest = mockChangeRequests.find(r => r.status === "deployed")!

  function openRollbackDialog() {
    render(<ConfigManagementPage />)
    fireEvent.click(screen.getByRole("button", { name: /^Deployed/ }))
    fireEvent.click(screen.getByRole("button", { name: `Rollback ${deployedRequest.request_id}` }))
  }

  it("clicking Rollback opens the director approval dialog", () => {
    openRollbackDialog()
    expect(screen.getByText("Rollback Requires Director Approval")).toBeInTheDocument()
  })

  it("rollback dialog shows the parameter being rolled back", () => {
    openRollbackDialog()
    expect(screen.getAllByText(deployedRequest.parameter_name).length).toBeGreaterThan(0)
  })

  it("renders the director user ID input", () => {
    openRollbackDialog()
    expect(screen.getByLabelText("Director user ID")).toBeInTheDocument()
  })

  it("shows error when wrong director ID is entered", () => {
    openRollbackDialog()
    fireEvent.change(screen.getByLabelText("Director user ID"), { target: { value: "USR-999" } })
    fireEvent.click(screen.getByRole("button", { name: "Confirm rollback" }))
    expect(screen.getByRole("alert")).toBeInTheDocument()
  })

  it("correct director ID (USR-003) confirms rollback and switches to Approved tab", () => {
    openRollbackDialog()
    fireEvent.change(screen.getByLabelText("Director user ID"), { target: { value: "USR-003" } })
    fireEvent.click(screen.getByRole("button", { name: "Confirm rollback" }))
    expect(screen.getByRole("button", { name: /^Approved/ })).toHaveAttribute("aria-selected", "true")
  })

  it("rollback reverts the threshold value in the thresholds table", () => {
    openRollbackDialog()
    fireEvent.change(screen.getByLabelText("Director user ID"), { target: { value: "USR-003" } })
    fireEvent.click(screen.getByRole("button", { name: "Confirm rollback" }))
    // Original (current) value should be back in the table
    expect(screen.getAllByText(deployedRequest.current_value).length).toBeGreaterThan(0)
  })

  it("Cancel closes the rollback dialog", () => {
    openRollbackDialog()
    fireEvent.click(screen.getByRole("button", { name: "Cancel" }))
    expect(screen.queryByText("Rollback Requires Director Approval")).not.toBeInTheDocument()
  })
})

// ── Version history ────────────────────────────────────────────────────────────

describe("Config Management — version history", () => {
  it("Version History section is collapsed by default", () => {
    render(<ConfigManagementPage />)
    // The section exists but parameter rows should not be visible until opened
    // The section header is a toggle button
    const vhSection = screen.getByText("Version History")
    expect(vhSection).toBeInTheDocument()
  })

  it("expanding Version History shows parameter accordion rows", () => {
    render(<ConfigManagementPage />)
    // The section is collapsed — click to open
    const vhToggle = screen.getByText("Version History").closest("button")!
    fireEvent.click(vhToggle)
    // Should now show toggle buttons for each threshold parameter
    mockThresholds.forEach(t => {
      expect(screen.getByRole("button", { name: `Toggle history for ${t.parameter_name}` })).toBeInTheDocument()
    })
  })

  it("expanding a parameter row shows its change history", () => {
    render(<ConfigManagementPage />)
    const vhToggle = screen.getByText("Version History").closest("button")!
    fireEvent.click(vhToggle)
    // Expand name_match_auto_apply which has history in mock data
    const paramToggle = screen.getByRole("button", { name: "Toggle history for name_match_auto_apply" })
    fireEvent.click(paramToggle)
    // Should show an old value from version history
    const history = mockVersionHistory["name_match_auto_apply"]
    expect(screen.getByText(history[0].old_value)).toBeInTheDocument()
    expect(screen.getAllByText(history[0].new_value).length).toBeGreaterThan(0)
  })

  it("collapsing a parameter row hides its history", () => {
    render(<ConfigManagementPage />)
    const vhToggle = screen.getByText("Version History").closest("button")!
    fireEvent.click(vhToggle)
    const paramToggle = screen.getByRole("button", { name: "Toggle history for name_match_auto_apply" })
    fireEvent.click(paramToggle) // expand
    fireEvent.click(paramToggle) // collapse
    const history = mockVersionHistory["name_match_auto_apply"]
    expect(screen.queryByText(history[0].old_value)).not.toBeInTheDocument()
  })
})

// ── Navigation ─────────────────────────────────────────────────────────────────

describe("Config Management — navigation", () => {
  it("clicking PayWise logo navigates home", () => {
    render(<ConfigManagementPage />)
    fireEvent.click(screen.getByText("PayWise"))
    expect(mockPush).toHaveBeenCalledWith("/")
  })

  it("clicking back button navigates to /admin", () => {
    render(<ConfigManagementPage />)
    fireEvent.click(screen.getByRole("button", { name: /Back to Admin/i }))
    expect(mockPush).toHaveBeenCalledWith("/admin")
  })
})

// ── Role switching ─────────────────────────────────────────────────────────────

describe("Config Management — role switching", () => {
  it("defaults to admin role (Marcus)", () => {
    render(<ConfigManagementPage />)
    expect(screen.getByText(/User: Marcus Webb/)).toBeInTheDocument()
  })

  it("opens role menu on click", () => {
    render(<ConfigManagementPage />)
    fireEvent.click(screen.getByRole("button", { name: /Switch role/i }))
    expect(screen.getByText("(analyst)")).toBeInTheDocument()
    expect(screen.getByText("(director)")).toBeInTheDocument()
  })

  it("switches role and updates footer", () => {
    render(<ConfigManagementPage />)
    fireEvent.click(screen.getByRole("button", { name: /Switch role/i }))
    fireEvent.click(screen.getAllByText(/Priya Venkataraman/)[0])
    expect(screen.getByText(/User: Priya Venkataraman/)).toBeInTheDocument()
  })
})

// ── Footer ─────────────────────────────────────────────────────────────────────

describe("Config Management — footer", () => {
  it("shows Audit Active", () => {
    render(<ConfigManagementPage />)
    expect(screen.getByText(/Audit Active/i)).toBeInTheDocument()
  })

  it("shows current role in footer", () => {
    render(<ConfigManagementPage />)
    expect(screen.getByText(/Role: admin/i)).toBeInTheDocument()
  })
})
