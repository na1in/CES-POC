import { test, expect } from "@playwright/test"
import { loginAs, INVESTIGATOR } from "./helpers/auth"

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
    // PMT-ESC-001 is seeded as an escalated payment for this test
    const paymentId = page.getByText(/^PMT-/).first()
    await paymentId.waitFor({ timeout: 10000 })
    await paymentId.click()
    await expect(page).toHaveURL(/\/payments\/PMT-/)
  })

  test("export case list button is present", async ({ page }) => {
    await expect(page.getByRole("button", { name: /export case list/i })).toBeVisible()
  })
})
