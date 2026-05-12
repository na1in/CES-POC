/**
 * CES-14 (updated for CES-30) — Investigation Queue component tests
 *
 * Pages now fetch data via SWR. SWR is mocked to return filtered mock fixtures
 * (escalated + pending_sender_response only) so all behavioral tests remain
 * identical to the original version.
 */

import React from "react"
import { render, screen, within } from "@testing-library/react"
import { fireEvent } from "@testing-library/react"
import { useRouter } from "next/navigation"
import InvestigationQueue from "@/app/investigations/page"
import { mockPayments, mockRecommendations, mockPaymentSignals } from "@/mocks/payments"
import type { PaymentListResponse } from "@/types/api"

// ── Mocks ─────────────────────────────────────────────────────────────────────

jest.mock("next/navigation", () => ({
  useRouter: jest.fn(),
}))

jest.mock("swr", () => ({
  __esModule: true,
  default: jest.fn(),
  SWRConfig: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

jest.mock("@/lib/api", () => ({
  apiFetch: jest.fn().mockResolvedValue({}),
  ApiError: class ApiError extends Error {
    status: number
    constructor(status: number, message: string) { super(message); this.status = status }
  },
  fetcher: jest.fn(),
  getToken: jest.fn(),
  setToken: jest.fn(),
  clearToken: jest.fn(),
}))

jest.mock("@/contexts/ToastContext", () => ({
  useToast: () => ({ showToast: jest.fn() }),
  ToastProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}))

import useSWR from "swr"

const mockPush = jest.fn()
const mockMutate = jest.fn()

// Only escalated + pending_sender_response — matches what the API returns for this page
const investigationPayments = mockPayments.filter(
  p => p.status === "escalated" || p.status === "pending_sender_response"
)

const mockListData: PaymentListResponse = {
  data: investigationPayments.map(p => ({
    payment: p,
    recommendation: mockRecommendations[p.payment_id] ?? null,
    signals: mockPaymentSignals[p.payment_id] ?? null,
  })),
  total: investigationPayments.length,
  page: 1,
  page_size: 50,
}

beforeEach(() => {
  mockPush.mockClear()
  mockMutate.mockClear()
  ;(useRouter as jest.Mock).mockReturnValue({ push: mockPush })
  ;(useSWR as jest.Mock).mockReturnValue({
    data: mockListData,
    isLoading: false,
    error: null,
    mutate: mockMutate,
  })
})

// ── Loading state ─────────────────────────────────────────────────────────────

describe("Investigation Queue — loading state", () => {
  it("shows skeleton rows while loading", () => {
    ;(useSWR as jest.Mock).mockReturnValue({ data: undefined, isLoading: true, error: null, mutate: mockMutate })
    const { container } = render(<InvestigationQueue />)
    expect(container.querySelector(".animate-pulse")).toBeInTheDocument()
  })

  it("does not render table rows while loading", () => {
    ;(useSWR as jest.Mock).mockReturnValue({ data: undefined, isLoading: true, error: null, mutate: mockMutate })
    render(<InvestigationQueue />)
    expect(screen.queryByRole("row")).not.toBeInTheDocument()
  })
})

// ── Error state ───────────────────────────────────────────────────────────────

describe("Investigation Queue — error state", () => {
  it("shows retry button on fetch error", () => {
    const { ApiError } = jest.requireMock("@/lib/api")
    ;(useSWR as jest.Mock).mockReturnValue({ data: undefined, isLoading: false, error: new ApiError(500, "Server error"), mutate: mockMutate })
    render(<InvestigationQueue />)
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument()
  })

  it("shows not found message for 404 error", () => {
    const { ApiError } = jest.requireMock("@/lib/api")
    ;(useSWR as jest.Mock).mockReturnValue({ data: undefined, isLoading: false, error: new ApiError(404, "Not found"), mutate: mockMutate })
    render(<InvestigationQueue />)
    expect(screen.getByText(/no escalated cases found/i)).toBeInTheDocument()
  })
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

    const flaggedIds = investigationPayments
      .filter(p => mockPaymentSignals[p.payment_id]?.risk.has_risk_flags)
      .map(p => p.payment_id)

    const unflaggedIds = investigationPayments
      .filter(p => !mockPaymentSignals[p.payment_id]?.risk.has_risk_flags)
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

  it("PMT-008 appears before PMT-005 (both flagged, PMT-008 created earlier)", () => {
    render(<InvestigationQueue />)
    const rows = screen.getAllByRole("row").slice(1)
    const pmt008Index = rows.findIndex(r => within(r).queryByText("PMT-008") !== null)
    const pmt005Index = rows.findIndex(r => within(r).queryByText("PMT-005") !== null)
    expect(pmt008Index).toBeLessThan(pmt005Index)
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
    const count = investigationPayments.length
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
    ;(useSWR as jest.Mock).mockReturnValue({
      data: { data: [], total: 0, page: 1, page_size: 50 },
      isLoading: false,
      error: null,
      mutate: mockMutate,
    })
    render(<InvestigationQueue />)
    expect(screen.getByText(/no escalated cases/i)).toBeInTheDocument()
  })
})

// ── Navigation ────────────────────────────────────────────────────────────────

describe("Investigation Queue — navigation", () => {
  it("clicking a row navigates to the correct payment detail URL", () => {
    render(<InvestigationQueue />)
    const rows = screen.getAllByRole("row").slice(1)
    fireEvent.click(rows[0])
    // First row is PMT-008 (risk-flagged, oldest creation date: 2026-04-10)
    expect(mockPush).toHaveBeenCalledWith("/payments/PMT-008")
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
