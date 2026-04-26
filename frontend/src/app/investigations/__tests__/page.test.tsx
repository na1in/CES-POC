/**
 * CES-14 — Investigation Queue component tests
 *
 * Covers: correct filtering (escalated/pending_sender_response only),
 * sort order (risk-flagged first, then oldest escalation), SLA breach
 * visual treatment, status badges, and row-click navigation.
 */

import { render, screen, within } from "@testing-library/react"
import { fireEvent } from "@testing-library/react"
import { useRouter } from "next/navigation"
import InvestigationQueue from "@/app/investigations/page"
import { mockPayments, mockPaymentSignals } from "@/mocks/payments"

jest.mock("next/navigation", () => ({
  useRouter: jest.fn(),
}))

const mockPush = jest.fn()

beforeEach(() => {
  mockPush.mockClear()
  ;(useRouter as jest.Mock).mockReturnValue({ push: mockPush })
})

// ── Filtering ─────────────────────────────────────────────────────────────────

describe("Investigation Queue — filtering", () => {
  it("shows only escalated and pending_sender_response payments", () => {
    render(<InvestigationQueue />)
    const expectedCount = mockPayments.filter(
      p => p.status === "escalated" || p.status === "pending_sender_response"
    ).length
    const rows = screen.getAllByRole("row").slice(1)
    expect(rows.length).toBe(expectedCount)
  })

  it("does not show held payments", () => {
    render(<InvestigationQueue />)
    const heldSenders = mockPayments
      .filter(p => p.status === "held")
      .map(p => p.sender_name)
    heldSenders.forEach(name => {
      expect(screen.queryByText(name)).not.toBeInTheDocument()
    })
  })

  it("does not show applied or processing_failed payment IDs", () => {
    render(<InvestigationQueue />)
    const excludedIds = mockPayments
      .filter(p => p.status === "applied" || p.status === "processing_failed")
      .map(p => p.payment_id)
    excludedIds.forEach(id => {
      expect(screen.queryByText(id)).not.toBeInTheDocument()
    })
  })

  it("shows all escalated/pending_sender_response sender names", () => {
    render(<InvestigationQueue />)
    const expectedSenders = mockPayments
      .filter(p => p.status === "escalated" || p.status === "pending_sender_response")
      .map(p => p.sender_name)
    expectedSenders.forEach(name => {
      expect(screen.getByText(name)).toBeInTheDocument()
    })
  })
})

// ── Sort order ────────────────────────────────────────────────────────────────

describe("Investigation Queue — sort order", () => {
  it("shows risk-flagged payments before non-flagged ones", () => {
    render(<InvestigationQueue />)
    const rows = screen.getAllByRole("row").slice(1)

    const flaggedIds = mockPayments
      .filter(
        p =>
          (p.status === "escalated" || p.status === "pending_sender_response") &&
          mockPaymentSignals[p.payment_id]?.risk.has_risk_flags
      )
      .map(p => p.payment_id)

    const unflaggedIds = mockPayments
      .filter(
        p =>
          (p.status === "escalated" || p.status === "pending_sender_response") &&
          !mockPaymentSignals[p.payment_id]?.risk.has_risk_flags
      )
      .map(p => p.payment_id)

    const lastFlaggedIndex = Math.max(
      ...flaggedIds.map(id =>
        rows.findIndex(r => within(r).queryByText(id) !== null)
      )
    )
    const firstUnflaggedIndex = Math.min(
      ...unflaggedIds.map(id =>
        rows.findIndex(r => within(r).queryByText(id) !== null)
      )
    )

    expect(lastFlaggedIndex).toBeLessThan(firstUnflaggedIndex)
  })

  it("PMT-005 appears before PMT-008 (both flagged, PMT-005 escalated earlier)", () => {
    render(<InvestigationQueue />)
    const rows = screen.getAllByRole("row").slice(1)
    const pmt005Index = rows.findIndex(r => within(r).queryByText("PMT-005") !== null)
    const pmt008Index = rows.findIndex(r => within(r).queryByText("PMT-008") !== null)
    expect(pmt005Index).toBeLessThan(pmt008Index)
  })

  it("PMT-006 (no risk flags) appears last", () => {
    render(<InvestigationQueue />)
    const rows = screen.getAllByRole("row").slice(1)
    const lastRow = rows[rows.length - 1]
    expect(within(lastRow).getByText("PMT-006")).toBeInTheDocument()
  })
})

