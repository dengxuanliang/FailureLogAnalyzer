import type { Page, Route } from "@playwright/test";

const JSON_HEADERS = { "Content-Type": "application/json; charset=utf-8" } as const;

const encodeBase64Url = (value: string) =>
  Buffer.from(value)
    .toString("base64")
    .replace(/=/g, "")
    .replace(/\+/g, "-")
    .replace(/\//g, "_");

const createMockJwt = () => {
  const header = encodeBase64Url(JSON.stringify({ alg: "none", typ: "JWT" }));
  const payload = encodeBase64Url(
    JSON.stringify({
      sub: "demo-user",
      role: "analyst",
      exp: Math.floor(Date.now() / 1000) + 3600,
    }),
  );
  return `${header}.${payload}.signature`;
};

const summaryResponse = {
  total_sessions: 1,
  total_records: 64,
  total_errors: 5,
  accuracy: 0.92,
  llm_analysed_count: 3,
  llm_total_cost: 1.23,
};

const distributionResponse = [
  { label: "Knowledge Errors", count: 3, percentage: 0.6 },
  { label: "Reasoning Errors", count: 2, percentage: 0.4 },
];

const trendsResponse = {
  data_points: [
    { period: "2026-03-22", error_rate: 0.2, total: 100, errors: 20 },
    { period: "2026-03-23", error_rate: 0.3, total: 120, errors: 36 },
  ],
};

const sessionsResponse = [
  {
    id: "session-1",
    model: "gpt-4.1",
    model_version: "2026-03-23",
    benchmark: "mmlu",
    dataset_name: "mmlu",
    total_count: 120,
    error_count: 5,
    accuracy: 0.958,
    tags: ["baseline"],
    created_at: new Date().toISOString(),
  },
];

const errorRecordsResponse = {
  items: [
    {
      id: "record-1",
      session_id: "session-1",
      benchmark: "mmlu",
      task_category: "Mathematics",
      question_id: "mmlu_math_001",
      question: "Mock question text for validation",
      is_correct: false,
      score: 0,
      error_tags: ["Reasoning Errors.逻辑推理.前提正确但推理链断裂"],
      has_llm_analysis: true,
    },
  ],
  total: 1,
  page: 1,
  size: 20,
};

const recordDetailResponse = {
  record: {
    id: "record-1",
    question: "Mock question text for validation",
    expected_answer: "42",
    model_answer: "41",
  },
  analysis_results: [
    {
      id: "result-1",
      analysis_type: "llm",
      error_types: ["推理性错误.逻辑推理.前提正确但推理链断裂"],
      root_cause: "Model dropped a critical premise in the third step.",
      severity: "high",
      confidence: 0.82,
      evidence: "The prompt asked for conditional reasoning, but the answer skipped condition C.",
      suggestion: "Reinforce conditional chaining training examples.",
      llm_model: "gpt-4.1",
      llm_cost: 0.035,
      unmatched_tags: [],
      created_at: new Date().toISOString(),
    },
  ],
  error_tags: [
    { tag_path: "推理性错误.逻辑推理.前提正确但推理链断裂" },
  ],
};

const loginResponse = {
  access_token: createMockJwt(),
  token_type: "bearer",
};

const fulfillJson = <T extends unknown>(route: Route, payload: T) =>
  route.fulfill({
    status: 200,
    headers: JSON_HEADERS,
    body: JSON.stringify(payload),
  });

const setupWebSocketShim = async (page: Page) => {
  await page.addInitScript(() => {
    class DummyWebSocket {
      static CONNECTING = 0;
      static OPEN = 1;
      static CLOSING = 2;
      static CLOSED = 3;

      readyState = DummyWebSocket.OPEN;
      onopen: ((event: Event) => void) | null = null;
      onmessage: ((event: MessageEvent) => void) | null = null;
      onerror: ((event: Event) => void) | null = null;
      onclose: ((event: CloseEvent) => void) | null = null;

      constructor(url: string) {
        this.dispatchEvent({ type: "open" });
      }

      send() {}

      close() {
        if (this.readyState === DummyWebSocket.CLOSED) {
          return;
        }
        this.readyState = DummyWebSocket.CLOSED;
        this.dispatchEvent({ type: "close" });
      }

      addEventListener() {}
      removeEventListener() {}

      private dispatchEvent(event: Event | CloseEvent) {
        if (event.type === "open" && this.onopen) {
          this.onopen(event);
        }
        if (event.type === "close" && this.onclose) {
          this.onclose(event as CloseEvent);
        }
      }
    }

    Object.defineProperty(window, "WebSocket", {
      value: DummyWebSocket,
      writable: true,
      configurable: true,
    });
  });
};

export async function setupPageMocks(page: Page) {
  await page.addInitScript(() => localStorage.setItem("i18nextLng", "en"));
  await setupWebSocketShim(page);

  await page.route("**/api/v1/auth/login", (route) => {
    if (route.request().method() !== "POST") {
      return route.continue();
    }
    fulfillJson(route, loginResponse);
  });

  await page.route("**/api/v1/analysis/summary", (route) => {
    fulfillJson(route, summaryResponse);
  });

  await page.route("**/api/v1/analysis/error-distribution**", (route) => {
    fulfillJson(route, distributionResponse);
  });

  await page.route("**/api/v1/trends", (route) => {
    fulfillJson(route, trendsResponse);
  });

  await page.route("**/api/v1/sessions", (route) => {
    fulfillJson(route, sessionsResponse);
  });

  await page.route("**/api/v1/analysis/records/*/detail", (route) => {
    fulfillJson(route, recordDetailResponse);
  });

  await page.route("**/api/v1/analysis/records**", (route) => {
    if (route.request().url().includes("/detail")) {
      return route.continue();
    }
    fulfillJson(route, errorRecordsResponse);
  });
}

export const DEMO_USERNAME = "demo";
export const DEMO_PASSWORD = "playsafe";
export const MOCK_RECORD_QUESTION = "Mock question text for validation";
