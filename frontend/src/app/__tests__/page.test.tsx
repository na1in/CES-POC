/**
 * CES-13 — Queue Dashboard component tests
 *
 * Covers: rendering, USD formatting, confidence colour bands, filters
 * (scenario/confidence/method), processing-failed banner, empty state,
 * row-click navigation, and default sort order.
 */

import { render, screen, fireEvent, within } from "@testing-library/react"
import { useRouter } from "next/navigation"
import QueueDashboard from "@/app/page"
import { mockPayments, mockRecommendations } from "@/mocks/payments"

jest.mock("next/navigation", () => ({
  useRouter: jest.fn(),
}))

const mockPush = jest.fn()

beforeEach(() => {
  mockPush.mockClear()
  ;(useRouter as jest.Mock).mockReturnValue({ push: mockPush })
})

// ── Rendering ─────────────────────────────────────────────────────────────────

describe("Queue Dashboard — rendering", () => {
  it("renders a table row for every mock payment", () => {
    render(<QueueDashboard />)
    // getAllByRole('row') includes the header row, so subtract 1
    const dataRows = screen.getAllByRole("row").length - 1
    expect(dataRows).toBe(mockPayments.length)
  })

  it("displays sender names from mock data", () => {
    render(<QueueDashboard />)
    expect(screen.getByText("Unknown Remitter")).toBeInTheDocument()
    // PMT-001 and PMT-006 share the same sender — both rows should appear
    expect(screen.getAllByText("Riverside Medical Group").length).toBe(2)
  })

  it("formats amounts as USD — not raw cents", () => {
    render(<QueueDashboard />)
    // PMT-001 and PMT-006 both have 245000 cents → $2,450.00 (two rows)
    expect(screen.getAllByText("$2,450.00").length).toBe(2)
    // Raw cents should never appear
    expect(screen.queryByText("245000")).not.toBeInTheDocument()
  })

  it("shows AI recommendation pills (APPLY, HOLD, ESCALATE)", () => {
    render(<QueueDashboard />)
    expect(screen.getByText("APPLY")).toBeInTheDocument()
    expect(screen.getAllByText("HOLD").length).toBeGreaterThan(0)
    expect(screen.getAllByText("ESCALATE").length).toBeGreaterThan(0)
  })

  it("shows scenario pills Sc1 through Sc5", () => {
    render(<QueueDashboard />)
    // Each label appears in both the filter bar and table cells
    ;["Sc1", "Sc2", "Sc3", "Sc4", "Sc5"].forEach(label => {
      expect(screen.getAllByText(label).length).toBeGreaterThanOrEqual(1)
    })
  })

  it("shows confidence band labels (Low, Medium, High)", () => {
    render(<QueueDashboard />)
    // These appear in both the filter bar and as cell badges
    expect(screen.getAllByText(/Low/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Medium/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/High/i).length).toBeGreaterThan(0)
  })

  it("shows age cells with relative time", () => {
    render(<QueueDashboard />)
    const ageCells = screen.getAllByText(/\d+(m|h|d) ago/)
    expect(ageCells.length).toBeGreaterThan(0)
  })
})

// ── Sort order ────────────────────────────────────────────────────────────────

describe("Queue Dashboard — default sort", () => {
  it("sorts rows by confidence score descending (highest first) by default", () => {
    render(<QueueDashboard />)
    const rows = screen.getAllByRole("row").slice(1) // skip header
    // PMT-001 has confidence 98 — highest — should be first data row
    expect(within(rows[0]).getByText("PMT-001")).toBeInTheDocument()
    // PMT-005 has confidence 4 — lowest — should be last row
    const lastRow = rows[rows.length - 1]
    expect(within(lastRow).getByText("Unknown Remitter")).toBeInTheDocument()
  })

  it("shows the sort dropdown with Confidence: High → Low selected by default", () => {
    render(<QueueDashboard />)
    const select = screen.getByRole("combobox", { name: /sort by/i })
    expect((select as HTMLSelectElement).value).toBe("confidence_desc")
  })

  it("switching sort to Confidence: Low → High puts PMT-005 first", () => {
    render(<QueueDashboard />)
    const select = screen.getByRole("combobox", { name: /sort by/i })
    fireEvent.change(select, { target: { value: "confidence_asc" } })
    const rows = screen.getAllByRole("row").slice(1)
    expect(within(rows[0]).getByText("Unknown Remitter")).toBeInTheDocument()
  })

  it("switching sort to Sender A→Z puts Blue Pines Construction first", () => {
    render(<QueueDashboard />)
    const select = screen.getByRole("combobox", { name: /sort by/i })
    fireEvent.change(select, { target: { value: "sender_asc" } })
    const rows = screen.getAllByRole("row").slice(1)
    expect(within(rows[0]).getByText("Blue Pines Construction")).toBeInTheDocument()
  })

  it("switching sort to Amount High→Low puts $12,000.00 first", () => {
    render(<QueueDashboard />)
    const select = screen.getByRole("combobox", { name: /sort by/i })
    fireEvent.change(select, { target: { value: "amount_desc" } })
    const rows = screen.getAllByRole("row").slice(1)
    expect(within(rows[0]).getByText("$12,000.00")).toBeInTheDocument()
  })
})

// ── Processing-failed banner ──────────────────────────────────────────────────