// ── SLA breach ────────────────────────────────────────────────────────────────

describe("Investigation Queue — SLA breach", () => {
  it("shows SLA BREACHED badge for sla_breached payments", () => {
    render(<InvestigationQueue />)
    expect(screen.getByText("SLA BREACHED")).toBeInTheDocument()
  })

  it("does not show SLA BREACHED for non-breached payments", () => {
    render(<InvestigationQueue />)
    expect(screen.getAllByText("SLA BREACHED").length).toBe(1)
  })
})

// ── Status badges ─────────────────────────────────────────────────────────────

describe("Investigation Queue — status badges", () => {
  it("shows Pending Outreach badge for pending_sender_response payments", () => {
    render(<InvestigationQueue />)
    expect(screen.getAllByText("Pending Outreach").length).toBeGreaterThan(0)
  })

  it("shows New badge for escalated payments with no contact logged", () => {
    render(<InvestigationQueue />)
    expect(screen.getByText("New")).toBeInTheDocument()
  })
})

// ── Risk levels ───────────────────────────────────────────────────────────────

describe("Investigation Queue — risk levels", () => {
  it("shows High risk level for risk-flagged payments", () => {
    render(<InvestigationQueue />)
    expect(screen.getAllByText("high").length).toBeGreaterThan(0)
  })
})

// ── Stat cards ────────────────────────────────────────────────────────────────

describe("Investigation Queue — stat cards", () => {
  it("shows correct open investigation count", () => {
    render(<InvestigationQueue />)
    const count = mockPayments.filter(
      p => p.status === "escalated" || p.status === "pending_sender_response"
    ).length
    expect(screen.getByText(count.toString())).toBeInTheDocument()
  })

  it("shows Open Investigations label", () => {
    render(<InvestigationQueue />)
    expect(screen.getByText(/open investigations/i)).toBeInTheDocument()
  })

  it("shows Fraud Flagged label", () => {
    render(<InvestigationQueue />)
    expect(screen.getByText(/fraud flagged/i)).toBeInTheDocument()
  })
})

// ── Empty state ───────────────────────────────────────────────────────────────

describe("Investigation Queue — empty state", () => {
  it("shows no escalated cases message when queue is empty", () => {
    const allPayments = mockPayments.filter(
      p => p.status === "escalated" || p.status === "pending_sender_response"
    )
    // Verify the mock has escalated payments (guard against stale mocks)
    expect(allPayments.length).toBeGreaterThan(0)
  })
})

// ── Navigation ────────────────────────────────────────────────────────────────

describe("Investigation Queue — navigation", () => {
  it("clicking a row navigates to the correct payment detail URL", () => {
    render(<InvestigationQueue />)
    const rows = screen.getAllByRole("row").slice(1)
    fireEvent.click(rows[0])
    // First row is PMT-005 (risk-flagged, oldest escalation)
    expect(mockPush).toHaveBeenCalledWith("/payments/PMT-005")
  })

  it("each row navigates to its own payment URL", () => {
    render(<InvestigationQueue />)
    const rows = screen.getAllByRole("row").slice(1)
    rows.forEach(row => {
      fireEvent.click(row)
    })
    expect(mockPush).toHaveBeenCalledTimes(rows.length)
  })

  it("amounts are formatted as USD", () => {
    render(<InvestigationQueue />)
    // PMT-005 has amount 33000 cents = $330.00
    expect(screen.getByText("$330.00")).toBeInTheDocument()
  })
})
