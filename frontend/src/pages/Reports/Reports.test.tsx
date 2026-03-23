import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { jest } from "@jest/globals";

const mockUseReportDetail: any = jest.fn();
const mockExportMutate: any = jest.fn();
const mockGenerateMutate: any = jest.fn();

const originalMatchMedia = window.matchMedia;
const originalGetComputedStyle = window.getComputedStyle;
const originalCreateObjectURL = URL.createObjectURL;
const originalRevokeObjectURL = URL.revokeObjectURL;
const originalAnchorClick = HTMLAnchorElement.prototype.click;

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
Object.defineProperty(URL, "createObjectURL", {
  writable: true,
  value: jest.fn(() => "blob://report-file"),
});
Object.defineProperty(URL, "revokeObjectURL", {
  writable: true,
  value: jest.fn(),
});
Object.defineProperty(HTMLAnchorElement.prototype, "click", {
  writable: true,
  value: jest.fn(),
});

jest.unstable_mockModule("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "reports.title": "Report Center",
        "reports.empty": "No reports available",
        "reports.columns.title": "Title",
        "reports.columns.type": "Type",
        "reports.columns.status": "Status",
        "reports.columns.benchmark": "Benchmark",
        "reports.columns.modelVersion": "Model Version",
        "reports.columns.createdAt": "Created At",
        "reports.columns.actions": "Actions",
        "reports.actions.view": "View Report",
        "reports.actions.exportJson": "Export JSON",
        "reports.actions.exportMarkdown": "Export Markdown",
        "reports.actions.generate": "Generate Report",
        "reports.exportSuccess": "Report export started",
        "reports.form.heading": "Generate New Report",
        "reports.form.title": "Report Title",
        "reports.form.titleRequired": "Report title is required",
        "reports.form.benchmark": "Benchmark Filter",
        "reports.form.modelVersion": "Model Version Filter",
        "reports.detail.title": "Report Detail",
        "reports.detail.id": "Report ID",
        "reports.detail.titleLabel": "Title",
        "reports.detail.type": "Type",
        "reports.detail.status": "Status",
        "reports.detail.createdAt": "Created At",
        "reports.detail.updatedAt": "Updated At",
        "reports.detail.content": "Content",
        "common.loading": "Loading...",
        "common.error": "Error",
        "common.retry": "Retry",
      };
      return map[key] ?? key;
    },
  }),
}));

jest.unstable_mockModule("@/api/queries/reports", () => ({
  useReports: () => ({
    data: [
      {
        id: "rep-1",
        title: "Weekly Summary",
        report_type: "summary",
        status: "done",
        benchmark: "mmlu",
        model_version: "v1",
        created_by: "analyst",
        created_at: "2026-03-22T00:00:00Z",
        updated_at: "2026-03-22T01:00:00Z",
      },
    ],
    isLoading: false,
    isError: false,
    refetch: jest.fn(),
  }),
  useReportDetail: mockUseReportDetail,
  useReportExport: () => ({
    mutateAsync: mockExportMutate,
    isPending: false,
  }),
  useGenerateReport: () => ({
    mutateAsync: mockGenerateMutate,
    isPending: false,
  }),
}));

const { default: Reports } = await import("./index");

describe("Reports page", () => {
  afterAll(() => {
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: originalMatchMedia,
    });
    Object.defineProperty(window, "getComputedStyle", {
      writable: true,
      value: originalGetComputedStyle,
    });
    Object.defineProperty(URL, "createObjectURL", {
      writable: true,
      value: originalCreateObjectURL,
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      writable: true,
      value: originalRevokeObjectURL,
    });
    Object.defineProperty(HTMLAnchorElement.prototype, "click", {
      writable: true,
      value: originalAnchorClick,
    });
  });

  beforeEach(() => {
    jest.clearAllMocks();
    mockGenerateMutate.mockResolvedValue({ report_id: "rep-new", status: "pending", message: "queued" });
    mockUseReportDetail.mockReturnValue({
      data: {
        id: "rep-1",
        title: "Weekly Summary",
        report_type: "summary",
        status: "done",
        benchmark: "mmlu",
        model_version: "v1",
        created_by: "analyst",
        created_at: "2026-03-22T00:00:00Z",
        updated_at: "2026-03-22T01:00:00Z",
        session_ids: ["sess-1"],
        time_range_start: null,
        time_range_end: null,
        content: { summary: "ok" },
        error_message: null,
      },
      isLoading: false,
      isError: false,
    });
    mockExportMutate.mockResolvedValue({
      blob: new globalThis.Blob(["{}"], { type: "application/json" }),
      filename: "report-rep-1.json",
    });
  });

  it("generates a new report from the report center form", async () => {
    render(<Reports />);

    await userEvent.type(screen.getByLabelText("Report Title"), "Nightly summary");
    await userEvent.type(screen.getByLabelText("Benchmark Filter"), "mmlu");
    await userEvent.type(screen.getByLabelText("Model Version Filter"), "v1");
    await userEvent.click(screen.getByRole("button", { name: "Generate Report" }));

    await waitFor(() => {
      expect(mockGenerateMutate).toHaveBeenCalledWith({
        title: "Nightly summary",
        report_type: "summary",
        benchmark: "mmlu",
        model_version: "v1",
      });
    });
  });

  it("renders report list and opens report detail", async () => {
    render(<Reports />);

    expect(screen.getByText("Report Center")).toBeInTheDocument();
    expect(screen.getByText("Weekly Summary")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "View Report" }));

    expect(await screen.findByText("Report Detail")).toBeInTheDocument();
    expect(screen.getByText(/"summary": "ok"/)).toBeInTheDocument();
  });

  it("exports report in json and markdown formats", async () => {
    render(<Reports />);

    await userEvent.click(screen.getByRole("button", { name: "Export JSON" }));
    await waitFor(() => {
      expect(mockExportMutate).toHaveBeenCalledWith({
        reportId: "rep-1",
        format: "json",
      });
    });

    await userEvent.click(screen.getByRole("button", { name: "Export Markdown" }));
    await waitFor(() => {
      expect(mockExportMutate).toHaveBeenCalledWith({
        reportId: "rep-1",
        format: "markdown",
      });
    });
  });
});
