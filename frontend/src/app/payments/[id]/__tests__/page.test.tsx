/**
 * CES-15 — Payment Detail page tests
 *
 * Covers: not-found state, payment info rendering, recommendation banner,
 * signal grid, policy sidebar, audit trail, decision action buttons,
 * override modal flow, and navigation.
 */

import { render, screen, fireEvent, within } from "@testing-library/react"
import { useRouter, useParams } from "next/navigation"
import PaymentDetail from "@/app/payments/[id]/page"

jest.mock("next/navigation", () => ({
  useRouter: jest.fn(),
  useParams: jest.fn(),
}))

const mockPush = jest.fn()
const mockBack = jest.fn()

beforeEach(() => {
  mockPush.mockClear()
  mockBack.mockClear()
  ;(useRouter as jest.Mock).mockReturnValue({ push: mockPush, back: mockBack })
})

function renderWith(id: string) {
  ;(useParams as jest.Mock).mockReturnValue({ id })
  return render(<PaymentDetail />)
}

// ── Not found ─────────────────────────────────────────────────────────────────

describe("Payment Detail — not found", () => {
  it("shows payment not found message for unknown ID", () => {
    renderWith("PMT-999")
    expect(screen.getByText(/payment not found/i)).toBeInTheDocument()
  })

  it("back to queue link navigates home for unknown ID", () => {
    renderWith("PMT-999")
    fireEvent.click(screen.getByText(/back to queue/i))
    expect(mockPush).toHaveBeenCalledWith("/")
  })
})

// ── Page header ───────────────────────────────────────────────────────────────

describe("Payment Detail — page header", () => {
  it("shows the correct case ID in the heading", () => {
    renderWith("PMT-001")
    expect(screen.getByRole("heading", { name: /Case PMT-001/i })).toBeInTheDocument()
  })

  it("shows SLA Breached badge for breached payments", () => {
    renderWith("PMT-008")
    expect(screen.getAllByText(/SLA Breached/i).length).toBeGreaterThan(0)
  })

  it("does not show SLA badge for non-breached payments", () => {
    renderWith("PMT-001")
    expect(screen.queryByText(/SLA Breached/i)).not.toBeInTheDocument()
  })

  it("back button calls router.back()", () => {
    renderWith("PMT-001")
    fireEvent.click(screen.getByRole("button", { name: /go back/i }))
    expect(mockBack).toHaveBeenCalled()
  })
})

// ── AI Recommendation banner ──────────────────────────────────────────────────

describe("Payment Detail — recommendation banner", () => {
  it("shows APPLY recommendation for PMT-001", () => {
    renderWith("PMT-001")
    expect(screen.getByText(/AI Recommendation: APPLY/i)).toBeInTheDocument()
  })

  it("shows HOLD recommendation for PMT-002", () => {
    renderWith("PMT-002")
    expect(screen.getByText(/AI Recommendation: HOLD/i)).toBeInTheDocument()
  })

  it("shows ESCALATE recommendation for PMT-005", () => {
    renderWith("PMT-005")
    expect(screen.getByText(/AI Recommendation: ESCALATE/i)).toBeInTheDocument()
  })

  it("shows confidence score", () => {
    renderWith("PMT-001")
    expect(screen.getByText(/Confidence Score: 98%/i)).toBeInTheDocument()
  })

  it("shows first reasoning line", () => {
    renderWith("PMT-001")
    expect(screen.getByText(/Name similarity 97 exceeds auto-apply threshold/i)).toBeInTheDocument()
  })
})

// ── Signal mini-grid ──────────────────────────────────────────────────────────

describe("Payment Detail — signal grid", () => {
  it("shows BEST NAME MATCH label", () => {
    renderWith("PMT-001")
    expect(screen.getByText("BEST NAME MATCH")).toBeInTheDocument()
  })

  it("shows SIMILARITY SCORE label", () => {
    renderWith("PMT-001")
    expect(screen.getByText("SIMILARITY SCORE")).toBeInTheDocument()
  })

  it("shows AMOUNT CORRELATION label", () => {
    renderWith("PMT-001")
    expect(screen.getByText("AMOUNT CORRELATION")).toBeInTheDocument()
  })

  it("shows DUPLICATE CHECK label", () => {
    renderWith("PMT-001")
    expect(screen.getByText("DUPLICATE CHECK")).toBeInTheDocument()
  })

  it("shows On target for zero variance (PMT-001)", () => {
    renderWith("PMT-001")
    expect(screen.getByText("On target")).toBeInTheDocument()
  })

  it("shows variance percentage for PMT-004 (50% overpayment)", () => {
    renderWith("PMT-004")
    expect(screen.getByText(/\+50% variance/i)).toBeInTheDocument()
  })

  it("shows No duplicates for PMT-001", () => {
    renderWith("PMT-001")
    expect(screen.getByText("No duplicates")).toBeInTheDocument()
  })

  it("shows duplicate target for PMT-006 (duplicate of PMT-001)", () => {
    renderWith("PMT-006")
    expect(screen.getByText("Duplicate of PMT-001")).toBeInTheDocument()
  })

  it("shows LLM indicator when LLM was used (PMT-002)", () => {
    renderWith("PMT-002")
    expect(screen.getByText(/\(LLM\)/)).toBeInTheDocument()
  })

  it("shows name similarity score", () => {
    renderWith("PMT-001")
    expect(screen.getByText("97%")).toBeInTheDocument()
  })
})

