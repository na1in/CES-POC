import { Page } from "@playwright/test"

/**
 * Log in as a given seed user by clicking their card on the login page.
 *
 * Seed users (from scripts/seed.py):
 *   USR-0001  Priya Sharma    Analyst
 *   USR-0002  Damien Torres   Investigator
 *   USR-0003  Lorraine Chen   Director
 *   USR-0004  Marcus Webb     Admin
 */
export async function loginAs(page: Page, name: string) {
  // Clear any existing session so RouteGuard doesn't bounce us from /login
  await page.goto("/")
  await page.evaluate(() => {
    localStorage.removeItem("ces_token")
    localStorage.removeItem("ces_user")
  })
  await page.goto("/login")
  await page.getByText(name).click()
  // Wait for redirect away from /login
  await page.waitForURL((url) => !url.pathname.includes("/login"), { timeout: 10000 })
}

export const ANALYST      = "Priya Sharma"
export const INVESTIGATOR = "Damien Torres"
export const DIRECTOR     = "Lorraine Chen"
export const ADMIN        = "Marcus Webb"
