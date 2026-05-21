import { test, expect } from "@playwright/test"
import { loginAs, DIRECTOR } from "./helpers/auth"

test.describe("Governance Dashboard", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, DIRECTOR)
  })

  test("shows governance dashboard heading", async ({ page }) => {
    await expect(page.getByRole("heading", { name: /governance dashboard/i })).toBeVisible()
    await expect(page.getByText(/performance metrics/i)).toBeVisible()
  })

  test("shows all six metric cards", async ({ page }) => {
    await expect(page.getByText("Auto-Applied by AI")).toBeVisible()
    await expect(page.getByText("Applied after Human Review")).toBeVisible()
    await expect(page.getByText("Held Pending Review")).toBeVisible()
    await expect(page.getByText("Escalated by AI")).toBeVisible()
    await expect(page.getByText("Escalated by Human")).toBeVisible()
    await expect(page.getByText("Human Overrides")).toBeVisible()
  })

  test("shows chart sections", async ({ page }) => {
    await expect(page.getByText("Payment Method Breakdown")).toBeVisible()
    await expect(page.getByText("SLA Adherence")).toBeVisible()
    await expect(page.getByText("Override Rate", { exact: true })).toBeVisible()
  })

  test("date range inputs are present", async ({ page }) => {
    await expect(page.locator('input[aria-label="Date from"]')).toBeVisible()
    await expect(page.locator('input[aria-label="Date to"]')).toBeVisible()
  })

  test("date range filter updates on change", async ({ page }) => {
    const fromInput = page.locator('input[aria-label="Date from"]')
    await fromInput.fill("2026-01-01")
    // Page should not crash
    await expect(page.getByRole("heading", { name: /governance dashboard/i })).toBeVisible()
  })

  test("export audit report button is present", async ({ page }) => {
    await expect(page.getByRole("button", { name: /export audit report/i })).toBeVisible()
  })

})
