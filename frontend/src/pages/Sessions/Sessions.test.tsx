import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { jest } from "@jest/globals";

const mockDeleteMutateAsync: any = jest.fn();
const mockRerunMutateAsync: any = jest.fn();
const mockUseSessionDetail: any = jest.fn();

const originalMatchMedia = window.matchMedia;
const originalGetComputedStyle = window.getComputedStyle;

jest.unstable_mockModule("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "sessions.title": "Sessions Center",
        "sessions.actions.view": "View Detail",
        "sessions.actions.rerun": "Rerun Rules",
        "sessions.actions.delete": "Delete Session",
        "sessions.detail.title": "Session Detail",
        "sessions.detail.updatedAt": "Updated At",
        "sessions.deleteSuccess": "Deleted",
        "common.loading": "Loading",
        "common.retry": "Retry",
        "common.error": "Load Failed",
        "sessions.empty": "No Sessions",
        "sessions.columns.model": "Model",
        "sessions.columns.version": "Version",
        "sessions.columns.benchmark": "Benchmark",
        "sessions.columns.errors": "Errors",
        "sessions.columns.accuracy": "Accuracy",
        "sessions.columns.createdAt": "Created",
        "sessions.columns.tags": "Tags",
        "sessions.columns.actions": "Actions",
        "sessions.detail.id": "ID",
        "sessions.detail.model": "Model",
        "sessions.detail.version": "Version",
        "sessions.detail.benchmark": "Benchmark",
        "sessions.detail.dataset": "Dataset",
        "sessions.detail.total": "Total",
        "sessions.detail.errors": "Errors",
        "sessions.detail.accuracy": "Accuracy",
        "sessions.detail.createdAt": "Created At",
      };
      return map[key] ?? key;
    },
  }),
}));

jest.unstable_mockModule("@/api/queries/sessions", () => ({
  useSessions: () => ({
    data: [
      {
        id: "sess-1",
        model: "gpt-4o",
        model_version: "v1",
        benchmark: "mmlu",
        dataset_name: "mmlu-dev",
        total_count: 100,
        error_count: 15,
        accuracy: 0.85,
        tags: ["nightly"],
        created_at: "2026-03-23T00:00:00Z",
      },
    ],
    isLoading: false,
    isError: false,
    refetch: jest.fn(),
  }),
  useSessionDetail: mockUseSessionDetail,
  useDeleteSession: () => ({
    mutateAsync: mockDeleteMutateAsync,
    isPending: false,
  }),
  useRerunSessionRules: () => ({
    mutateAsync: mockRerunMutateAsync,
    isPending: false,
  }),
}));

const { default: Sessions } = await import("./index");

describe("Sessions page", () => {
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
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: originalMatchMedia,
    });
    Object.defineProperty(window, "getComputedStyle", {
      writable: true,
      value: originalGetComputedStyle,
    });
  });

  beforeEach(() => {
    jest.clearAllMocks();
    mockUseSessionDetail.mockReturnValue({
      data: {
        id: "sess-1",
        model: "gpt-4o",
        model_version: "v1",
        benchmark: "mmlu",
        dataset_name: "mmlu-dev",
        total_count: 100,
        error_count: 15,
        accuracy: 0.85,
        tags: ["nightly"],
        created_at: "2026-03-23T00:00:00Z",
        updated_at: "2026-03-23T01:00:00Z",
      },
      isLoading: false,
      isError: false,
    });
  });

  it("renders session list and opens detail pane", async () => {
    render(<Sessions />);

    expect(screen.getByText("Sessions Center")).toBeInTheDocument();
    expect(screen.getByText("gpt-4o")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "View Detail" }));

    expect(await screen.findByText("Session Detail")).toBeInTheDocument();
    expect(screen.getByText("Updated At")).toBeInTheDocument();
  });

  it("triggers rerun-rules and delete actions", async () => {
    mockRerunMutateAsync.mockResolvedValue({
      session_id: "sess-1",
      job_id: "job-123",
      message: "queued",
    });
    mockDeleteMutateAsync.mockResolvedValue({
      session_id: "sess-1",
      deleted: true,
    });

    render(<Sessions />);

    await userEvent.click(screen.getByRole("button", { name: "Rerun Rules" }));
    await waitFor(() => {
      expect(mockRerunMutateAsync).toHaveBeenCalledWith({ sessionId: "sess-1" });
    });

    await userEvent.click(screen.getByRole("button", { name: "Delete Session" }));
    await waitFor(() => {
      expect(mockDeleteMutateAsync).toHaveBeenCalledWith("sess-1");
    });
  });
});
