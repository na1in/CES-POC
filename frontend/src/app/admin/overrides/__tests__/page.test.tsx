/**
 * CES-38 — Override Analysis tests
 *
 * Covers: page structure, filter bar, table rendering, scenario filter,
 * confidence band filter, reason search, empty state, Payment ID navigation,
 * override reason truncation/expand, navigation, role switching, footer.
 */

import { render, screen, fireEvent } from "@testing-library/react"
import { useRouter } from "next/navigation"
import OverrideAnalysisPage from "@/app/admin/overrides/page"
import { mockOverrides } from "@/mocks/overrides"

jest.mock("next/navigation", () => ({
  useRouter: jest.fn(),
}))

const mockPush = jest.fn()

beforeEach(() => {
  mockPush.mockClear()
  ;(useRouter as jest.Mock).mockReturnValue({ push: mockPush })
})

// ── Page structure ─────────────────────────────────────────────────────────────

describe("Override Analysis — page structure", () => {
  it("renders the page heading", () => {
    render(<OverrideAnalysisPage />)
    expect(screen.getByRole("heading", { name: /Override Analysis/i })).toBeInTheDocument()
  })

  it("shows the page subtitle", () => {
    render(<OverrideAnalysisPage />)
    expect(screen.getByText(/Analyst override patterns/i)).toBeInTheDocument()
  })

  it("shows the override count in the header", () => {
    render(<OverrideAnalysisPage />)
    expect(screen.getByText(`${mockOverrides.length} overrides`)).toBeInTheDocument()
  })
})

// ── Filter bar ─────────────────────────────────────────────────────────────────

describe("Override Analysis — filter bar", () => {
  it("renders the scenario dropdown", () => {
    render(<OverrideAnalysisPage />)
    expect(screen.getByLabelText("Filter by scenario")).toBeInTheDocument()
  })

  it("renders the confidence band dropdown", () => {
    render(<OverrideAnalysisPage />)
    expect(screen.getByLabelText("Filter by confidence band")).toBeInTheDocument()
  })

  it("renders the date-from input", () => {
    render(<OverrideAnalysisPage />)
    expect(screen.getByLabelText("Date from")).toBeInTheDocument()
  })

  it("renders the date-to input", () => {
    render(<OverrideAnalysisPage />)
    expect(screen.getByLabelText("Date to")).toBeInTheDocument()
  })

  it("renders the override reason search input", () => {
    render(<OverrideAnalysisPage />)
    expect(screen.getByLabelText("Search override reason")).toBeInTheDocument()
  })

  it("scenario dropdown defaults to All", () => {
    render(<OverrideAnalysisPage />)
    expect(screen.getByLabelText<HTMLSelectElement>("Filter by scenario").value).toBe("All")
  })

  it("confidence band dropdown defaults to All", () => {
    render(<OverrideAnalysisPage />)
    expect(screen.getByLabelText<HTMLSelectElement>("Filter by confidence band").value).toBe("All")
  })
})

// ── Table ──────────────────────────────────────────────────────────────────────

describe("Override Analysis — table", () => {
  it("shows all table column headers", () => {
    render(<OverrideAnalysisPage />)
    // Use getAllByText for labels that also appear in the filter bar ("Scenario")
    expect(screen.getByText("Payment ID")).toBeInTheDocument()
    expect(screen.getAllByText("Scenario").length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText("AI Rec")).toBeInTheDocument()
    expect(screen.getByText("Human Decision")).toBeInTheDocument()
    expect(screen.getByText("Confidence")).toBeInTheDocument()
    expect(screen.getAllByText("Override Reason").length).toBeGreaterThanOrEqual(1)
    expect(screen.getByText("Date")).toBeInTheDocument()
    expect(screen.getByText("Analyst")).toBeInTheDocument()
  })

  it("renders all mock override rows by default", () => {
    render(<OverrideAnalysisPage />)
    mockOverrides.forEach(o => {
      expect(screen.getByRole("button", { name: o.payment_id })).toBeInTheDocument()
    })
  })

  it("renders confidence scores for each row", () => {
    render(<OverrideAnalysisPage />)
    mockOverrides.forEach(o => {
      expect(screen.getAllByText(`${o.confidence_score}%`).length).toBeGreaterThan(0)
    })
  })

  it("renders analyst names", () => {
    render(<OverrideAnalysisPage />)
    expect(screen.getAllByText("Priya Venkataraman").length).toBeGreaterThan(0)
  })
})

// ── Scenario filter ────────────────────────────────────────────────────────────

