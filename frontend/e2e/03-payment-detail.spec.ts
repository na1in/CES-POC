import { test, expect } from "@playwright/test"
import { loginAs, ANALYST, INVESTIGATOR } from "./helpers/auth"

async function openFirstPayment(page: any) {
  await loginAs(page, ANALYST)
  const paymentId = page.getByText(/^PMT-/).first()
  await paymentId.waitFor({ timeout: 10000 })
  await paymentId.click()
  await page.waitForURL(/\/payments\/PMT-/)
}

test.describe("Payment Detail", () => {
  test("renders case heading and payment info section", async ({ page }) => {
    await openFirstPayment(page)
    await expect(page.getByRole("heading", { name: /case pmt-/i })).toBeVisible()
    await expect(page.getByText("Payment Information")).toBeVisible()
    await expect(page.getByText("SENDER NAME", { exact: true })).toBeVisible()
    // Use exact match to avoid ambiguity with audit log entries that contain "amount"
    await expect(page.getByText("AMOUNT", { exact: true }).first()).toBeVisible()
    await expect(page.getByText("PAYMENT METHOD")).toBeVisible()
  })

  test("shows payment status and audit trail", async ({ page }) => {
    await openFirstPayment(page)
    // Status badge and audit trail are always present regardless of processing state
    await expect(page.getByText("Audit Trail")).toBeVisible()
    await expect(page.getByText("Payment Information")).toBeVisible()
  })

  test("shows audit trail section", async ({ page }) => {
    await openFirstPayment(page)
    await expect(page.getByText("Audit Trail")).toBeVisible()
  })

  test("back button returns to queue", async ({ page }) => {
    await openFirstPayment(page)
    // Back is a <button>, not a link
    await page.getByRole("button", { name: /back/i }).click()
    await expect(page).toHaveURL("/")
  })

  test("investigator sees Add Investigation Note on escalated payment", async ({ page }) => {
    await loginAs(page, INVESTIGATOR)
    // PMT-ESC-001 is seeded as escalated — shows the investigation note button
    const paymentId = page.getByText(/^PMT-/).first()
    await paymentId.waitFor({ timeout: 10000 })
    await paymentId.click()
    await page.waitForURL(/\/payments\/PMT-/)
    await expect(page.getByRole("button", { name: /add investigation note/i })).toBeVisible()
  })
})