// ── Manual review warning ─────────────────────────────────────────────────────

describe("Payment Detail — manual review", () => {
  it("shows Manual Review Required for payments needing approval", () => {
    renderWith("PMT-002")
    expect(screen.getByText(/Manual Review Required/i)).toBeInTheDocument()
  })

  it("does not show Manual Review Required for auto-applied payment", () => {
    renderWith("PMT-001")
    expect(screen.queryByText(/Manual Review Required/i)).not.toBeInTheDocument()
  })
})

// ── Payment Information section ───────────────────────────────────────────────

describe("Payment Detail — payment information", () => {
  it("shows Payment Information heading", () => {
    renderWith("PMT-001")
    expect(screen.getByText("Payment Information")).toBeInTheDocument()
  })

  it("shows sender name", () => {
    renderWith("PMT-001")
    // Appears in both sender name and policy holder fields
    expect(screen.getAllByText("Riverside Medical Group").length).toBeGreaterThan(0)
  })

  it("shows formatted amount for PMT-001 ($2,450.00)", () => {
    renderWith("PMT-001")
    // Amount appears in both the large display and payment history rows
    expect(screen.getAllByText("$2,450.00").length).toBeGreaterThan(0)
  })

  it("shows payment method", () => {
    renderWith("PMT-001")
    expect(screen.getByText("ACH")).toBeInTheDocument()
  })

  it("shows reference field when present", () => {
    renderWith("PMT-001")
    // POL-88341 appears in reference field and policy sidebar
    expect(screen.getAllByText(/POL-88341/).length).toBeGreaterThan(0)
  })
})

// ── Decision action buttons ───────────────────────────────────────────────────

describe("Payment Detail — decision actions", () => {
  it("shows Accept HOLD button for held payment (PMT-002)", () => {
    renderWith("PMT-002")
    expect(screen.getByRole("button", { name: /Accept HOLD/i })).toBeInTheDocument()
  })

  it("shows Override Recommendation button for held payment", () => {
    renderWith("PMT-002")
    expect(screen.getByRole("button", { name: /Override Recommendation/i })).toBeInTheDocument()
  })

  it("shows Escalate button for held payment", () => {
    renderWith("PMT-002")
    expect(screen.getByRole("button", { name: /Escalate/i })).toBeInTheDocument()
  })

  it("shows applied status badge for applied payment (PMT-001)", () => {
    renderWith("PMT-001")
    expect(screen.getByText(/Applied — No action required/i)).toBeInTheDocument()
  })

  it("shows Return to Sender button for escalated payment (PMT-006)", () => {
    renderWith("PMT-006")
    expect(screen.getByRole("button", { name: /Return to Sender/i })).toBeInTheDocument()
  })

  it("shows Reprocess Payment button for processing_failed payment (PMT-007)", () => {
    renderWith("PMT-007")
    expect(screen.getByRole("button", { name: /Reprocess Payment/i })).toBeInTheDocument()
  })
})

// ── Override modal ────────────────────────────────────────────────────────────

describe("Payment Detail — override modal", () => {
  it("opens the override dialog when Override Recommendation is clicked", () => {
    renderWith("PMT-002")
    fireEvent.click(screen.getByRole("button", { name: /Override Recommendation/i }))
    expect(screen.getByRole("dialog", { name: /Override Recommendation/i })).toBeInTheDocument()
  })

  it("Submit Override button is disabled when reason is empty", () => {
    renderWith("PMT-002")
    fireEvent.click(screen.getByRole("button", { name: /Override Recommendation/i }))
    const submitBtn = screen.getByRole("button", { name: /Submit Override/i })
    expect(submitBtn).toBeDisabled()
  })

  it("Submit Override button is enabled after typing a reason", () => {
    renderWith("PMT-002")
    fireEvent.click(screen.getByRole("button", { name: /Override Recommendation/i }))
    fireEvent.change(screen.getByRole("textbox", { name: /Override reason/i }), {
      target: { value: "Sender confirmed via phone call" },
    })
    expect(screen.getByRole("button", { name: /Submit Override/i })).not.toBeDisabled()
  })

  it("closes the modal when Cancel is clicked", () => {
    renderWith("PMT-002")
    fireEvent.click(screen.getByRole("button", { name: /Override Recommendation/i }))
    fireEvent.click(screen.getByRole("button", { name: /Cancel/i }))
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
  })

  it("closes the modal and shows toast after submitting a reason", () => {
    renderWith("PMT-002")
    fireEvent.click(screen.getByRole("button", { name: /Override Recommendation/i }))
    fireEvent.change(screen.getByRole("textbox", { name: /Override reason/i }), {
      target: { value: "Verified identity" },
    })
    fireEvent.click(screen.getByRole("button", { name: /Submit Override/i }))
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument()
    expect(screen.getByRole("status")).toHaveTextContent(/Override recorded/i)
  })
})

