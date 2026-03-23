import { act, renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { jest } from "@jest/globals";
import apiClient from "../client";
import { useDeleteSession, useRerunSessionRules, useSessionDetail, useSessions } from "./sessions";
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
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
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

  it("fetches session detail when session id is provided", async () => {
    const sessionDetail = {
      id: "sess-2",
      model: "gpt-4o",
      model_version: "v1.1",
      benchmark: "mmlu",
      dataset_name: null,
      total_count: 50,
      error_count: 5,
      accuracy: 0.9,
      tags: [],
      created_at: "2026-03-20T00:00:00Z",
      updated_at: "2026-03-21T00:00:00Z",
    };

    const getSpy = jest
      .spyOn(apiClient, "get")
      .mockResolvedValueOnce({ data: sessionDetail } as Awaited<ReturnType<typeof apiClient.get>>);

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    const { result } = renderHook(() => useSessionDetail("sess-2"), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(sessionDetail);
    expect(getSpy).toHaveBeenCalledWith("/sessions/sess-2");
  });

  it("deletes sessions and reruns rules via mutations", async () => {
    const deleteSpy = jest
      .spyOn(apiClient, "delete")
      .mockResolvedValueOnce({ data: { session_id: "sess-3", deleted: true } } as Awaited<
        ReturnType<typeof apiClient.delete>
      >);
    const postSpy = jest
      .spyOn(apiClient, "post")
      .mockResolvedValueOnce({ data: { session_id: "sess-3", job_id: "job-1", message: "queued" } } as Awaited<
        ReturnType<typeof apiClient.post>
      >);

    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    });
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    const deleteHook = renderHook(() => useDeleteSession(), { wrapper });
    const rerunHook = renderHook(() => useRerunSessionRules(), { wrapper });

    await act(async () => {
      await rerunHook.result.current.mutateAsync({ sessionId: "sess-3" });
      await deleteHook.result.current.mutateAsync("sess-3");
    });

    expect(postSpy).toHaveBeenCalledWith("/sessions/sess-3/actions/rerun-rules", { rule_ids: null });
    expect(deleteSpy).toHaveBeenCalledWith("/sessions/sess-3");
  });
});
