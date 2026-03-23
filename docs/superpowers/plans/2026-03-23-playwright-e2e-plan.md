# Playwright E2E Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add deterministic Playwright coverage for login→overview and analysis/detail flows while keeping the backend fully mocked within the browser.

**Architecture:** Playwright launches the Vite dev server via `webServer`, installs route intercepts (including a WebSocket shim) through a shared helper, and drives the two key UI journeys to ensure the stat cards, navigation, treemap, error table, and drawer render from mocked API payloads.

**Tech Stack:** `@playwright/test`, Vite dev server, TypeScript helpers for mocks, route intercepts, docs in `docs/superpowers`.

---

### Task 1: Prepare Playwright tooling

**Files:**
- Modify: `frontend/package.json` (deps + `test:e2e` script)
- Modify: `frontend/package-lock.json`
- Create: `frontend/playwright.config.ts`

**Test:** `npx playwright test --help`

- [ ] **Step 1: Update npm config**
  ```json
  "devDependencies": {
    "@playwright/test": "^1.43.0",
    ...
  },
  "scripts": {
    "test:e2e": "playwright test",
    ...
  }
  ```

- [ ] **Step 2: Add Playwright config**
  ```ts
  import { defineConfig } from "@playwright/test";
  export default defineConfig({
    testDir: "./e2e",
    webServer: {
      command: "npm run dev -- --host 127.0.0.1 --port 4173",
      port: 4173,
      reuseExistingServer: true,
    },
  });
  ```

- [ ] **Step 3: Run npm install**
  ```bash
  cd frontend
  npm install
  ```

- [ ] **Step 4: Smoke Playwright CLI**
  ```bash
  cd frontend
  npx playwright test --help
  ```
  Expect: command exits 0 and prints usage (no tests yet).

- [ ] **Step 5: (Optional) Commit**
  ```bash
  git add frontend/package.json frontend/package-lock.json frontend/playwright.config.ts
  git commit -m "chore: add Playwright tooling"
  ```

### Task 2: Implement mocks + E2E specs

**Files:**
- Create: `frontend/e2e/helpers.ts`
- Create: `frontend/e2e/login.spec.ts`
- Create: `frontend/e2e/main-flow.spec.ts`

**Test:** `npx playwright test e2e/login.spec.ts`, `npx playwright test e2e/main-flow.spec.ts`, `npx playwright test`

- [ ] **Step 1: Add helper module** that exposes
  - `setupPageMocks(page: Page)` hooking `page.route` for `/auth/login`, `/analysis/summary`, `/trends`, `/analysis/error-distribution`, `/analysis/records`, `/analysis/records/:id/detail`, `/sessions`
  - `stubWebSocketShim(page)` via `page.addInitScript`
  - Mock data for summary, distribution, records, detail, and a `createMockJwt()` helper
  - Ensure `localStorage` gets `i18nextLng=en` before the app loads
  - Validate the helper is imported by both specs

- [ ] **Step 2: Write `login.spec.ts`**
  ```ts
  test("login to overview", async ({ page }) => {
    await setupMocks(page);
    await page.goto("/login");
    await page.getByLabel("Username").fill("demo");
    ...
    await page.getByRole("button", { name: "Login" }).click();
    await expect(page).toHaveURL(/\/overview$/);
    await expect(page.getByText("Overview")).toBeVisible();
    await expect(page.getByText("Total Errors")).toBeVisible();
  });
  ```
  - Run: `cd frontend && npx playwright test e2e/login.spec.ts`
  - Expect: PASS

- [ ] **Step 3: Write `main-flow.spec.ts`**
  ```ts
  test("navigate to error analysis and open detail", async ({ page }) => {
    await setupMocks(page);
    await page.goto("/login");
    ... // reuse login steps
    await page.getByText("Error Analysis").click();
    await expect(page.getByText("Error Type Distribution")).toBeVisible();
    await page.getByRole("button", { name: "View Detail" }).click();
    await expect(page.getByText("Mock question text")).toBeVisible();
  });
  ```
  - Run: `cd frontend && npx playwright test e2e/main-flow.spec.ts`
  - Expect: PASS

- [ ] **Step 4: Run full suite**
  ```bash
  cd frontend
  npx playwright test
  ```
  Expect: both specs pass

- [ ] **Step 5: Commit**
  ```bash
  git add frontend/e2e/helpers.ts frontend/e2e/login.spec.ts frontend/e2e/main-flow.spec.ts
  git commit -m "test: add Playwright E2E flows"
  ```

### Task 3: Document the E2E workflow

**Files:**
- Create: `docs/superpowers/e2e.md`

- [ ] **Step 1: Draft doc** explaining
  - Install browsers via `npx playwright install`
  - Run `npm run test:e2e` (or `npx playwright test`) from the `frontend` folder
  - Mention `VITE_API_BASE_URL` can remain default and the tests mock all API responses
  - Reference the WebSocket shim and login/demo credential

- [ ] **Step 2: (Optional) Commit**
  ```bash
  git add docs/superpowers/e2e.md
  git commit -m "docs: describe E2E workflow"
  ```