// ── Matched Policy sidebar ────────────────────────────────────────────────────

describe("Payment Detail — matched policy sidebar", () => {
  it("shows Matched Policy heading", () => {
    renderWith("PMT-001")
    expect(screen.getByText("Matched Policy")).toBeInTheDocument()
  })

  it("shows the policy number for PMT-001", () => {
    renderWith("PMT-001")
    expect(screen.getByText("POL-88341")).toBeInTheDocument()
  })

  it("shows policy holder name", () => {
    renderWith("PMT-001")
    // "Riverside Medical Group" appears in both sender name and policy holder
    const instances = screen.getAllByText("Riverside Medical Group")
    expect(instances.length).toBeGreaterThan(0)
  })

  it("shows Active badge for policy status", () => {
    renderWith("PMT-001")
    expect(screen.getByText("Active")).toBeInTheDocument()
  })

  it("shows No matched policy for PMT-005 (no policy match)", () => {
    renderWith("PMT-005")
    expect(screen.getByText("No matched policy")).toBeInTheDocument()
  })
})

// ── Case metadata ─────────────────────────────────────────────────────────────

describe("Payment Detail — case metadata", () => {
  it("shows CASE ID label", () => {
    renderWith("PMT-001")
    expect(screen.getByText("CASE ID")).toBeInTheDocument()
  })

  it("shows the payment ID in case metadata", () => {
    renderWith("PMT-001")
    // PMT-001 appears in heading and metadata
    expect(screen.getAllByText("PMT-001").length).toBeGreaterThan(0)
  })

  it("shows Closed — Applied status for applied payment", () => {
    renderWith("PMT-001")
    expect(screen.getByText("Closed — Applied")).toBeInTheDocument()
  })

  it("shows Open — Awaiting Decision for held payment", () => {
    renderWith("PMT-002")
    expect(screen.getByText("Open — Awaiting Decision")).toBeInTheDocument()
  })
})

// ── Audit trail ───────────────────────────────────────────────────────────────

describe("Payment Detail — audit trail", () => {
  it("shows Audit Trail heading for payments with log entries", () => {
    renderWith("PMT-001")
    expect(screen.getByText("Audit Trail")).toBeInTheDocument()
  })

  it("shows Case Created entry", () => {
    renderWith("PMT-001")
    expect(screen.getByText("Case Created")).toBeInTheDocument()
  })

  it("shows Analysis Complete entry for PMT-001", () => {
    renderWith("PMT-001")
    expect(screen.getByText("Analysis Complete")).toBeInTheDocument()
  })

  it("shows SLA Breached entry for PMT-008", () => {
    renderWith("PMT-008")
    expect(screen.getAllByText("SLA Breached").length).toBeGreaterThan(0)
  })
})

// ── Payment History ───────────────────────────────────────────────────────────

describe("Payment Detail — payment history", () => {
  it("shows Payment History section for policies with history", () => {
    renderWith("PMT-001")
    expect(screen.getByText("Payment History")).toBeInTheDocument()
  })

  it("shows Applied badges in payment history", () => {
    renderWith("PMT-001")
    const appliedBadges = screen.getAllByText("Applied")
    expect(appliedBadges.length).toBeGreaterThan(0)
  })

  it("does not show payment history for PMT-005 (no policy)", () => {
    renderWith("PMT-005")
    expect(screen.queryByText("Payment History")).not.toBeInTheDocument()
  })
})

// ── Case notes ────────────────────────────────────────────────────────────────

describe("Payment Detail — case notes", () => {
  it("shows Case Notes section for PMT-002 (has annotations)", () => {
    renderWith("PMT-002")
    expect(screen.getByText("Case Notes")).toBeInTheDocument()
  })

  it("shows annotation content for PMT-002", () => {
    renderWith("PMT-002")
    expect(screen.getByText(/Called client — confirmed/i)).toBeInTheDocument()
  })

  it("does not show Case Notes for PMT-003 (no annotations)", () => {
    renderWith("PMT-003")
    expect(screen.queryByText("Case Notes")).not.toBeInTheDocument()
  })
})

// ── Footer ────────────────────────────────────────────────────────────────────

describe("Payment Detail — footer", () => {
  it("shows Audit Active in footer", () => {
    renderWith("PMT-001")
    expect(screen.getByText(/Audit Active/i)).toBeInTheDocument()
  })
})
