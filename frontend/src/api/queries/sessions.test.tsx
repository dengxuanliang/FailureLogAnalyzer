import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { jest } from "@jest/globals";
import apiClient from "../client";
import { useSessions } from "./sessions";
import type { EvalSession } from "@/types/api";

describe("useSessions", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("fetches sessions with query key ['sessions'] and returns the data", async () => {
    const sessions: EvalSession[] = [
      {
        id: "sess-1",
        model: "gpt-4o",
        model_version: "v1.0",
        benchmark: "mmlu",
        dataset_name: "mmlu-dev",
        total_count: 100,
        error_count: 20,
        accuracy: 0.8,
        tags: ["nightly"],
        created_at: "2026-03-20T00:00:00Z",
      },
    ];

    const getSpy = jest
      .spyOn(apiClient, "get")
      .mockResolvedValueOnce({ data: sessions } as Awaited<ReturnType<typeof apiClient.get>>);

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    const { result } = renderHook(() => useSessions(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(sessions);
    expect(getSpy).toHaveBeenCalledWith("/sessions");
    expect(queryClient.getQueryData(["sessions"])).toEqual(sessions);
  });
});
