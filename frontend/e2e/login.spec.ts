import { test, expect } from "@playwright/test";
import { setupPageMocks } from "./helpers";

test.beforeEach(async ({ page }) => {
  await setupPageMocks(page);
});

test("logs in and reaches the overview", async ({ page }) => {
  await page.goto("/login");

  await page.getByLabel(/username/i).fill("demo");
  await page.getByLabel(/password/i).fill("playsafe");
  await page.getByRole("button", { name: /login/i }).click();

  await expect(page).toHaveURL(/\/overview$/);
  await expect(page.getByText("Total Errors")).toBeVisible();
  await expect(page.getByText("Error Analysis")).toBeVisible();
});
