# Playwright E2E for FailureLogAnalyzer

> Date: 2026-03-23
> Status: Draft

## 1. Objective

Provide deterministic browser-level regression coverage for the frontend by running Playwright tests against the real Vite dev server while stubbing the minimal API surface (auth, overview, analysis) inside the Playwright session. The tests should exercise the login flow and the core exploration path (Overview → Error Analysis → Record Detail) without depending on a real backend or WebSocket streams.

## 2. Architectural approach

- **Execution target**: Playwright will launch against the local Vite dev server (e.g., http://127.0.0.1:4173) with `webServer` support so tests can run from CLI without starting the server manually.
- **Mocking strategy**: Use Playwright route intercepts and `page.addInitScript` to stub every `/api/v1` call the UI makes during the happy-path login and analysis journeys: auth/login, analysis summary/distributions/records/details, trends, and the sessions list used by the filter bar. A lightweight `WebSocket` shim prevents `useJobNotifications`/agent websocket hooks from reaching the network.
- **Data model**: Mocks return small but realistic payloads (stat cards, error distribution, records with tags/details) that the UI renders verbatim, which keeps assertions stable and meaningful.

## 3. Tests to ship

1. **Login & Overview readiness**
   - Visit `/login`, fill a demo username/password, and submit the form.
   - Assert that `/overview` loads, navigation links appear, and at least one stat card (e.g., “Total Errors”) renders the stubbed value. This proves auth, redirect, filter bar session fetch, and stat widgets work together.
2. **Main analysis flow**
   - After login, click the “Error Analysis” navigation item.
   - Wait for the treemap and error table to render using the mocked distributions/records.
   - Click “View Detail” on the stubbed record and assert the detail drawer shows the expected question text and a blue LLM analysis card.

## 4. Supporting artifacts

- **Playwright config**: resides in `frontend/playwright.config.ts` and defines the base URL, viewport, retries, and `webServer` command that runs `npm run dev -- --host 127.0.0.1 --port 4173`.
- **Helpers**: `frontend/e2e/helpers.ts` exports the shared mock payloads, JWT creation, and a `setupPageMocks(page)` helper that installs route intercepts plus the WebSocket shim and consistent locale (`en`).
- **Documentation**: a short snippet under `docs/superpowers/e2e.md` outlines how to install Playwright browsers and run the new `npm run test:e2e` script.

This design keeps the browser flow grounded in the real UI while keeping external dependencies fake and deterministic, satisfying the “stable, lightweight local/dev friendly” requirement.
