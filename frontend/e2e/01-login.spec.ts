import { test, expect } from "@playwright/test"
import { loginAs, ANALYST, INVESTIGATOR, DIRECTOR, ADMIN } from "./helpers/auth"

test.describe("Login", () => {
  test("shows four user cards on the login page", async ({ page }) => {
    await page.goto("/login")
    await expect(page.getByText("Priya Sharma")).toBeVisible()
    await expect(page.getByText("Damien Torres")).toBeVisible()
    await expect(page.getByText("Lorraine Chen")).toBeVisible()
    await expect(page.getByText("Marcus Webb")).toBeVisible()
  })

  test("analyst lands on queue dashboard", async ({ page }) => {
    await loginAs(page, ANALYST)
    await expect(page).toHaveURL("/")
    await expect(page.getByRole("heading", { name: /payment queue/i })).toBeVisible()
  })

  test("investigator lands on investigation queue", async ({ page }) => {
    await loginAs(page, INVESTIGATOR)
    await expect(page).toHaveURL("/investigations")
  })

  test("director lands on governance dashboard", async ({ page }) => {
    await loginAs(page, DIRECTOR)
    await expect(page).toHaveURL("/governance")
  })

  test("admin lands on admin dashboard", async ({ page }) => {
    await loginAs(page, ADMIN)
    await expect(page).toHaveURL("/admin")
  })

  test("sign out returns to login page", async ({ page }) => {
    await loginAs(page, ANALYST)
    // Open user menu and sign out
    await page.getByRole("button", { name: /priya/i }).click()
    await page.getByText(/sign out/i).click()
    await expect(page).toHaveURL("/login")
  })

  test("unauthenticated visit to / redirects to login", async ({ page }) => {
    await page.goto("/")
    await expect(page).toHaveURL(/\/login/)
  })
})
