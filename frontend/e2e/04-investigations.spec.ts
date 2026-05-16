import { test, expect } from "@playwright/test"
import { loginAs, INVESTIGATOR, ANALYST } from "./helpers/auth"

test.describe("Investigation Queue", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, INVESTIGATOR)
  })

  test("shows investigation queue heading", async ({ page }) => {
    await expect(page.getByRole("heading", { name: /investigation queue/i })).toBeVisible()
    await expect(page.getByText(/escalated cases requiring specialist investigation/i)).toBeVisible()
  })

  test("shows stat cards", async ({ page }) => {
    await expect(page.getByText("Open Investigations")).toBeVisible()
    await expect(page.getByText("Fraud Flagged")).toBeVisible()
    await expect(page.getByText("Pending Outreach")).toBeVisible()
    await expect(page.getByText("Cases Closed Today")).toBeVisible()
  })

  test("shows escalated cases table or empty state", async ({ page }) => {
    const hasRows = await page.getByRole("row").count()
    if (hasRows > 1) {
      await expect(page.getByText("CASE ID")).toBeVisible()
      await expect(page.getByText("RISK LEVEL")).toBeVisible()
      await expect(page.getByText("SENDER")).toBeVisible()
    } else {
      await expect(page.getByText(/no escalated cases/i)).toBeVisible()
    }
  })

  test("clicking a case row navigates to payment detail", async ({ page }) => {
    const row = page.getByRole("row").nth(1)
    const hasRow = await row.isVisible().catch(() => false)
    if (!hasRow) {
      test.skip()
      return
    }
    await row.click()
    await expect(page).toHaveURL(/\/payments\/PMT-/)
  })

  test("analyst cannot access investigations page", async ({ page }) => {
    await loginAs(page, ANALYST)
    // Analyst starts at / — trying to navigate to /investigations should redirect or stay at /
    await page.goto("/investigations")
    // Should be redirected away (back to / or /login)
    await expect(page).not.toHaveURL("/investigations")
  })

  test("export case list button is present", async ({ page }) => {
    await expect(page.getByRole("button", { name: /export case list/i })).toBeVisible()
  })
})
