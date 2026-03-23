# Browser E2E (Playwright)

## Running locally

1. From the `frontend` directory, make sure dependencies are up to date and install the Playwright browsers:
   ```bash
   cd frontend
   npm install
   npx playwright install
   ```
2. The Playwright config automatically starts the Vite dev server (`npm run dev -- --host 127.0.0.1 --port 4173`) via the `webServer` hook, so no manual server start is needed.
3. Run the deterministic suite:
   ```bash
   npm run test:e2e
   ```

## How the tests stay deterministic

- Each spec stubs the `/api/v1` surface (`/auth/login`, `/analysis/*`, `/trends`, `/sessions`) through Playwright `page.route` handlers defined in `frontend/e2e/helpers.ts`.
- A `page.addInitScript` shim replaces `window.WebSocket` so background hooks (job notifications, agent chat) never hit real sockets.
- The suite reuses the same mock payloads for summary cards, distributions, error records, and the record detail drawer, so the assertions stay stable without a backend.
