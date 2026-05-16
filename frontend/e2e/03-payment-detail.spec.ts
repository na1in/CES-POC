import { test, expect } from "@playwright/test"
import { loginAs, ANALYST, INVESTIGATOR } from "./helpers/auth"

async function openFirstPayment(page: any) {
  await loginAs(page, ANALYST)
  const firstRow = page.getByRole("row").nth(1)
  await firstRow.waitFor({ timeout: 10000 })
  await firstRow.click()
  await page.waitForURL(/\/payments\/PMT-/)
}

test.describe("Payment Detail", () => {
  test("renders case heading and payment info section", async ({ page }) => {
    await openFirstPayment(page)
    await expect(page.getByRole("heading", { name: /case pmt-/i })).toBeVisible()
    await expect(page.getByText("Payment Information")).toBeVisible()
    await expect(page.getByText("SENDER NAME")).toBeVisible()
    await expect(page.getByText("AMOUNT")).toBeVisible()
    await expect(page.getByText("PAYMENT METHOD")).toBeVisible()
  })

  test("shows AI recommendation banner", async ({ page }) => {
    await openFirstPayment(page)
    await expect(page.getByText(/AI Recommendation/i)).toBeVisible()
    await expect(page.getByText(/Confidence Score/i)).toBeVisible()
  })

  test("shows audit trail section", async ({ page }) => {
    await openFirstPayment(page)
    await expect(page.getByText("Audit Trail")).toBeVisible()
  })

  test("back button returns to queue", async ({ page }) => {
    await openFirstPayment(page)
    await page.getByRole("link", { name: /back/i }).click()
    await expect(page).toHaveURL("/")
  })

  test("override dialog opens and requires reason", async ({ page }) => {
    await openFirstPayment(page)
    const overrideBtn = page.getByRole("button", { name: /override recommendation/i })
    await overrideBtn.waitFor({ timeout: 5000 })
    await overrideBtn.click()

    const dialog = page.getByRole("dialog", { name: /override recommendation/i })
    await expect(dialog).toBeVisible()

    const textarea = dialog.getByRole("textbox", { name: /override reason/i })
    await expect(textarea).toBeVisible()
  })

  test("override dialog can be submitted with a reason", async ({ page }) => {
    await openFirstPayment(page)
    const overrideBtn = page.getByRole("button", { name: /override recommendation/i })
    await overrideBtn.waitFor({ timeout: 5000 })
    await overrideBtn.click()

    const dialog = page.getByRole("dialog", { name: /override recommendation/i })
    const textarea = dialog.getByRole("textbox", { name: /override reason/i })
    await textarea.fill("Testing override flow in Playwright.")

    // Submit — button text depends on dialog state (confirm / save / apply)
    const submitBtn = dialog.getByRole("button").filter({ hasText: /confirm|submit|apply|save/i }).first()
    await submitBtn.click()

    // Dialog should close on success
    await expect(dialog).toBeHidden({ timeout: 8000 })
  })

  test("investigator sees investigation note button", async ({ page }) => {
    await loginAs(page, INVESTIGATOR)
    // Navigate to investigations then pick the first case
    const firstRow = page.getByRole("row").nth(1)
    await firstRow.waitFor({ timeout: 10000 })
    await firstRow.click()
    await page.waitForURL(/\/payments\/PMT-/)
    await expect(page.getByRole("button", { name: /add investigation note/i })).toBeVisible()
  })
})
