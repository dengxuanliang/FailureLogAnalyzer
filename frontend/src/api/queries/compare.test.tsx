import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import { jest } from "@jest/globals";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import apiClient from "@/api/client";
import { FilterProvider } from "@/contexts/FilterContext";
import type { RadarData, VersionComparison, VersionDiff } from "@/types/api";
import { useRadarData, useVersionComparison, useVersionDiff } from "./compare";

const createWrapper = (initialEntry = "/") => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return ({ children }: { children: ReactNode }) => (
    <MemoryRouter
      initialEntries={[initialEntry]}
      future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
    >
      <QueryClientProvider client={queryClient}>
        <FilterProvider>{children}</FilterProvider>
      </QueryClientProvider>
    </MemoryRouter>
  );
};

describe("compare query hooks", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("useVersionComparison fetches comparison data and includes benchmark when present", async () => {
    const backendPayload = {
      version_a: "v1.0",
      version_b: "v2.0",
      benchmark: "mmlu",
      sessions_a: 10,
      sessions_b: 10,
      accuracy_a: 0.7,
      accuracy_b: 0.8,
      error_rate_a: 0.3,
      error_rate_b: 0.2,
    };

    const getSpy = jest
      .spyOn(apiClient, "get")
      .mockResolvedValueOnce({ data: backendPayload } as Awaited<ReturnType<typeof apiClient.get>>);

    const { result } = renderHook(() => useVersionComparison("v1.0", "v2.0"), {
      wrapper: createWrapper("/?benchmark=mmlu"),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const expected: VersionComparison = {
      version_a: "v1.0",
      version_b: "v2.0",
      benchmark: "mmlu",
      metrics_a: { total: 10, errors: 3, accuracy: 0.7, error_type_distribution: {} },
      metrics_b: { total: 10, errors: 2, accuracy: 0.8, error_type_distribution: {} },
    };

    expect(result.current.data).toEqual(expected);
    expect(getSpy).toHaveBeenCalledWith("/compare/versions", {
      params: {
        version_a: "v1.0",
        version_b: "v2.0",
        benchmark: "mmlu",
      },
    });
  });

  it("useVersionDiff fetches diff data without benchmark when filter is absent", async () => {
    const backendPayload = {
      version_a: "v1.0",
      version_b: "v2.0",
      regressed: [
        { question_id: "q1", benchmark: "mmlu", category: "math" },
      ],
      improved: [],
      new_errors: [{ question_id: "q2", benchmark: "mmlu", new_tag: "格式与规范错误" }],
      fixed_errors: [{ question_id: "q3", benchmark: "mmlu", old_tag: "推理错误" }],
    };

    const getSpy = jest
      .spyOn(apiClient, "get")
      .mockResolvedValueOnce({ data: backendPayload } as Awaited<ReturnType<typeof apiClient.get>>);

    const { result } = renderHook(() => useVersionDiff("v1.0", "v2.0"), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    const expected: VersionDiff = {
      regressed: [{ question_id: "q1", benchmark: "mmlu", task_category: "math", question: "" }],
      improved: [],
      new_errors: ["格式与规范错误"],
      resolved_errors: ["推理错误"],
    };

    expect(result.current.data).toEqual(expected);
    expect(getSpy).toHaveBeenCalledWith("/compare/diff", {
      params: {
        version_a: "v1.0",
        version_b: "v2.0",
      },
    });
  });

  it("useRadarData fetches radar data and includes benchmark when present", async () => {
    const mockData: RadarData = {
      dimensions: ["math", "logic", "reading"],
      scores_a: [0.8, 0.7, 0.9],
      scores_b: [0.85, 0.75, 0.88],
    };

    const getSpy = jest
      .spyOn(apiClient, "get")
      .mockResolvedValueOnce({ data: mockData } as Awaited<ReturnType<typeof apiClient.get>>);

    const { result } = renderHook(() => useRadarData("v1.0", "v2.0"), {
      wrapper: createWrapper("/?benchmark=ceval"),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(mockData);
    expect(getSpy).toHaveBeenCalledWith("/compare/radar", {
      params: {
        version_a: "v1.0",
        version_b: "v2.0",
        benchmark: "ceval",
      },
    });
  });

  it("useVersionComparison does not fetch when versionA is missing", async () => {
    const getSpy = jest.spyOn(apiClient, "get");

    const { result } = renderHook(() => useVersionComparison(null, "v2.0"), {
      wrapper: createWrapper("/?benchmark=mmlu"),
    });

    await waitFor(() => expect(result.current.fetchStatus).toBe("idle"));
    expect(result.current.isFetching).toBe(false);
    expect(getSpy).not.toHaveBeenCalled();
  });

  it("useVersionDiff does not fetch when versionB is missing", async () => {
    const getSpy = jest.spyOn(apiClient, "get");

    const { result } = renderHook(() => useVersionDiff("v1.0", null), {
      wrapper: createWrapper("/?benchmark=mmlu"),
    });

    await waitFor(() => expect(result.current.fetchStatus).toBe("idle"));
    expect(result.current.isFetching).toBe(false);
    expect(getSpy).not.toHaveBeenCalled();
  });

  it("useRadarData does not fetch when versions are missing", async () => {
    const getSpy = jest.spyOn(apiClient, "get");

    const { result } = renderHook(() => useRadarData(null, null), {
      wrapper: createWrapper("/?benchmark=mmlu"),
    });

    await waitFor(() => expect(result.current.fetchStatus).toBe("idle"));
    expect(result.current.isFetching).toBe(false);
    expect(getSpy).not.toHaveBeenCalled();
  });
});
