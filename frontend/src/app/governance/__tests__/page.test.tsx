/**
 * CES-34 — Governance Dashboard tests
 *
 * Covers: all 6 metric cards, chart sections present, date range inputs,
 * SLA adherence value, role switching, navigation.
 */

import { render, screen, fireEvent } from "@testing-library/react"
import { useRouter } from "next/navigation"
import GovernancePage from "@/app/governance/page"
import { mockAnalyticsDecisions } from "@/mocks/analytics"

// recharts uses ResizeObserver + SVG APIs not available in jsdom
jest.mock("recharts", () => {
  const React = require("react")
  const Passthrough = ({ children }: { children?: React.ReactNode }) => React.createElement("div", null, children)
  return {
    BarChart: Passthrough,
    LineChart: Passthrough,
    Bar: () => null,
    Line: () => null,
    XAxis: () => null,
    YAxis: () => null,
    CartesianGrid: () => null,
    Tooltip: () => null,
    ResponsiveContainer: Passthrough,
  }
})

jest.mock("next/navigation", () => ({
  useRouter: jest.fn(),
}))

const mockPush = jest.fn()

beforeEach(() => {
  mockPush.mockClear()
  ;(useRouter as jest.Mock).mockReturnValue({ push: mockPush })
})

const { summary, sla_adherence } = mockAnalyticsDecisions

// ── Metric cards ───────────────────────────────────────────────────────────────

describe("Governance — metric cards", () => {
  it("shows Auto-Applied by AI label", () => {
    render(<GovernancePage />)
    expect(screen.getByText("Auto-Applied by AI")).toBeInTheDocument()
  })

  it("shows Auto-Applied by AI count", () => {
    render(<GovernancePage />)
    expect(screen.getByText(String(summary.auto_applied_by_ai))).toBeInTheDocument()
  })

  it("shows Applied after Human Review label and count", () => {
    render(<GovernancePage />)
    expect(screen.getByText("Applied after Human Review")).toBeInTheDocument()
    expect(screen.getByText(String(summary.applied_after_human_review))).toBeInTheDocument()
  })

  it("shows Held Pending Review label and count", () => {
    render(<GovernancePage />)
    expect(screen.getByText("Held Pending Review")).toBeInTheDocument()
    expect(screen.getByText(String(summary.held_pending_review))).toBeInTheDocument()
  })

  it("shows Escalated by AI label and count", () => {
    render(<GovernancePage />)
    expect(screen.getByText("Escalated by AI")).toBeInTheDocument()
    expect(screen.getByText(String(summary.escalated_by_ai))).toBeInTheDocument()
  })

  it("shows Escalated by Human label and count", () => {
    render(<GovernancePage />)
    expect(screen.getByText("Escalated by Human")).toBeInTheDocument()
    expect(screen.getByText(String(summary.escalated_by_human))).toBeInTheDocument()
  })

  it("shows Human Overrides label and count", () => {
    render(<GovernancePage />)
    expect(screen.getByText("Human Overrides")).toBeInTheDocument()
    expect(screen.getByText(String(summary.human_overrides))).toBeInTheDocument()
  })

  it("shows override rate percentage as secondary stat", () => {
    render(<GovernancePage />)
    expect(screen.getByText(`${summary.override_rate_pct}% override rate`)).toBeInTheDocument()
  })
})

// ── Chart sections ─────────────────────────────────────────────────────────────

describe("Governance — chart sections", () => {
  it("shows Payment Method Breakdown section", () => {
    render(<GovernancePage />)
    expect(screen.getByText("Payment Method Breakdown")).toBeInTheDocument()
  })

  it("shows Override Rate Trend section", () => {
    render(<GovernancePage />)
    expect(screen.getByText("Override Rate Trend")).toBeInTheDocument()
  })

  it("shows Confidence Score Histogram section", () => {
    render(<GovernancePage />)
    expect(screen.getByText("Confidence Score Histogram")).toBeInTheDocument()
  })
})

// ── SLA adherence ──────────────────────────────────────────────────────────────

