import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { jest } from "@jest/globals";
import { fireEvent, render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { MemoryRouter } from "react-router-dom";

const mockUseCrossBenchmarkMatrix = jest.fn();
const mockUseWeaknessReport = jest.fn();
const mockSetFilter = jest.fn();
const originalGetComputedStyle = window.getComputedStyle;

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
    value: jest.fn().mockImplementation(() => ({
      getPropertyValue: () => "",
      overflow: "auto",
      overflowX: "auto",
      overflowY: "auto",
      borderLeftWidth: "0",
      borderTopWidth: "0",
      borderRightWidth: "0",
      borderBottomWidth: "0",
      scrollMarginTop: "0",
      scrollMarginRight: "0",
      scrollMarginBottom: "0",
      scrollMarginLeft: "0",
    })),
  });
});

afterAll(() => {
  Object.defineProperty(window, "getComputedStyle", {
    writable: true,
    value: originalGetComputedStyle,
  });
});

await jest.unstable_mockModule("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) =>
      ({
        "cross.title": "Benchmark 横向分析",
        "cross.heatmap.title": "模型版本 × Benchmark 错误率热力图",
        "cross.heatmap.xAxisLabel": "Benchmark",
        "cross.heatmap.yAxisLabel": "模型版本",
        "cross.heatmap.tooltip": "错误率",
        "cross.heatmap.noData": "暂无跨 Benchmark 数据",
        "cross.weakness.title": "系统性弱点识别报告",
        "cross.weakness.generatedAt": "生成时间",
        "cross.weakness.noReport": "暂无分析报告，请先完成多个 Benchmark 的评测分析",
        "cross.patterns.title": "跨 Benchmark 共性错误模式",
        "cross.patterns.columns.errorType": "错误类型",
        "cross.patterns.columns.benchmarks": "涉及 Benchmark",
        "cross.patterns.columns.avgErrorRate": "平均错误率",
        "cross.patterns.columns.recordCount": "涉及题数",
        "cross.patterns.noData": "暂无共性错误模式数据",
        "common.error": "加载失败",
        "common.retry": "重试",
      })[key] ?? key,
  }),
}));

await jest.unstable_mockModule("@/api/queries/cross-benchmark", () => ({
  useCrossBenchmarkMatrix: mockUseCrossBenchmarkMatrix,
  useWeaknessReport: mockUseWeaknessReport,
}));

await jest.unstable_mockModule("@/hooks/useGlobalFilters", () => ({
  useGlobalFilters: () => ({
    benchmark: null,
    model_version: null,
    time_range_start: null,
    time_range_end: null,
    setFilter: mockSetFilter,
    resetFilters: jest.fn(),
  }),
}));

await jest.unstable_mockModule("@/components/EChartsWrapper", () => ({
  __esModule: true,
  default: ({ onEvents }: { onEvents?: { click?: (params: unknown) => void } }) => (
    <button
      data-testid="echarts-mock"
      onClick={() => onEvents?.click?.({ value: [0, 0, 0.3] })}
      type="button"
    />
  ),
}));

const { default: CrossBenchmark } = await import("./index");

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  return ({ children }: { children: ReactNode }) => (
    <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </MemoryRouter>
  );
}

describe("CrossBenchmark page", () => {
  beforeEach(() => {
    jest.clearAllMocks();

    mockUseCrossBenchmarkMatrix.mockReturnValue({
      data: null,
      isLoading: false,
      isError: false,
      refetch: jest.fn(),
    });

    mockUseWeaknessReport.mockReturnValue({
      data: null,
      isLoading: false,
      isError: false,
      refetch: jest.fn(),
    });
  });

  it("renders page and section titles", () => {
    render(<CrossBenchmark />, { wrapper: createWrapper() });

    expect(screen.getByText("Benchmark 横向分析")).toBeInTheDocument();
    expect(screen.getByText("模型版本 × Benchmark 错误率热力图")).toBeInTheDocument();
    expect(screen.getByText("系统性弱点识别报告")).toBeInTheDocument();
    expect(screen.getByText("跨 Benchmark 共性错误模式")).toBeInTheDocument();
  });

  it("wires heatmap cell clicks into benchmark and model version filter updates", () => {
    mockUseCrossBenchmarkMatrix.mockReturnValue({
      data: {
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
      },
      isLoading: false,
      isError: false,
      refetch: jest.fn(),
    });

    render(<CrossBenchmark />, { wrapper: createWrapper() });
    fireEvent.click(screen.getByTestId("echarts-mock"));

    expect(mockSetFilter).toHaveBeenCalledWith("benchmark", "mmlu");
    expect(mockSetFilter).toHaveBeenCalledWith("model_version", "v1.0");
  });

  it("renders weakness summary text and common patterns from report data", () => {
    mockUseWeaknessReport.mockReturnValue({
      data: {
        generated_at: "2026-03-20T10:00:00Z",
        summary: "模型存在系统性弱点。",
        common_patterns: [
          {
            error_type: "reasoning.math",
            affected_benchmarks: ["mmlu", "gsm8k"],
            avg_error_rate: 0.45,
            record_count: 200,
          },
        ],
      },
      isLoading: false,
      isError: false,
      refetch: jest.fn(),
    });

    render(<CrossBenchmark />, { wrapper: createWrapper() });

    expect(screen.getByText(/模型存在系统性弱点/)).toBeInTheDocument();
    expect(screen.getByText("reasoning.math")).toBeInTheDocument();
  });

  it("shows an error alert and retries failed queries", () => {
    const refetchMatrix = jest.fn();
    const refetchReport = jest.fn();

    mockUseCrossBenchmarkMatrix.mockReturnValue({
      data: null,
      isLoading: false,
      isError: true,
      refetch: refetchMatrix,
    });

    mockUseWeaknessReport.mockReturnValue({
      data: null,
      isLoading: false,
      isError: true,
      refetch: refetchReport,
    });

    render(<CrossBenchmark />, { wrapper: createWrapper() });
    fireEvent.click(screen.getByRole("button", { name: /重\s*试/ }));

    expect(screen.getByText("加载失败")).toBeInTheDocument();
    expect(refetchMatrix).toHaveBeenCalled();
    expect(refetchReport).toHaveBeenCalled();
  });
});
