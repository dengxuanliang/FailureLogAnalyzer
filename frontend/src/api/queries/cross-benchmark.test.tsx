import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import type { ReactNode } from "react";
import { jest } from "@jest/globals";
import apiClient from "@/api/client";
import { FilterContext, type FilterContextValue } from "@/contexts/FilterContext";
import { useCrossBenchmarkMatrix, useWeaknessReport } from "./cross-benchmark";

function createWrapper(filters: Partial<FilterContextValue> = {}) {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  const filterValue: FilterContextValue = {
    benchmark: null,
    model_version: null,
    time_range_start: null,
    time_range_end: null,
    setFilter: jest.fn(),
    resetFilters: jest.fn(),
    ...filters,
  };

  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <FilterContext.Provider value={filterValue}>{children}</FilterContext.Provider>
    </QueryClientProvider>
  );

  return { queryClient, wrapper };
}

describe("cross-benchmark query hooks", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("fetches the matrix with only relevant non-null global filters", async () => {
    const matrix = {
      model_versions: ["v1.0", "v2.0"],
      benchmarks: ["mmlu", "gsm8k"],
      cells: [
        {
          model_version: "v1.0",
          benchmark: "mmlu",
          error_rate: 0.3,
          error_count: 30,
          total_count: 100,
        },
      ],
    };

    const getSpy = jest
      .spyOn(apiClient, "get")
      .mockResolvedValueOnce({ data: matrix } as Awaited<ReturnType<typeof apiClient.get>>);

    const { queryClient, wrapper } = createWrapper({
      benchmark: "mmlu",
      model_version: null,
      time_range_start: "2026-03-01",
    });

    const { result } = renderHook(() => useCrossBenchmarkMatrix(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(matrix);
    expect(getSpy).toHaveBeenCalledWith("/cross-benchmark/matrix", {
      params: { benchmark: "mmlu" },
    });
    expect(queryClient.getQueryData(["crossBenchmarkMatrix", "mmlu", null])).toEqual(matrix);
  });

  it("fetches the weakness report with benchmark and model_version in params and query key", async () => {
    const report = {
      generated_at: "2026-03-21T08:00:00Z",
      summary: "Shared reasoning weakness.",
      common_patterns: [
        {
          error_type: "reasoning.math",
          affected_benchmarks: ["mmlu", "gsm8k"],
          avg_error_rate: 0.42,
          record_count: 120,
        },
      ],
    };

    const getSpy = jest
      .spyOn(apiClient, "get")
      .mockResolvedValueOnce({ data: report } as Awaited<ReturnType<typeof apiClient.get>>);

    const { queryClient, wrapper } = createWrapper({
      benchmark: "gsm8k",
      model_version: "v2.0",
    });

    const { result } = renderHook(() => useWeaknessReport(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(report);
    expect(getSpy).toHaveBeenCalledWith("/cross-benchmark/weakness", {
      params: { benchmark: "gsm8k", model_version: "v2.0" },
    });
    expect(queryClient.getQueryData(["weaknessReport", "gsm8k", "v2.0"])).toEqual(report);
  });

  it("returns null report data when backend has no report yet", async () => {
    jest
      .spyOn(apiClient, "get")
      .mockResolvedValueOnce({ data: null } as Awaited<ReturnType<typeof apiClient.get>>);

    const { wrapper } = createWrapper();
    const { result } = renderHook(() => useWeaknessReport(), { wrapper });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toBeNull();
  });
});