describe("Override Analysis — scenario filter", () => {
  it("filtering by Scenario 1 shows only Scenario 1 rows", () => {
    render(<OverrideAnalysisPage />)
    fireEvent.change(screen.getByLabelText("Filter by scenario"), { target: { value: "Scenario 1" } })
    const sc1Overrides = mockOverrides.filter(o => o.scenario === "Scenario 1")
    const otherOverrides = mockOverrides.filter(o => o.scenario !== "Scenario 1")
    sc1Overrides.forEach(o => expect(screen.getByRole("button", { name: o.payment_id })).toBeInTheDocument())
    otherOverrides.forEach(o => expect(screen.queryByRole("button", { name: o.payment_id })).not.toBeInTheDocument())
  })

  it("count updates when scenario filter is applied", () => {
    render(<OverrideAnalysisPage />)
    fireEvent.change(screen.getByLabelText("Filter by scenario"), { target: { value: "Scenario 1" } })
    const sc1Count = mockOverrides.filter(o => o.scenario === "Scenario 1").length
    expect(screen.getByText(`${sc1Count} overrides`)).toBeInTheDocument()
  })

  it("resetting to All shows all rows again", () => {
    render(<OverrideAnalysisPage />)
    fireEvent.change(screen.getByLabelText("Filter by scenario"), { target: { value: "Scenario 1" } })
    fireEvent.change(screen.getByLabelText("Filter by scenario"), { target: { value: "All" } })
    expect(screen.getByText(`${mockOverrides.length} overrides`)).toBeInTheDocument()
  })
})

// ── Confidence band filter ─────────────────────────────────────────────────────

describe("Override Analysis — confidence band filter", () => {
  it("filtering by High shows only High band rows", () => {
    render(<OverrideAnalysisPage />)
    fireEvent.change(screen.getByLabelText("Filter by confidence band"), { target: { value: "High" } })
    const highOverrides = mockOverrides.filter(o => o.confidence_band === "High")
    const lowOverrides = mockOverrides.filter(o => o.confidence_band === "Low")
    highOverrides.forEach(o => expect(screen.getByRole("button", { name: o.payment_id })).toBeInTheDocument())
    lowOverrides.forEach(o => expect(screen.queryByRole("button", { name: o.payment_id })).not.toBeInTheDocument())
  })

  it("filtering by Low shows only Low band rows", () => {
    render(<OverrideAnalysisPage />)
    fireEvent.change(screen.getByLabelText("Filter by confidence band"), { target: { value: "Low" } })
    const lowOverrides = mockOverrides.filter(o => o.confidence_band === "Low")
    lowOverrides.forEach(o => expect(screen.getByRole("button", { name: o.payment_id })).toBeInTheDocument())
  })
})

// ── Reason search filter ───────────────────────────────────────────────────────

describe("Override Analysis — reason search filter", () => {
  it("searching by reason keyword filters matching rows", () => {
    render(<OverrideAnalysisPage />)
    fireEvent.change(screen.getByLabelText("Search override reason"), { target: { value: "fraud" } })
    const fraudOverrides = mockOverrides.filter(o => o.override_reason.toLowerCase().includes("fraud"))
    const nonFraudOverrides = mockOverrides.filter(o => !o.override_reason.toLowerCase().includes("fraud"))
    fraudOverrides.forEach(o => expect(screen.getByRole("button", { name: o.payment_id })).toBeInTheDocument())
    nonFraudOverrides.forEach(o => expect(screen.queryByRole("button", { name: o.payment_id })).not.toBeInTheDocument())
  })

  it("search is case-insensitive", () => {
    render(<OverrideAnalysisPage />)
    fireEvent.change(screen.getByLabelText("Search override reason"), { target: { value: "FRAUD" } })
    const fraudOverrides = mockOverrides.filter(o => o.override_reason.toLowerCase().includes("fraud"))
    expect(screen.getByText(`${fraudOverrides.length} override${fraudOverrides.length !== 1 ? "s" : ""}`)).toBeInTheDocument()
  })
})

// ── Empty state ────────────────────────────────────────────────────────────────

describe("Override Analysis — empty state", () => {
  it("shows empty state when filters return no results", () => {
    render(<OverrideAnalysisPage />)
    fireEvent.change(screen.getByLabelText("Search override reason"), { target: { value: "zzz-no-match-xyz" } })
    expect(screen.getByText("No overrides match your filters.")).toBeInTheDocument()
  })

  it("hides table when empty state is shown", () => {
    render(<OverrideAnalysisPage />)
    fireEvent.change(screen.getByLabelText("Search override reason"), { target: { value: "zzz-no-match-xyz" } })
    expect(screen.queryByText("Payment ID")).not.toBeInTheDocument()
  })

  it("shows 0 count in header when no results", () => {
    render(<OverrideAnalysisPage />)
    fireEvent.change(screen.getByLabelText("Search override reason"), { target: { value: "zzz-no-match-xyz" } })
    expect(screen.getByText("0 overrides")).toBeInTheDocument()
  })
})

// ── Payment ID navigation ──────────────────────────────────────────────────────

