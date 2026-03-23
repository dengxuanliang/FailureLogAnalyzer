import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { jest } from "@jest/globals";
import "@/i18n";

const mockUploadMutateAsync: any = jest.fn();
const mockTriggerMutateAsync: any = jest.fn();
const mockUseIngestJobStatusQueries: any = jest.fn();
const mockUseLlmJobStatusQueries: any = jest.fn();
const originalMatchMedia = window.matchMedia;
const originalGetComputedStyle = window.getComputedStyle;

jest.unstable_mockModule("@/api/queries/operations", () => ({
  useIngestUpload: () => ({
    mutateAsync: mockUploadMutateAsync,
    isPending: false,
  }),
  useLlmStrategies: () => ({
    data: [
      {
        id: "strategy-1",
        name: "Manual Strategy",
        strategy_type: "manual",
        config: {},
        llm_provider: "openai",
        llm_model: "gpt-4o",
        prompt_template_id: null,
        max_concurrent: 2,
        daily_budget: 5,
        is_active: true,
        created_by: "tester",
        created_at: "2026-03-23T00:00:00Z",
        updated_at: "2026-03-23T00:00:00Z",
      },
    ],
    isLoading: false,
  }),
  useTriggerLlmJob: () => ({
    mutateAsync: mockTriggerMutateAsync,
    isPending: false,
  }),
  useIngestJobStatusQueries: mockUseIngestJobStatusQueries,
  useLlmJobStatusQueries: mockUseLlmJobStatusQueries,
}));

const { default: Operations } = await import("./index");

describe("Operations page", () => {
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
      value: (() => ({
        getPropertyValue: () => "",
      })) as unknown as typeof window.getComputedStyle,
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

    mockUploadMutateAsync.mockResolvedValue({
      job_id: "ingest-1",
      session_id: "session-1",
      message: "Ingestion job queued",
    });

    mockTriggerMutateAsync.mockResolvedValue({
      job_id: "llm-1",
      celery_task_id: "celery-1",
      status: "queued",
    });

    mockUseIngestJobStatusQueries.mockImplementation((jobIds: string[]) =>
      jobIds.map((jobId) => ({
        data: {
          job_id: jobId,
          session_id: "session-1",
          file_path: "/tmp/upload.jsonl",
          status: "running",
          processed: 2,
          total: 10,
          total_written: 2,
          total_skipped: 0,
          reason: "",
          created_at: 1,
        },
        isLoading: false,
        isError: false,
      })),
    );

    mockUseLlmJobStatusQueries.mockImplementation((jobIds: string[]) =>
      jobIds.map((jobId) => ({
        data: {
          job_id: jobId,
          session_id: "session-1",
          strategy_id: "strategy-1",
          status: "queued",
          processed: 0,
          total: null,
          succeeded: 0,
          failed: 0,
          total_cost: 0,
          reason: "",
          stop_reason: null,
          created_at: 1,
          updated_at: 1,
        },
        isLoading: false,
        isError: false,
      })),
    );
  });

  it("renders upload and job monitoring sections", () => {
    render(<Operations />);

    expect(screen.getByText("Operations Center")).toBeInTheDocument();
    expect(screen.getByText("Upload JSONL for Ingestion")).toBeInTheDocument();
    expect(screen.getByText("Monitor Ingest + LLM Jobs")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Upload JSONL" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Trigger LLM Job" })).toBeInTheDocument();
  });

  it("uploads file and starts tracking ingest job status", async () => {
    render(<Operations />);

    await userEvent.type(screen.getByLabelText("Benchmark"), "mmlu");
    await userEvent.type(screen.getByLabelText("Model"), "gpt-4o");
    await userEvent.type(screen.getByLabelText("Model Version"), "v1");

    const file = new window.File(['{"id":1}\n'], "eval.jsonl", { type: "application/json" });
    await userEvent.upload(screen.getByLabelText("JSONL File"), file);

    await userEvent.click(screen.getByRole("button", { name: "Upload JSONL" }));

    await waitFor(() => {
      expect(mockUploadMutateAsync).toHaveBeenCalledWith({
        file,
        benchmark: "mmlu",
        model: "gpt-4o",
        model_version: "v1",
      });
    });

    expect(await screen.findByText("ingest-1")).toBeInTheDocument();
    expect(screen.getByText("running")).toBeInTheDocument();
  });

  it("triggers llm job with latest session and tracks llm status", async () => {
    render(<Operations />);

    await userEvent.type(screen.getByLabelText("Benchmark"), "mmlu");
    await userEvent.type(screen.getByLabelText("Model"), "gpt-4o");
    await userEvent.type(screen.getByLabelText("Model Version"), "v2");

    const file = new window.File(['{"id":2}\n'], "eval2.jsonl", { type: "application/json" });
    await userEvent.upload(screen.getByLabelText("JSONL File"), file);
    await userEvent.click(screen.getByRole("button", { name: "Upload JSONL" }));

    await waitFor(() => expect(mockUploadMutateAsync).toHaveBeenCalledTimes(1));

    await userEvent.click(screen.getByRole("button", { name: "Trigger LLM Job" }));

    await waitFor(() => {
      expect(mockTriggerMutateAsync).toHaveBeenCalledWith({
        session_id: "session-1",
        strategy_id: "strategy-1",
      });
    });

    expect(await screen.findByText("llm-1")).toBeInTheDocument();
    expect(screen.getByDisplayValue("session-1")).toBeInTheDocument();
  });
});
