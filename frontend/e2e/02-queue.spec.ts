import { test, expect } from "@playwright/test"
import { loginAs, ANALYST, INVESTIGATOR } from "./helpers/auth"

test.describe("Payment Queue", () => {
  test.beforeEach(async ({ page }) => {
    await loginAs(page, ANALYST)
  })

  test("shows queue heading and stat cards", async ({ page }) => {
    await expect(page.getByRole("heading", { name: /payment operations queue/i })).toBeVisible()
    await expect(page.getByText("Cases Open")).toBeVisible()
    await expect(page.getByText("Auto-Applied")).toBeVisible()
    await expect(page.getByText("On Hold")).toBeVisible()
    await expect(page.getByText("Escalated")).toBeVisible()
  })

  test("shows Open Cases and Closed Cases tabs", async ({ page }) => {
    await expect(page.getByRole("button", { name: /open cases/i })).toBeVisible()
    await expect(page.getByRole("button", { name: /closed cases/i })).toBeVisible()
  })

  test("shows table headers", async ({ page }) => {
    await expect(page.getByText("SENDER")).toBeVisible()
    await expect(page.getByText("AMOUNT")).toBeVisible()
    await expect(page.getByText("RECOMMENDATION")).toBeVisible()
    await expect(page.getByText("CONFIDENCE")).toBeVisible()
  })

  test("sort dropdown changes order", async ({ page }) => {
    const sort = page.getByRole("combobox", { name: /sort by/i })
    await expect(sort).toBeVisible()
    await sort.selectOption("confidence_desc")
    await expect(sort).toHaveValue("confidence_desc")
  })

  test("confidence filter chips are clickable", async ({ page }) => {
    const low = page.getByRole("button", { name: /^low$/i })
    await low.click()
    // Filter chip should remain visible (no crash)
    await expect(low).toBeVisible()
  })

  test("method filter chips are clickable", async ({ page }) => {
    const ach = page.getByRole("button", { name: /^ach$/i })
    await ach.click()
    await expect(ach).toBeVisible()
  })

  test("clicking a payment row navigates to detail", async ({ page }) => {
    // Wait for at least one row to appear
    const firstRow = page.getByRole("row").nth(1)
    await firstRow.waitFor({ timeout: 10000 })
    await firstRow.click()
    await expect(page).toHaveURL(/\/payments\/PMT-/)
  })

  test("investigator cannot access queue dashboard", async ({ page }) => {
    await loginAs(page, INVESTIGATOR)
    await expect(page).toHaveURL("/investigations")
  })
})