describe("Override Analysis — Payment ID navigation", () => {
  it("clicking a payment ID navigates to its detail page", () => {
    render(<OverrideAnalysisPage />)
    const first = mockOverrides[0]
    fireEvent.click(screen.getByRole("button", { name: first.payment_id }))
    expect(mockPush).toHaveBeenCalledWith(`/payments/${first.payment_id}`)
  })

  it("each payment ID links to the correct detail page", () => {
    render(<OverrideAnalysisPage />)
    mockOverrides.slice(0, 3).forEach(o => {
      fireEvent.click(screen.getByRole("button", { name: o.payment_id }))
      expect(mockPush).toHaveBeenCalledWith(`/payments/${o.payment_id}`)
    })
  })
})

// ── Override reason truncation ─────────────────────────────────────────────────

describe("Override Analysis — override reason truncation", () => {
  const longReasonEntry = mockOverrides.find(o => o.override_reason.length > 80)!
  const shortReasonEntry = mockOverrides.find(o => o.override_reason.length <= 80)

  it("long reasons show truncated text with 'more' button", () => {
    render(<OverrideAnalysisPage />)
    const longReasonCount = mockOverrides.filter(o => o.override_reason.length > 80).length
    expect(screen.getAllByRole("button", { name: "Expand reason" }).length).toBe(longReasonCount)
  })

  it("clicking 'more' expands the reason", () => {
    render(<OverrideAnalysisPage />)
    const moreBtn = screen.getAllByRole("button", { name: "Expand reason" })[0]
    fireEvent.click(moreBtn)
    expect(screen.getByRole("button", { name: "Collapse reason" })).toBeInTheDocument()
  })

  it("clicking 'less' collapses the reason again", () => {
    render(<OverrideAnalysisPage />)
    const moreBtn = screen.getAllByRole("button", { name: "Expand reason" })[0]
    fireEvent.click(moreBtn)
    const lessBtn = screen.getByRole("button", { name: "Collapse reason" })
    fireEvent.click(lessBtn)
    expect(screen.getAllByRole("button", { name: "Expand reason" }).length).toBeGreaterThan(0)
  })

  it("expanding shows the full reason text", () => {
    render(<OverrideAnalysisPage />)
    const moreBtn = screen.getAllByRole("button", { name: "Expand reason" })[0]
    fireEvent.click(moreBtn)
    expect(screen.getByText(longReasonEntry.override_reason)).toBeInTheDocument()
  })

  it("short reasons do not show a 'more' button", () => {
    if (!shortReasonEntry) return
    render(<OverrideAnalysisPage />)
    // Expand all to isolate — just verify count of expand buttons matches long-reason rows
    const longReasonCount = mockOverrides.filter(o => o.override_reason.length > 80).length
    expect(screen.getAllByRole("button", { name: "Expand reason" }).length).toBe(longReasonCount)
  })
})

// ── Navigation ─────────────────────────────────────────────────────────────────

describe("Override Analysis — navigation", () => {
  it("clicking PayWise logo navigates home", () => {
    render(<OverrideAnalysisPage />)
    fireEvent.click(screen.getByText("PayWise"))
    expect(mockPush).toHaveBeenCalledWith("/")
  })

  it("clicking back button navigates to /admin", () => {
    render(<OverrideAnalysisPage />)
    fireEvent.click(screen.getByRole("button", { name: /Back to Admin/i }))
    expect(mockPush).toHaveBeenCalledWith("/admin")
  })
})

// ── Role switching ─────────────────────────────────────────────────────────────

describe("Override Analysis — role switching", () => {
  it("defaults to admin role (Marcus)", () => {
    render(<OverrideAnalysisPage />)
    expect(screen.getByText(/User: Marcus Webb/)).toBeInTheDocument()
  })

  it("opens role menu on click", () => {
    render(<OverrideAnalysisPage />)
    fireEvent.click(screen.getByRole("button", { name: /Switch role/i }))
    // Role menu shows role labels like "(analyst)" — unique to the menu
    expect(screen.getByText("(analyst)")).toBeInTheDocument()
    expect(screen.getByText("(director)")).toBeInTheDocument()
  })

  it("switches role and updates footer", () => {
    render(<OverrideAnalysisPage />)
    fireEvent.click(screen.getByRole("button", { name: /Switch role/i }))
    fireEvent.click(screen.getAllByText(/Priya Venkataraman/)[0])
    expect(screen.getByText(/User: Priya Venkataraman/)).toBeInTheDocument()
  })
})

// ── Footer ─────────────────────────────────────────────────────────────────────

describe("Override Analysis — footer", () => {
  it("shows Audit Active", () => {
    render(<OverrideAnalysisPage />)
    expect(screen.getByText(/Audit Active/i)).toBeInTheDocument()
  })

  it("shows current role in footer", () => {
    render(<OverrideAnalysisPage />)
    expect(screen.getByText(/Role: admin/i)).toBeInTheDocument()
  })
})