describe("Queue Dashboard — processing-failed banner", () => {
  it("shows the banner when a payment has status=processing_failed", () => {
    const hasFailedPayment = mockPayments.some(p => p.status === "processing_failed")
    expect(hasFailedPayment).toBe(true) // guard: mock data must have one

    render(<QueueDashboard />)
    expect(screen.getByText(/failed to process/i)).toBeInTheDocument()
  })

  it("dismisses the banner when the X button is clicked", () => {
    render(<QueueDashboard />)
    const dismissBtn = screen.getByRole("button", { name: /dismiss/i })
    fireEvent.click(dismissBtn)
    expect(screen.queryByText(/failed to process/i)).not.toBeInTheDocument()
  })
})

// ── Filters ───────────────────────────────────────────────────────────────────

describe("Queue Dashboard — scenario filter", () => {
  it("clicking Sc5 shows only scenario_5 payments", () => {
    render(<QueueDashboard />)
    // The filter bar has a Sc5 chip; click it
    const filterChips = screen.getAllByText("Sc5")
    // First match is the filter chip (before the table pill)
    fireEvent.click(filterChips[0])

    const sc5PaymentIds = Object.entries(mockRecommendations)
      .filter(([, r]) => r.scenario_route === "scenario_5")
      .map(([id]) => id)

    // Rows after filtering should only contain scenario_5 sender names
    const sc5SenderNames = mockPayments
      .filter(p => sc5PaymentIds.includes(p.payment_id))
      .map(p => p.sender_name)

    const rows = screen.getAllByRole("row").slice(1)
    expect(rows.length).toBe(sc5SenderNames.length)
    sc5SenderNames.forEach(name => {
      expect(screen.getByText(name)).toBeInTheDocument()
    })
  })
})

describe("Queue Dashboard — confidence band filter", () => {
  it("clicking Low shows only payments with confidence < 40", () => {
    render(<QueueDashboard />)
    // Click the "Low" filter chip in the Confidence row
    const lowChips = screen.getAllByText("Low")
    fireEvent.click(lowChips[0])

    const lowConfidenceIds = Object.entries(mockRecommendations)
      .filter(([, r]) => r.confidence_score < 40)
      .map(([id]) => id)

    const rows = screen.getAllByRole("row").slice(1)
    expect(rows.length).toBe(lowConfidenceIds.length)
  })
})

describe("Queue Dashboard — payment method filter", () => {
  it("clicking ACH shows only ACH payments", () => {
    render(<QueueDashboard />)
    fireEvent.click(screen.getByRole("button", { name: "ACH" }))

    const achPayments = mockPayments.filter(p => p.payment_method === "ACH")
    const rows = screen.getAllByRole("row").slice(1)
    expect(rows.length).toBe(achPayments.length)
  })

  it("clicking Wire shows only Wire payments", () => {
    render(<QueueDashboard />)
    fireEvent.click(screen.getByRole("button", { name: "Wire" }))

    const wirePayments = mockPayments.filter(p => p.payment_method === "Wire")
    const rows = screen.getAllByRole("row").slice(1)
    expect(rows.length).toBe(wirePayments.length)
  })
})

// ── Empty state ───────────────────────────────────────────────────────────────

describe("Queue Dashboard — empty state", () => {
  it("shows empty state when filters eliminate all rows", () => {
    render(<QueueDashboard />)
    // Apply two conflicting filters to guarantee zero results:
    // Sc1 AND Low confidence — no Sc1 payment has confidence < 40
    const sc1Chips = screen.getAllByText("Sc1")
    fireEvent.click(sc1Chips[0])
    const lowChips = screen.getAllByText("Low")
    fireEvent.click(lowChips[0])

    expect(screen.getByText(/no payments match your filters/i)).toBeInTheDocument()
  })

  it("shows a Clear filters button in the empty state", () => {
    render(<QueueDashboard />)
    const sc1Chips = screen.getAllByText("Sc1")
    fireEvent.click(sc1Chips[0])
    const lowChips = screen.getAllByText("Low")
    fireEvent.click(lowChips[0])

    // Both the filter bar link and the empty-state button say "Clear filters"
    const clearBtns = screen.getAllByRole("button", { name: /clear filters/i })
    expect(clearBtns.length).toBeGreaterThanOrEqual(1)
  })

  it("clicking Clear filters restores all rows", () => {
    render(<QueueDashboard />)
    const sc1Chips = screen.getAllByText("Sc1")
    fireEvent.click(sc1Chips[0])
    const lowChips = screen.getAllByText("Low")
    fireEvent.click(lowChips[0])

    // Both the filter bar link and the empty-state button say "Clear filters"; click either
    fireEvent.click(screen.getAllByRole("button", { name: /clear filters/i })[0])

    const rows = screen.getAllByRole("row").slice(1)
    expect(rows.length).toBe(mockPayments.length)
  })
})

// ── Row-click navigation ──────────────────────────────────────────────────────

describe("Queue Dashboard — navigation", () => {
  it("clicking a row calls router.push with the correct payment detail URL", () => {
    render(<QueueDashboard />)
    const rows = screen.getAllByRole("row").slice(1)
    // First row is PMT-001 (highest confidence = 98, default sort)
    fireEvent.click(rows[0])
    expect(mockPush).toHaveBeenCalledWith("/payments/PMT-001")
  })

  it("each payment routes to its own URL", () => {
    render(<QueueDashboard />)
    const rows = screen.getAllByRole("row").slice(1)

    // Sort payments by confidence descending to match default rendered order
    const sorted = [...mockPayments].sort((a, b) => {
      const aScore = mockRecommendations[a.payment_id]?.confidence_score ?? 0
      const bScore = mockRecommendations[b.payment_id]?.confidence_score ?? 0
      return bScore - aScore
    })

    rows.forEach((row, i) => {
      fireEvent.click(row)
      expect(mockPush).toHaveBeenCalledWith(`/payments/${sorted[i].payment_id}`)
    })
  })
})
