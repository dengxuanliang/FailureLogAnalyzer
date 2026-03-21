import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { type ReactNode } from "react";
import { jest } from "@jest/globals";
import "@/i18n";

const mockUseAnalysisSummary = jest.fn();
const mockUseErrorDistribution = jest.fn();
const mockUseTrends = jest.fn();
const mockSend = jest.fn();
const mockSetIsOpen = jest.fn();
const originalMatchMedia = window.matchMedia;

jest.unstable_mockModule("echarts-for-react", () => ({
  default: () => <div data-testid="echarts-mock" />,
}));

jest.unstable_mockModule("@/api/queries/analysis", () => ({
  useAnalysisSummary: mockUseAnalysisSummary,
  useErrorDistribution: mockUseErrorDistribution,
}));

jest.unstable_mockModule("@/api/queries/trends", () => ({
  useTrends: mockUseTrends,
}));

jest.unstable_mockModule("@/hooks/useAgentChat", () => ({
  useAgentChat: () => ({
    send: mockSend,
    setIsOpen: mockSetIsOpen,
  }),
}));

jest.unstable_mockModule("@/hooks/useGlobalFilters", () => ({
  useGlobalFilters: () => ({
    benchmark: "mmlu",
    model_version: "v2.0",
    time_range_start: null,
    time_range_end: null,
  }),
}));

const { default: Overview } = await import("./index");

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        {children}
      </MemoryRouter>
    </QueryClientProvider>
  );
};

describe("Overview page", () => {
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
  });

  afterAll(() => {
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: originalMatchMedia,
    });
  });

  beforeEach(() => {
    jest.clearAllMocks();

    mockUseAnalysisSummary.mockReturnValue({
      data: {
        total_sessions: 5,
        total_records: 1000,
        total_errors: 300,
        accuracy: 0.7,
        llm_analysed_count: 150,
        llm_total_cost: 1.23,
      },
      isLoading: false,
      isError: false,
      refetch: jest.fn(),
    });

    mockUseErrorDistribution.mockReturnValue({
      data: [
        { label: "格式与规范错误", count: 50, percentage: 16.7 },
        { label: "推理性错误", count: 100, percentage: 33.3 },
      ],
      isLoading: false,
      isError: false,
      refetch: jest.fn(),
    });

    mockUseTrends.mockReturnValue({
      data: {
        data_points: [
          { period: "v1.0", error_rate: 0.35, total: 500, errors: 175 },
          { period: "v2.0", error_rate: 0.3, total: 500, errors: 150 },
        ],
      },
      isLoading: false,
      isError: false,
      refetch: jest.fn(),
    });
  });

  it("renders five KPI stat cards", () => {
    render(<Overview />, { wrapper: createWrapper() });

    expect(screen.getByText("Total Sessions")).toBeInTheDocument();
    expect(screen.getByText("Total Errors")).toBeInTheDocument();
    expect(screen.getByText("Accuracy")).toBeInTheDocument();
    expect(screen.getByText("LLM Analysed")).toBeInTheDocument();
    expect(screen.getByText("LLM Cost")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Analyze" })).toBeInTheDocument();
  });

  it("renders stat values and chart titles", () => {
    render(<Overview />, { wrapper: createWrapper() });

    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByText("300")).toBeInTheDocument();
    expect(screen.getByText("Error Rate Trend")).toBeInTheDocument();
    expect(screen.getByText("L1 Error Type Distribution")).toBeInTheDocument();
  });

  it("opens agent chat and sends analyze instruction", async () => {
    render(<Overview />, { wrapper: createWrapper() });

    await userEvent.click(screen.getByRole("button", { name: "Analyze" }));

    expect(mockSetIsOpen).toHaveBeenCalledWith(true);
    expect(mockSend).toHaveBeenCalledWith(
      "Analyze current evaluation errors. benchmark: mmlu, model version: v2.0",
    );
  });
});
