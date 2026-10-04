/**
 * CES-30 (updated from CES-13) — Queue Dashboard component tests
 *
 * Pages now fetch data via SWR. SWR is mocked to return mock fixtures
 * synchronously so all rendering/filter/sort/navigation tests remain
 * behaviorally identical to the original mock-data version.
 */

import React from "react"
import { render, screen, fireEvent, within } from "@testing-library/react"
import { useRouter } from "next/navigation"
import QueueDashboard from "@/app/page"
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

const mockListData: PaymentListResponse = {
  data: mockPayments.map(p => ({
    payment: p,
    recommendation: mockRecommendations[p.payment_id] ?? null,
    signals: mockPaymentSignals[p.payment_id] ?? null,
  })),
  total: mockPayments.length,
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

// ── Rendering ─────────────────────────────────────────────────────────────────

describe("Queue Dashboard — rendering", () => {
  it("renders a table row for every mock payment", () => {
    render(<QueueDashboard />)
    const dataRows = screen.getAllByRole("row").length - 1
    expect(dataRows).toBe(mockPayments.length)
  })

  it("displays sender names from mock data", () => {
    render(<QueueDashboard />)
    expect(screen.getByText("Unknown Remitter")).toBeInTheDocument()
    expect(screen.getAllByText("Riverside Medical Group").length).toBe(2)
  })

  it("formats amounts as USD — not raw cents", () => {
    render(<QueueDashboard />)
    expect(screen.getAllByText("$2,450.00").length).toBe(2)
    expect(screen.queryByText("245000")).not.toBeInTheDocument()
  })

  it("shows recommendation pills (APPLY, HOLD, ESCALATE)", () => {
    render(<QueueDashboard />)
    expect(screen.getByText("APPLY")).toBeInTheDocument()
    expect(screen.getAllByText("HOLD").length).toBeGreaterThan(0)
    expect(screen.getAllByText("ESCALATE").length).toBeGreaterThan(0)
  })

  it("shows scenario pills Sc1 through Sc5", () => {
    render(<QueueDashboard />)
    ;["Sc1", "Sc2", "Sc3", "Sc4", "Sc5"].forEach(label => {
      expect(screen.getAllByText(label).length).toBeGreaterThanOrEqual(1)
    })
  })

  it("shows confidence band labels (Low, Medium, High)", () => {
    render(<QueueDashboard />)
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

// ── Loading state ─────────────────────────────────────────────────────────────

describe("Queue Dashboard — loading state", () => {
  it("shows skeleton rows while loading", () => {
    ;(useSWR as jest.Mock).mockReturnValue({ data: undefined, isLoading: true, error: null, mutate: mockMutate })
    const { container } = render(<QueueDashboard />)
    expect(container.querySelector(".animate-pulse")).toBeInTheDocument()
  })

  it("does not render table rows while loading", () => {
    ;(useSWR as jest.Mock).mockReturnValue({ data: undefined, isLoading: true, error: null, mutate: mockMutate })
    render(<QueueDashboard />)
    expect(screen.queryByRole("row")).not.toBeInTheDocument()
  })
})

// ── Error state ───────────────────────────────────────────────────────────────

describe("Queue Dashboard — error state", () => {
  it("shows retry button on fetch error", () => {
    const { ApiError } = jest.requireMock("@/lib/api")
    ;(useSWR as jest.Mock).mockReturnValue({ data: undefined, isLoading: false, error: new ApiError(500, "Server error"), mutate: mockMutate })
    render(<QueueDashboard />)
    expect(screen.getByRole("button", { name: /retry/i })).toBeInTheDocument()
  })

  it("shows not found message for 404 error", () => {
    const { ApiError } = jest.requireMock("@/lib/api")
    ;(useSWR as jest.Mock).mockReturnValue({ data: undefined, isLoading: false, error: new ApiError(404, "Not found"), mutate: mockMutate })
    render(<QueueDashboard />)
    expect(screen.getByText(/no payments found/i)).toBeInTheDocument()
  })
})

// ── Sort order ────────────────────────────────────────────────────────────────

const RANK: Record<string, number> = { apply: 0, hold: 1, escalate: 2 }
const recOf = (id: string) => mockRecommendations[id]?.recommendation as string | undefined
const rankOf = (id: string) => (recOf(id) != null ? RANK[recOf(id)!] : 3)

describe("Queue Dashboard — default sort", () => {
  it("sorts rows by recommendation (Apply → Hold → Escalate) by default", () => {
    render(<QueueDashboard />)
    const rows = screen.getAllByRole("row").slice(1)
    const labels = rows.map(r => within(r).queryByText(/^(APPLY|HOLD|ESCALATE)$/)?.textContent?.toLowerCase())
    const ranks = labels.map(l => (l != null ? RANK[l] : 3))
    expect(ranks).toEqual([...ranks].sort((a, b) => a - b))
  })

  it("shows the sort dropdown with Recommendation: Apply → Escalate selected by default", () => {
    render(<QueueDashboard />)
    const select = screen.getByRole("combobox", { name: /sort by/i })
    expect((select as HTMLSelectElement).value).toBe("rec_apply_first")
  })

  it("switching sort to Recommendation: Escalate → Apply lists escalations first", () => {
    render(<QueueDashboard />)
    const select = screen.getByRole("combobox", { name: /sort by/i })
    fireEvent.change(select, { target: { value: "rec_escalate_first" } })
    const rows = screen.getAllByRole("row").slice(1)
    const labels = rows.map(r => within(r).queryByText(/^(APPLY|HOLD|ESCALATE)$/)?.textContent?.toLowerCase())
    const ranks = labels.map(l => (l != null ? RANK[l] : 3))
    expect(ranks).toEqual([...ranks].sort((a, b) => b - a))
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
    const filterChips = screen.getAllByText("Sc5")
    fireEvent.click(filterChips[0])

    const sc5PaymentIds = Object.entries(mockRecommendations)
      .filter(([, r]) => r.scenario_route === "scenario_5")
      .map(([id]) => id)

    const sc5SenderNames = mockPayments
      .filter(p => sc5PaymentIds.includes(p.payment_id))
      .map(p => p.sender_name)

    const rows = screen.getAllByRole("row").slice(1)
    expect(rows.length).toBe(sc5SenderNames.length)
  })
})

describe("Queue Dashboard — recommendation filter", () => {
  it.each([["Escalate", "escalate"], ["Hold", "hold"], ["Apply", "apply"]])(
    "clicking the %s chip shows only %s recommendations",
    (chip, rec) => {
      render(<QueueDashboard />)
      fireEvent.click(screen.getByRole("button", { name: chip }))
      const expected = mockPayments.filter(p => recOf(p.payment_id) === rec).length
      const rows = screen.getAllByRole("row").slice(1)
      expect(rows.length).toBe(expected)
    },
  )

  it("has no payment method filter", () => {
    render(<QueueDashboard />)
    expect(screen.queryByRole("button", { name: "ACH" })).not.toBeInTheDocument()
    expect(screen.queryByRole("button", { name: "Wire" })).not.toBeInTheDocument()
  })
})

// ── Empty state ───────────────────────────────────────────────────────────────

describe("Queue Dashboard — empty state", () => {
  it("shows empty state when filters eliminate all rows", () => {
    render(<QueueDashboard />)
    const sc1Chips = screen.getAllByText("Sc1")
    fireEvent.click(sc1Chips[0])
    const lowChips = screen.getAllByText("Low")
    fireEvent.click(lowChips[0])
    expect(screen.getByText(/no payments match your filters/i)).toBeInTheDocument()
  })

  it("clicking Clear filters restores all rows", () => {
    render(<QueueDashboard />)
    const sc1Chips = screen.getAllByText("Sc1")
    fireEvent.click(sc1Chips[0])
    const lowChips = screen.getAllByText("Low")
    fireEvent.click(lowChips[0])
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
    fireEvent.click(rows[0])
    expect(mockPush).toHaveBeenCalledWith("/payments/PMT-001")
  })

  it("each payment routes to its own URL", () => {
    render(<QueueDashboard />)
    const rows = screen.getAllByRole("row").slice(1)

    const sorted = [...mockPayments].sort((a, b) => rankOf(a.payment_id) - rankOf(b.payment_id))

    rows.forEach((row, i) => {
      fireEvent.click(row)
      expect(mockPush).toHaveBeenCalledWith(`/payments/${sorted[i].payment_id}`)
    })
  })
})
