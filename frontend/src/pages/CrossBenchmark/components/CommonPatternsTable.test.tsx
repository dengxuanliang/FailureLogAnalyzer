import { jest } from "@jest/globals";
import { render, screen } from "@testing-library/react";

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
        "cross.patterns.title": "跨 Benchmark 共性错误模式",
        "cross.patterns.columns.errorType": "错误类型",
        "cross.patterns.columns.benchmarks": "涉及 Benchmark",
        "cross.patterns.columns.avgErrorRate": "平均错误率",
        "cross.patterns.columns.recordCount": "涉及题数",
        "cross.patterns.noData": "暂无共性错误模式数据",
      })[key] ?? key,
  }),
}));

const { default: CommonPatternsTable } = await import("./CommonPatternsTable");

const mockPatterns = [
  {
    error_type: "推理性错误.数学/计算错误",
    affected_benchmarks: ["mmlu", "gsm8k", "math"],
    avg_error_rate: 0.45,
    record_count: 230,
  },
  {
    error_type: "格式与规范错误.输出格式不符",
    affected_benchmarks: ["humaneval", "mbpp"],
    avg_error_rate: 0.28,
    record_count: 110,
  },
];

describe("CommonPatternsTable", () => {
  it("renders the card title and column headers", () => {
    render(<CommonPatternsTable patterns={mockPatterns} loading={false} />);

    expect(screen.getByText("跨 Benchmark 共性错误模式")).toBeInTheDocument();
    expect(screen.getByText("错误类型")).toBeInTheDocument();
    expect(screen.getByText("涉及 Benchmark")).toBeInTheDocument();
    expect(screen.getByText("平均错误率")).toBeInTheDocument();
    expect(screen.getByText("涉及题数")).toBeInTheDocument();
  });

  it("renders pattern values, benchmark tags, and formatted rates", () => {
    render(<CommonPatternsTable patterns={mockPatterns} loading={false} />);

    expect(screen.getByText("推理性错误.数学/计算错误")).toBeInTheDocument();
    expect(screen.getByText("格式与规范错误.输出格式不符")).toBeInTheDocument();
    expect(screen.getByText("mmlu")).toBeInTheDocument();
    expect(screen.getByText("gsm8k")).toBeInTheDocument();
    expect(screen.getByText("45.0%")).toBeInTheDocument();
    expect(screen.getByText("28.0%")).toBeInTheDocument();
  });

  it("shows empty state when no patterns are available", () => {
    render(<CommonPatternsTable patterns={[]} loading={false} />);

    expect(screen.getByText("暂无共性错误模式数据")).toBeInTheDocument();
  });
});
