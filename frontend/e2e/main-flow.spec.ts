import { test, expect } from "@playwright/test";
import { MOCK_RECORD_QUESTION, setupPageMocks } from "./helpers";

test.beforeEach(async ({ page }) => {
  await setupPageMocks(page);
});

test("opens error analysis and record detail", async ({ page }) => {
  await page.goto("/login");

  await page.getByLabel(/username/i).fill("demo");
  await page.getByLabel(/password/i).fill("playsafe");
  await page.getByRole("button", { name: /login/i }).click();

  await expect(page.getByText("Error Analysis")).toBeVisible();

  await page.getByText("Error Analysis").click();
  await expect(page.getByText("Error Type Distribution")).toBeVisible();

  await page.getByRole("button", { name: /view detail/i }).click();
  await expect(page.getByText(MOCK_RECORD_QUESTION)).toBeVisible();
});
