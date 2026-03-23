import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { jest } from "@jest/globals";

const apiClientMock: any = {
  get: jest.fn(),
  post: jest.fn(),
};

await jest.unstable_mockModule("../client", () => ({
  __esModule: true,
  default: apiClientMock,
}));

const {
  useIngestUpload,
  useIngestJobStatusQueries,
  useLlmJobStatusQueries,
  useLlmStrategies,
  useTriggerLlmJob,
} = await import("./operations");

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe("operations query hooks", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    Object.defineProperty(window, "fetch", {
      writable: true,
      value: jest.fn(),
    });
    localStorage.clear();
  });

  it("uploads ingest files via multipart request", async () => {
    localStorage.setItem("token", "token-123");
    (window.fetch as any).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ job_id: "ingest-1", session_id: "sess-1", message: "queued" }),
    });

    const { result } = renderHook(() => useIngestUpload(), {
      wrapper: createWrapper(),
    });

    const file = new window.File(['{"q":"x"}\n'], "data.jsonl", { type: "application/json" });

    await act(async () => {
      await result.current.mutateAsync({
        file,
        benchmark: "mmlu",
        model: "gpt-4o",
        model_version: "v1",
      });
    });

    expect(window.fetch).toHaveBeenCalledTimes(1);
    const [url, options] = (window.fetch as any).mock.calls[0] as [string, { method: string; headers?: Record<string, string>; body?: unknown }];
    expect(url).toBe("/api/v1/ingest/upload");
    expect(options.method).toBe("POST");
    expect(options.headers).toEqual({ Authorization: "Bearer token-123" });
    expect(options.body).toBeInstanceOf(globalThis.FormData);
  });

  it("polls ingest and llm job statuses for tracked jobs", async () => {
    apiClientMock.get.mockImplementation(async (url: string) => ({ data: { job_id: url, status: "pending" } }));

    const { result } = renderHook(
      () => ({
        ingest: useIngestJobStatusQueries(["ing-1", "ing-2"]),
        llm: useLlmJobStatusQueries(["llm-1"]),
      }),
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(result.current.ingest[0]?.isSuccess).toBe(true);
      expect(result.current.ingest[1]?.isSuccess).toBe(true);
      expect(result.current.llm[0]?.isSuccess).toBe(true);
    });

    expect(apiClientMock.get).toHaveBeenCalledWith("/ingest/ing-1/status");
    expect(apiClientMock.get).toHaveBeenCalledWith("/ingest/ing-2/status");
    expect(apiClientMock.get).toHaveBeenCalledWith("/llm/jobs/llm-1/status");
  });

  it("fetches strategies and triggers llm job", async () => {
    apiClientMock.get.mockResolvedValueOnce({ data: [{ id: "strategy-1", name: "manual" }] });
    apiClientMock.post.mockResolvedValueOnce({ data: { job_id: "llm-1", celery_task_id: "cel-1", status: "queued" } });

    const strategiesHook = renderHook(() => useLlmStrategies(), { wrapper: createWrapper() });
    await waitFor(() => expect(strategiesHook.result.current.isSuccess).toBe(true));
    expect(apiClientMock.get).toHaveBeenCalledWith("/llm/strategies");

    const triggerHook = renderHook(() => useTriggerLlmJob(), { wrapper: createWrapper() });
    await act(async () => {
      await triggerHook.result.current.mutateAsync({
        session_id: "sess-1",
        strategy_id: "strategy-1",
      });
    });

    expect(apiClientMock.post).toHaveBeenCalledWith("/llm/jobs/trigger", {
      session_id: "sess-1",
      strategy_id: "strategy-1",
      manual_record_ids: [],
      expect_manual_records: false,
    });
  });
});
