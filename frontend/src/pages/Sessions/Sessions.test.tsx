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
    t: (key: string, options?: Record<string, string | number>) => {
      const map: Record<string, string> = {
        "sessions.title": "Sessions Center",
        "sessions.actions.view": "View Detail",
        "sessions.actions.rerun": "Rerun Rules",
        "sessions.actions.delete": "Delete Session",
        "sessions.actions.deleteSelected": "Delete Selected ({{count}})",
        "sessions.actions.clearSelection": "Clear Selection",
        "sessions.detail.title": "Session Detail",
        "sessions.detail.updatedAt": "Updated At",
        "sessions.deleteSuccess": "Deleted",
        "sessions.deleteSelectedSuccess": "Deleted {{count}} sessions",
        "sessions.deleteSelectedConfirm": "Delete {{count}} selected sessions?",
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
      return (map[key] ?? key).replace(/\{\{(\w+)\}\}/g, (_match, token) => String(options?.[token] ?? ""));
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
      {
        id: "sess-2",
        model: "gpt-4.1",
        model_version: "v2",
        benchmark: "codeforces",
        dataset_name: "cf",
        total_count: 80,
        error_count: 10,
        accuracy: 0.875,
        tags: ["weekly"],
        created_at: "2026-03-24T00:00:00Z",
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
  const originalConfirm = window.confirm;

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
    window.confirm = originalConfirm;
  });

  beforeEach(() => {
    jest.clearAllMocks();
    window.confirm = jest.fn(() => true);
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

    await userEvent.click(screen.getAllByRole("button", { name: "View Detail" })[0]);

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

    await userEvent.click(screen.getAllByRole("button", { name: "Rerun Rules" })[0]);
    await waitFor(() => {
      expect(mockRerunMutateAsync).toHaveBeenCalledWith({ sessionId: "sess-1" });
    });

    await userEvent.click(screen.getAllByRole("button", { name: "Delete Session" })[0]);
    await waitFor(() => {
      expect(mockDeleteMutateAsync).toHaveBeenCalledWith("sess-1");
    });
  });

  it("supports selecting multiple sessions and deleting them in batch", async () => {
    mockDeleteMutateAsync.mockResolvedValue({
      session_id: "sess-1",
      deleted: true,
    });

    render(<Sessions />);

    const checkboxes = screen.getAllByRole("checkbox");
    await userEvent.click(checkboxes[1]);
    await userEvent.click(checkboxes[2]);

    await userEvent.click(screen.getByRole("button", { name: "Delete Selected (2)" }));

    await waitFor(() => {
      expect(window.confirm).toHaveBeenCalled();
      expect(mockDeleteMutateAsync).toHaveBeenNthCalledWith(1, "sess-1");
      expect(mockDeleteMutateAsync).toHaveBeenNthCalledWith(2, "sess-2");
    });
  });
});
