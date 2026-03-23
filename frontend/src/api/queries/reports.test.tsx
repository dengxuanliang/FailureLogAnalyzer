import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { jest } from "@jest/globals";
import type { ReactNode } from "react";

const apiClientMock: any = {
  get: jest.fn(),
};

await jest.unstable_mockModule("../client", () => ({
  __esModule: true,
  default: apiClientMock,
}));

const { useReportDetail, useReportExport, useReports } = await import("./reports");

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

describe("report query hooks", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("fetches report list", async () => {
    apiClientMock.get.mockImplementationOnce(async () => ({
      data: [{ id: "r1", title: "Summary", report_type: "summary" }],
    }));

    const { result } = renderHook(() => useReports(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual([{ id: "r1", title: "Summary", report_type: "summary" }]);
    expect(apiClientMock.get).toHaveBeenCalledWith("/reports");
  });

  it("fetches report detail by id", async () => {
    apiClientMock.get.mockImplementationOnce(async () => ({
      data: { id: "r2", title: "Detail", report_type: "summary" },
    }));

    const { result } = renderHook(() => useReportDetail("r2"), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual({ id: "r2", title: "Detail", report_type: "summary" });
    expect(apiClientMock.get).toHaveBeenCalledWith("/reports/r2");
  });

  it("exports report with requested format", async () => {
    apiClientMock.get.mockImplementationOnce(async () => ({
      data: new globalThis.Blob(["hello"], { type: "application/json" }),
      headers: { "content-disposition": "attachment; filename=report-r3.json" },
    }));

    const { result } = renderHook(() => useReportExport(), { wrapper: createWrapper() });

    await act(async () => {
      await result.current.mutateAsync({ reportId: "r3", format: "json" });
    });

    expect(apiClientMock.get).toHaveBeenCalledWith("/reports/r3/export", {
      params: { format: "json" },
      responseType: "blob",
    });
  });
});