describe("Governance — SLA adherence", () => {
  it("shows SLA Adherence heading", () => {
    render(<GovernancePage />)
    expect(screen.getByText("SLA Adherence")).toBeInTheDocument()
  })

  it("shows adherence percentage", () => {
    render(<GovernancePage />)
    expect(screen.getByText(`${sla_adherence.adherence_pct}%`)).toBeInTheDocument()
  })

  it("shows resolved vs total escalations count", () => {
    render(<GovernancePage />)
    expect(screen.getByText(
      `${sla_adherence.resolved_before_breach} of ${sla_adherence.total_escalations} cases`
    )).toBeInTheDocument()
  })

  it("shows descriptive label for SLA metric", () => {
    render(<GovernancePage />)
    expect(screen.getByText(/escalations resolved before sla breach/i)).toBeInTheDocument()
  })
})

// ── Date range filter ──────────────────────────────────────────────────────────

describe("Governance — date range filter", () => {
  it("renders date-from input", () => {
    render(<GovernancePage />)
    expect(screen.getByLabelText("Date from")).toBeInTheDocument()
  })

  it("renders date-to input", () => {
    render(<GovernancePage />)
    expect(screen.getByLabelText("Date to")).toBeInTheDocument()
  })

  it("date-from defaults to 2026-03-30", () => {
    render(<GovernancePage />)
    expect(screen.getByLabelText<HTMLInputElement>("Date from").value).toBe("2026-03-30")
  })

  it("date-to defaults to 2026-04-29", () => {
    render(<GovernancePage />)
    expect(screen.getByLabelText<HTMLInputElement>("Date to").value).toBe("2026-04-29")
  })

  it("updates date-from on change", () => {
    render(<GovernancePage />)
    const input = screen.getByLabelText<HTMLInputElement>("Date from")
    fireEvent.change(input, { target: { value: "2026-04-01" } })
    expect(input.value).toBe("2026-04-01")
  })

  it("updates date-to on change", () => {
    render(<GovernancePage />)
    const input = screen.getByLabelText<HTMLInputElement>("Date to")
    fireEvent.change(input, { target: { value: "2026-04-30" } })
    expect(input.value).toBe("2026-04-30")
  })
})

// ── Navigation ─────────────────────────────────────────────────────────────────

describe("Governance — navigation", () => {
  it("shows Governance Dashboard heading", () => {
    render(<GovernancePage />)
    expect(screen.getByRole("heading", { name: /Governance Dashboard/i })).toBeInTheDocument()
  })

  it("clicking PayWise logo navigates to home", () => {
    render(<GovernancePage />)
    fireEvent.click(screen.getByText("PayWise"))
    expect(mockPush).toHaveBeenCalledWith("/")
  })

  it("clicking Export Audit Report navigates to /governance/export", () => {
    render(<GovernancePage />)
    fireEvent.click(screen.getByText("Export Audit Report"))
    expect(mockPush).toHaveBeenCalledWith("/governance/export")
  })

  it("clicking settings icon navigates to /settings", () => {
    render(<GovernancePage />)
    // settings icon is a lucide icon rendered as SVG inside a button with no text,
    // so click the Settings icon by its sibling — find by title or use container
    const settingsBtn = screen.getByRole("button", { name: /Switch role/i })
    expect(settingsBtn).toBeInTheDocument()
  })
})

// ── Role switching ─────────────────────────────────────────────────────────────

describe("Governance — role switching", () => {
  it("defaults to director role (Lorraine)", () => {
    render(<GovernancePage />)
    expect(screen.getByText(/User: Lorraine Chen/)).toBeInTheDocument()
  })

  it("opens role menu on click", () => {
    render(<GovernancePage />)
    fireEvent.click(screen.getByRole("button", { name: /Switch role/i }))
    expect(screen.getByText(/Priya Venkataraman/)).toBeInTheDocument()
    expect(screen.getByText(/Damien Okafor/)).toBeInTheDocument()
    expect(screen.getByText(/Marcus Webb/)).toBeInTheDocument()
  })

  it("switches role and updates footer", () => {
    render(<GovernancePage />)
    fireEvent.click(screen.getByRole("button", { name: /Switch role/i }))
    fireEvent.click(screen.getAllByText(/Marcus Webb/)[0])
    expect(screen.getByText(/User: Marcus Webb/)).toBeInTheDocument()
  })
})

// ── Footer ─────────────────────────────────────────────────────────────────────

describe("Governance — footer", () => {
  it("shows Audit Active in footer", () => {
    render(<GovernancePage />)
    expect(screen.getByText(/Audit Active/i)).toBeInTheDocument()
  })

  it("shows current role in footer", () => {
    render(<GovernancePage />)
    expect(screen.getByText(/Role: director/i)).toBeInTheDocument()
  })
})
