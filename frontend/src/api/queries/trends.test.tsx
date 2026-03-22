import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { renderHook, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";
import { jest } from "@jest/globals";
import apiClient from "../client";
import { FilterProvider } from "@/contexts/FilterContext";
import { useTrends } from "./trends";

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

describe("useTrends", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("fetches trend data using benchmark and model version filters", async () => {
    const trendData = {
      data_points: [
        { period: "v1.0", error_rate: 0.35, total: 500, errors: 175 },
        { period: "v2.0", error_rate: 0.3, total: 500, errors: 150 },
      ],
    };

    const getSpy = jest
      .spyOn(apiClient, "get")
      .mockResolvedValueOnce({ data: trendData } as Awaited<ReturnType<typeof apiClient.get>>);

    const { result } = renderHook(() => useTrends(), {
      wrapper: createWrapper("/?benchmark=mmlu&model_version=v2.0"),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual(trendData);
    expect(getSpy).toHaveBeenCalledWith("/trends", {
      params: {
        benchmark: "mmlu",
        model_version: "v2.0",
      },
    });
  });
});
