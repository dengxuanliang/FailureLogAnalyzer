import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { jest } from "@jest/globals";
import apiClient from "../client";
import { FilterProvider } from "@/contexts/FilterContext";
import {
  useAnalysisSummary,
  useErrorDistribution,
  useErrorRecords,
  useRecordDetail,
} from "./analysis";

const createWrapper = (entry = "/") => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return ({ children }: { children: ReactNode }) => (
    <MemoryRouter
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      initialEntries={[entry]}
    >
      <QueryClientProvider client={queryClient}>
        <FilterProvider>{children}</FilterProvider>
      </QueryClientProvider>
    </MemoryRouter>
  );
};

describe("analysis query hooks", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("fetches the analysis summary with active global filters", async () => {
    const summary = {
      total_sessions: 5,
      total_records: 1000,
      total_errors: 300,
      accuracy: 0.7,
      llm_analysed_count: 150,
      llm_total_cost: 1.23,
    };

    const getSpy = jest
      .spyOn(apiClient, "get")
      .mockResolvedValueOnce({ data: summary } as Awaited<ReturnType<typeof apiClient.get>>);

    const { result } = renderHook(() => useAnalysisSummary(), {
      wrapper: createWrapper(
        "/?benchmark=mmlu&model_version=v1.0&time_range_start=2026-01-01&time_range_end=2026-01-31",
      ),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(summary);
    expect(getSpy).toHaveBeenCalledWith("/analysis/summary", {
      params: {
        benchmark: "mmlu",
        model_version: "v1.0",
        time_range_start: "2026-01-01",
        time_range_end: "2026-01-31",
      },
    });
  });

  it("fetches error distribution with error_type drill-down and filters", async () => {
    const distribution = [
      { label: "推理性错误", count: 10, percentage: 50 },
      { label: "格式与规范错误", count: 10, percentage: 50 },
    ];

    const getSpy = jest
      .spyOn(apiClient, "get")
      .mockResolvedValueOnce({ data: distribution } as Awaited<ReturnType<typeof apiClient.get>>);

    const { result } = renderHook(
      () => useErrorDistribution("error_type", "推理性错误"),
      {
        wrapper: createWrapper("/?benchmark=ceval&model_version=v2.0"),
      },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(distribution);
    expect(getSpy).toHaveBeenCalledWith("/analysis/error-distribution", {
      params: {
        group_by: "error_type",
        error_type: "推理性错误",
        benchmark: "ceval",
        model_version: "v2.0",
      },
    });
  });

  it("fetches paginated error records", async () => {
    const records = {
      items: [
        {
          id: "rec-1",
          session_id: "sess-1",
          benchmark: "mmlu",
          task_category: "math",
          question_id: "q1",
          question: "What is 2+2?",
          is_correct: false,
          score: 0,
          error_tags: ["推理性错误.数学/计算错误"],
          has_llm_analysis: true,
        },
      ],
      total: 1,
      page: 1,
      size: 20,
    };

    const getSpy = jest
      .spyOn(apiClient, "get")
      .mockResolvedValueOnce({ data: records } as Awaited<ReturnType<typeof apiClient.get>>);

    const { result } = renderHook(
      () => useErrorRecords({ page: 1, size: 20, errorType: "推理性错误" }),
      {
        wrapper: createWrapper("/?benchmark=mmlu&model_version=v1.0"),
      },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(records);
    expect(getSpy).toHaveBeenCalledWith("/analysis/records", {
      params: {
        page: 1,
        size: 20,
        error_type: "推理性错误",
        benchmark: "mmlu",
        model_version: "v1.0",
      },
    });
  });

  it("fetches record detail by id", async () => {
    const detail = {
      record: { id: "rec-1", question: "What is 2+2?" },
      analysis_results: [],
      error_tags: [],
    };

    const getSpy = jest
      .spyOn(apiClient, "get")
      .mockResolvedValueOnce({ data: detail } as Awaited<ReturnType<typeof apiClient.get>>);

    const { result } = renderHook(() => useRecordDetail("rec-1"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(detail);
    expect(getSpy).toHaveBeenCalledWith("/analysis/records/rec-1/detail");
  });

  it("does not fetch record detail when id is null", async () => {
    const getSpy = jest.spyOn(apiClient, "get");

    const { result } = renderHook(() => useRecordDetail(null), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.fetchStatus).toBe("idle"));
    expect(getSpy).not.toHaveBeenCalled();
  });
});
