/**
 * CES-37 — Admin Dashboard tests
 *
 * Covers: page structure, scenario tabs, tab switching updates all data,
 * summary tiles, chart sections, navigation, role switching, footer.
 */

import { render, screen, fireEvent } from "@testing-library/react"
import { useRouter } from "next/navigation"
import AdminDashboardPage from "@/app/admin/page"
import { mockAdminAnalytics } from "@/mocks/analytics"

jest.mock("recharts", () => {
  const React = require("react")
  const Passthrough = ({ children }: { children?: React.ReactNode }) => React.createElement("div", null, children)
  return {
    LineChart: Passthrough,
    BarChart: Passthrough,
    PieChart: Passthrough,
    Line: () => null,
    Bar: () => null,
    Pie: () => null,
    Cell: () => null,
    XAxis: () => null,
    YAxis: () => null,
    CartesianGrid: () => null,
    Tooltip: () => null,
    Legend: () => null,
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

// ── Page structure ─────────────────────────────────────────────────────────────

describe("Admin Dashboard — page structure", () => {
  it("renders the page heading", () => {
    render(<AdminDashboardPage />)
    expect(screen.getByRole("heading", { name: /Admin Dashboard/i })).toBeInTheDocument()
  })

  it("shows the page subtitle", () => {
    render(<AdminDashboardPage />)
    expect(screen.getByText(/Per-scenario AI performance analytics/i)).toBeInTheDocument()
  })

  it("shows all four chart section titles", () => {
    render(<AdminDashboardPage />)
    expect(screen.getByText("Case Volume Trend")).toBeInTheDocument()
    expect(screen.getByText("Decision Distribution")).toBeInTheDocument()
    expect(screen.getByText("Override Rate by Confidence Band")).toBeInTheDocument()
    expect(screen.getByText("Confidence Score Histogram")).toBeInTheDocument()
  })
})

// ── Scenario tabs ──────────────────────────────────────────────────────────────

describe("Admin Dashboard — scenario tabs", () => {
  it("renders all six tabs", () => {
    render(<AdminDashboardPage />)
    expect(screen.getByRole("button", { name: "All" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Scenario 1" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Scenario 2" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Scenario 3" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Scenario 4" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Scenario 5" })).toBeInTheDocument()
  })

  it("All tab is selected by default", () => {
    render(<AdminDashboardPage />)
    expect(screen.getByRole("button", { name: "All" })).toHaveAttribute("aria-selected", "true")
  })

  it("other tabs are not selected by default", () => {
    render(<AdminDashboardPage />)
    expect(screen.getByRole("button", { name: "Scenario 1" })).toHaveAttribute("aria-selected", "false")
  })

  it("clicking a tab marks it as selected", () => {
    render(<AdminDashboardPage />)
    fireEvent.click(screen.getByRole("button", { name: "Scenario 1" }))
    expect(screen.getByRole("button", { name: "Scenario 1" })).toHaveAttribute("aria-selected", "true")
  })

  it("clicking a tab deselects the previous tab", () => {
    render(<AdminDashboardPage />)
    fireEvent.click(screen.getByRole("button", { name: "Scenario 2" }))
    expect(screen.getByRole("button", { name: "All" })).toHaveAttribute("aria-selected", "false")
  })
})

// ── Summary tiles — All tab ────────────────────────────────────────────────────

describe("Admin Dashboard — summary tiles (All tab)", () => {
  it("shows Volume label", () => {
    render(<AdminDashboardPage />)
    expect(screen.getByText("Volume")).toBeInTheDocument()
  })

  it("shows correct volume for All tab", () => {
    render(<AdminDashboardPage />)
    expect(screen.getByText(mockAdminAnalytics.all.volume.toLocaleString())).toBeInTheDocument()
  })

  it("shows Avg Confidence label", () => {
    render(<AdminDashboardPage />)
    expect(screen.getByText("Avg Confidence")).toBeInTheDocument()
  })

  it("shows correct avg confidence for All tab", () => {
    render(<AdminDashboardPage />)
    expect(screen.getByText(`${mockAdminAnalytics.all.avg_confidence}%`)).toBeInTheDocument()
  })

  it("shows Override Count label", () => {
    render(<AdminDashboardPage />)
    expect(screen.getByText("Override Count")).toBeInTheDocument()
  })

  it("shows correct override count for All tab", () => {
    render(<AdminDashboardPage />)
    expect(screen.getByText(String(mockAdminAnalytics.all.override_count))).toBeInTheDocument()
  })
})

// ── Tab switching updates all data ─────────────────────────────────────────────

describe("Admin Dashboard — tab switching updates stats", () => {
  it("switching to Scenario 1 shows scenario 1 volume", () => {
    render(<AdminDashboardPage />)
    fireEvent.click(screen.getByRole("button", { name: "Scenario 1" }))
    expect(screen.getByText(mockAdminAnalytics.scenario_1.volume.toLocaleString())).toBeInTheDocument()
  })

  it("switching to Scenario 1 shows scenario 1 avg confidence", () => {
    render(<AdminDashboardPage />)
    fireEvent.click(screen.getByRole("button", { name: "Scenario 1" }))
    expect(screen.getByText(`${mockAdminAnalytics.scenario_1.avg_confidence}%`)).toBeInTheDocument()
  })

  it("switching to Scenario 1 shows scenario 1 override count", () => {
    render(<AdminDashboardPage />)
    fireEvent.click(screen.getByRole("button", { name: "Scenario 1" }))
    expect(screen.getByText(String(mockAdminAnalytics.scenario_1.override_count))).toBeInTheDocument()
  })

  it("switching to Scenario 2 shows scenario 2 volume", () => {
    render(<AdminDashboardPage />)
    fireEvent.click(screen.getByRole("button", { name: "Scenario 2" }))
    expect(screen.getByText(mockAdminAnalytics.scenario_2.volume.toLocaleString())).toBeInTheDocument()
  })

  it("switching back to All restores All data", () => {
    render(<AdminDashboardPage />)
    fireEvent.click(screen.getByRole("button", { name: "Scenario 3" }))
    fireEvent.click(screen.getByRole("button", { name: "All" }))
    expect(screen.getByText(mockAdminAnalytics.all.volume.toLocaleString())).toBeInTheDocument()
  })

  it("each scenario shows distinct volume values", () => {
    render(<AdminDashboardPage />)
    // Verify scenario volumes are not all the same as "All"
    fireEvent.click(screen.getByRole("button", { name: "Scenario 4" }))
    expect(screen.getByText(mockAdminAnalytics.scenario_4.volume.toLocaleString())).toBeInTheDocument()
    expect(screen.queryByText(mockAdminAnalytics.all.volume.toLocaleString())).not.toBeInTheDocument()
  })
})

// ── Navigation ─────────────────────────────────────────────────────────────────

describe("Admin Dashboard — navigation", () => {
  it("clicking PayWise logo navigates home", () => {
    render(<AdminDashboardPage />)
    fireEvent.click(screen.getByText("PayWise"))
    expect(mockPush).toHaveBeenCalledWith("/")
  })

  it("clicking Override Analysis navigates to /admin/overrides", () => {
    render(<AdminDashboardPage />)
    fireEvent.click(screen.getByRole("button", { name: /Override Analysis/i }))
    expect(mockPush).toHaveBeenCalledWith("/admin/overrides")
  })

  it("clicking Config Management navigates to /admin/config", () => {
    render(<AdminDashboardPage />)
    fireEvent.click(screen.getByRole("button", { name: /Config Management/i }))
    expect(mockPush).toHaveBeenCalledWith("/admin/config")
  })
})

// ── Role switching ─────────────────────────────────────────────────────────────

describe("Admin Dashboard — role switching", () => {
  it("defaults to admin role (Marcus)", () => {
    render(<AdminDashboardPage />)
    expect(screen.getByText(/User: Marcus Webb/)).toBeInTheDocument()
  })

  it("opens role menu on click", () => {
    render(<AdminDashboardPage />)
    fireEvent.click(screen.getByRole("button", { name: /Switch role/i }))
    expect(screen.getByText(/Priya Venkataraman/)).toBeInTheDocument()
    expect(screen.getByText(/Lorraine Chen/)).toBeInTheDocument()
  })

  it("switches role and updates footer", () => {
    render(<AdminDashboardPage />)
    fireEvent.click(screen.getByRole("button", { name: /Switch role/i }))
    fireEvent.click(screen.getAllByText(/Lorraine Chen/)[0])
    expect(screen.getByText(/User: Lorraine Chen/)).toBeInTheDocument()
  })
})

// ── Footer ─────────────────────────────────────────────────────────────────────

describe("Admin Dashboard — footer", () => {
  it("shows Audit Active", () => {
    render(<AdminDashboardPage />)
    expect(screen.getByText(/Audit Active/i)).toBeInTheDocument()
  })

  it("shows current role in footer", () => {
    render(<AdminDashboardPage />)
    expect(screen.getByText(/Role: admin/i)).toBeInTheDocument()
  })
})
