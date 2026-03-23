import { jest } from "@jest/globals";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";

const mockUseReportDetail: any = jest.fn();
const mockUseReportExport: any = jest.fn();
const mockNavigate = jest.fn();
const originalMatchMedia = window.matchMedia;
const originalGetComputedStyle = window.getComputedStyle;

jest.unstable_mockModule("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "reports.detail.title": "报告详情",
        "reports.actions.exportJson": "导出JSON",
        "reports.actions.exportMarkdown": "导出Markdown",
        "reports.actions.back": "返回列表",
        "common.retry": "重试",
        "common.error": "加载失败",
      };
      return map[key] ?? key;
    },
  }),
}));

jest.unstable_mockModule("@/api/queries/reports", () => ({
  useReportDetail: mockUseReportDetail,
  useReportExport: mockUseReportExport,
}));

jest.unstable_mockModule("react-router-dom", () => ({
  useParams: () => ({ reportId: "r2" }),
  useNavigate: () => mockNavigate,
}));

const { default: ReportDetail } = await import("./ReportDetail");

describe("Report detail page", () => {
  beforeAll(() => {
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: ((query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: jest.fn(),
        removeListener: jest.fn(),
        addEventListener: jest.fn(),
        removeEventListener: jest.fn(),
        dispatchEvent: jest.fn(() => false),
      })) as typeof window.matchMedia,
    });
    Object.defineProperty(window, "getComputedStyle", {
      writable: true,
      value: (() => ({ getPropertyValue: () => "" })) as unknown as typeof window.getComputedStyle,
    });
  });

  afterAll(() => {
    Object.defineProperty(window, "matchMedia", { writable: true, value: originalMatchMedia });
    Object.defineProperty(window, "getComputedStyle", { writable: true, value: originalGetComputedStyle });
  });

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("renders detail and exports", async () => {
    const exportMutate: any = jest.fn();
    exportMutate.mockResolvedValue({ blob: new Blob(), filename: "report-r2.json" });

    mockUseReportDetail.mockReturnValue({
      data: {
        id: "r2",
        title: "Detail",
        report_type: "summary",
        status: "done",
        benchmark: "mmlu",
        model_version: "v1",
        created_by: "analyst",
        created_at: "2026-03-21T00:00:00Z",
        updated_at: "2026-03-21T00:10:00Z",
        session_ids: ["sess-1"],
        time_range_start: null,
        time_range_end: null,
        content: { hello: "world" },
        error_message: null,
      },
      isLoading: false,
      isError: false,
      refetch: jest.fn(),
    });
    mockUseReportExport.mockReturnValue({ mutateAsync: exportMutate, isPending: false });

    render(<ReportDetail />);

    expect(screen.getByText("报告详情")).toBeInTheDocument();
    expect(screen.getByText("Detail")).toBeInTheDocument();
    expect(screen.getByText(/hello/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "导出JSON" }));
    await waitFor(() => expect(exportMutate).toHaveBeenCalledWith({ reportId: "r2", format: "json" }));

    fireEvent.click(screen.getByRole("button", { name: "导出Markdown" }));
    await waitFor(() => expect(exportMutate).toHaveBeenCalledWith({ reportId: "r2", format: "markdown" }));

    fireEvent.click(screen.getByRole("button", { name: "返回列表" }));
    expect(mockNavigate).toHaveBeenCalledWith("/reports");
  });
});
