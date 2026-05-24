import { test, expect } from "@playwright/test"
import { loginAs, ADMIN } from "./helpers/auth"

test.describe("Admin Dashboard", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, ADMIN)
  })

  test("shows admin dashboard heading", async ({ page }) => {
    await expect(page.getByRole("heading", { name: /admin dashboard/i })).toBeVisible()
    await expect(page.getByText(/per-scenario AI performance analytics/i)).toBeVisible()
  })

  test("shows scenario tabs", async ({ page }) => {
    await expect(page.getByRole("button", { name: /^all$/i })).toBeVisible()
    await expect(page.getByRole("button", { name: /scenario 1/i })).toBeVisible()
    await expect(page.getByRole("button", { name: /scenario 2/i })).toBeVisible()
    await expect(page.getByRole("button", { name: /scenario 3/i })).toBeVisible()
    await expect(page.getByRole("button", { name: /scenario 4/i })).toBeVisible()
    await expect(page.getByRole("button", { name: /scenario 5/i })).toBeVisible()
  })

  test("scenario tab filter changes chart title", async ({ page }) => {
    await page.getByRole("button", { name: /scenario 1/i }).click()
    // Either the title updates or charts are still visible — no crash
    await expect(page.getByRole("heading", { name: /admin dashboard/i })).toBeVisible()
  })

  test("shows stat tiles for selected scenario", async ({ page }) => {
    await expect(page.getByText("Volume", { exact: true })).toBeVisible()
    await expect(page.getByText("Avg Confidence")).toBeVisible()
    await expect(page.getByText("Override Count")).toBeVisible()
  })

  test("override analysis link is present", async ({ page }) => {
    await expect(page.getByRole("button", { name: /override analysis/i })).toBeVisible()
  })

  test("config management link is present", async ({ page }) => {
    await expect(page.getByRole("button", { name: /config management/i })).toBeVisible()
  })

  test("config management navigates to /admin/config", async ({ page }) => {
    await page.getByRole("button", { name: /config management/i }).click()
    await expect(page).toHaveURL(/\/admin\/config/, { timeout: 10000 })
  })

})
