/**
 * CES-16 — Settings page tests
 *
 * Covers: all 8 thresholds shown, column headers, Propose Change button
 * visible only for admin role, non-admin notice, role switching, navigation.
 */

import { render, screen, fireEvent } from "@testing-library/react"
import { useRouter } from "next/navigation"
import SettingsPage from "@/app/settings/page"
import { mockThresholds } from "@/mocks/thresholds"

jest.mock("next/navigation", () => ({
  useRouter: jest.fn(),
}))

const mockPush = jest.fn()

beforeEach(() => {
  mockPush.mockClear()
  ;(useRouter as jest.Mock).mockReturnValue({ push: mockPush })
})

// ── All thresholds shown ───────────────────────────────────────────────────────

describe("Settings — threshold table", () => {
  it("shows all 8 thresholds", () => {
    render(<SettingsPage />)
    mockThresholds.forEach(t => {
      expect(screen.getByText(t.parameter_name)).toBeInTheDocument()
    })
  })

  it("shows all threshold values", () => {
    render(<SettingsPage />)
    mockThresholds.forEach(t => {
      expect(screen.getByText(t.parameter_value)).toBeInTheDocument()
    })
  })

  it("shows all threshold descriptions", () => {
    render(<SettingsPage />)
    mockThresholds.forEach(t => {
      expect(screen.getByText(t.description)).toBeInTheDocument()
    })
  })

  it("shows PARAMETER column header", () => {
    render(<SettingsPage />)
    expect(screen.getByText("PARAMETER")).toBeInTheDocument()
  })

  it("shows VALUE column header", () => {
    render(<SettingsPage />)
    expect(screen.getByText("VALUE")).toBeInTheDocument()
  })

  it("shows DESCRIPTION column header", () => {
    render(<SettingsPage />)
    expect(screen.getByText("DESCRIPTION")).toBeInTheDocument()
  })

  it("shows LAST CHANGED column header", () => {
    render(<SettingsPage />)
    expect(screen.getByText("LAST CHANGED")).toBeInTheDocument()
  })

  it("shows the correct total threshold count in the footer note", () => {
    render(<SettingsPage />)
    expect(screen.getByText(/8 thresholds/i)).toBeInTheDocument()
  })
})

// ── Specific threshold values ─────────────────────────────────────────────────

describe("Settings — specific threshold values", () => {
  it("shows name_match_auto_apply with value 90%", () => {
    render(<SettingsPage />)
    expect(screen.getByText("name_match_auto_apply")).toBeInTheDocument()
    expect(screen.getByText("90%")).toBeInTheDocument()
  })

  it("shows duplicate_window_hours with value 72h", () => {
    render(<SettingsPage />)
    expect(screen.getByText("duplicate_window_hours")).toBeInTheDocument()
    expect(screen.getByText("72h")).toBeInTheDocument()
  })

  it("shows duplicate_amount_tolerance_cents with value $2.00", () => {
    render(<SettingsPage />)
    expect(screen.getByText("duplicate_amount_tolerance_cents")).toBeInTheDocument()
    expect(screen.getByText("$2.00")).toBeInTheDocument()
  })
})

// ── Non-admin role (default) ───────────────────────────────────────────────────

describe("Settings — non-admin (analyst, default)", () => {
  it("shows the admin notice for non-admin users", () => {
    render(<SettingsPage />)
    expect(screen.getByText(/contact your admin to request threshold changes/i)).toBeInTheDocument()
  })

  it("does not show Propose Change buttons for non-admin", () => {
    render(<SettingsPage />)
    expect(screen.queryByRole("button", { name: /Propose Change/i })).not.toBeInTheDocument()
  })

  it("does not show ACTION column header for non-admin", () => {
    render(<SettingsPage />)
    expect(screen.queryByText("ACTION")).not.toBeInTheDocument()
  })
})

// ── Admin role ────────────────────────────────────────────────────────────────

describe("Settings — admin role (Marcus)", () => {
  function switchToAdmin() {
    render(<SettingsPage />)
    fireEvent.click(screen.getByRole("button", { name: /Switch role/i }))
    fireEvent.click(screen.getByText(/Marcus Webb/))
  }

  it("shows Propose Change button for each threshold when admin", () => {
    switchToAdmin()
    const proposeButtons = screen.getAllByRole("button", { name: /Propose Change/i })
    expect(proposeButtons.length).toBe(mockThresholds.length)
  })

  it("shows ACTION column header for admin", () => {
    switchToAdmin()
    expect(screen.getByText("ACTION")).toBeInTheDocument()
  })

  it("does not show the non-admin notice when admin", () => {
    switchToAdmin()
    expect(screen.queryByText(/contact your admin to request threshold changes/i)).not.toBeInTheDocument()
  })

  it("clicking Propose Change navigates to /admin/config", () => {
    switchToAdmin()
    const buttons = screen.getAllByRole("button", { name: /Propose Change/i })
    fireEvent.click(buttons[0])
    expect(mockPush).toHaveBeenCalledWith("/admin/config")
  })
})

// ── Role switching ────────────────────────────────────────────────────────────

describe("Settings — role switching", () => {
  it("shows role menu when role button is clicked", () => {
    render(<SettingsPage />)
    fireEvent.click(screen.getByRole("button", { name: /Switch role/i }))
    expect(screen.getByText(/Damien Okafor/)).toBeInTheDocument()
    expect(screen.getByText(/Lorraine Chen/)).toBeInTheDocument()
    expect(screen.getByText(/Marcus Webb/)).toBeInTheDocument()
  })

  it("shows current user name in footer after switching role", () => {
    render(<SettingsPage />)
    // Default is analyst: Priya Venkataraman
    expect(screen.getByText(/Priya Venkataraman/)).toBeInTheDocument()
    // Switch to director
    fireEvent.click(screen.getByRole("button", { name: /Switch role/i }))
    fireEvent.click(screen.getByText(/Lorraine Chen/))
    expect(screen.getByText(/Lorraine Chen/)).toBeInTheDocument()
  })

  it("investigator role shows non-admin notice", () => {
    render(<SettingsPage />)
    fireEvent.click(screen.getByRole("button", { name: /Switch role/i }))
    fireEvent.click(screen.getByText(/Damien Okafor/))
    expect(screen.getByText(/contact your admin to request threshold changes/i)).toBeInTheDocument()
  })

  it("director role shows non-admin notice", () => {
    render(<SettingsPage />)
    fireEvent.click(screen.getByRole("button", { name: /Switch role/i }))
    fireEvent.click(screen.getByText(/Lorraine Chen/))
    expect(screen.getByText(/contact your admin to request threshold changes/i)).toBeInTheDocument()
  })
})

// ── Navigation ────────────────────────────────────────────────────────────────

describe("Settings — navigation", () => {
  it("shows Settings heading", () => {
    render(<SettingsPage />)
    expect(screen.getByRole("heading", { name: /Settings/i })).toBeInTheDocument()
  })

  it("clicking PayWise logo navigates to home", () => {
    render(<SettingsPage />)
    fireEvent.click(screen.getByText("PayWise"))
    expect(mockPush).toHaveBeenCalledWith("/")
  })
})

// ── Footer ────────────────────────────────────────────────────────────────────

describe("Settings — footer", () => {
  it("shows Audit Active in footer", () => {
    render(<SettingsPage />)
    expect(screen.getByText(/Audit Active/i)).toBeInTheDocument()
  })

  it("shows current role in footer", () => {
    render(<SettingsPage />)
    expect(screen.getByText(/Role: analyst/i)).toBeInTheDocument()
  })
})
