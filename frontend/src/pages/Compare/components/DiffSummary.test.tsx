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

jest.unstable_mockModule("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "compare.diff.title": "变化摘要",
        "compare.diff.regressed": "退化题目",
        "compare.diff.improved": "进步题目",
        "compare.diff.newErrors": "新增错误类型",
        "compare.diff.resolvedErrors": "已解决错误类型",
        "compare.diff.noChanges": "两个版本间没有差异",
        "compare.diff.questionId": "题目 ID",
        "compare.diff.benchmark": "Benchmark",
        "compare.diff.category": "任务类别",
        "compare.metrics.total": "总题数",
        "compare.metrics.errors": "错题数",
        "compare.metrics.accuracy": "准确率",
      };
      return map[key] ?? key;
    },
  }),
}));

const { default: DiffSummary } = await import("./DiffSummary");
import type { VersionComparison, VersionDiff } from "../../../types/api";

const mockComparison: VersionComparison = {
  version_a: "v1.0",
  version_b: "v2.0",
  benchmark: null,
  metrics_a: { total: 100, errors: 30, accuracy: 0.7, error_type_distribution: {} },
  metrics_b: { total: 100, errors: 20, accuracy: 0.8, error_type_distribution: {} },
};

const mockDiff: VersionDiff = {
  regressed: [
    { question_id: "q1", benchmark: "mmlu", task_category: "math", question: "2+2?" },
  ],
  improved: [
    { question_id: "q2", benchmark: "mmlu", task_category: "logic", question: "If A then B" },
  ],
  new_errors: ["格式与规范错误"],
  resolved_errors: ["解析类错误"],
};

describe("DiffSummary", () => {
  it("renders metrics comparison", () => {
    render(
      <DiffSummary
        comparison={mockComparison}
        diff={mockDiff}
        loading={false}
      />,
    );

    expect(screen.getByText("变化摘要")).toBeInTheDocument();
    expect(screen.getByText("总题数")).toBeInTheDocument();
  });

  it("renders regressed items", () => {
    render(
      <DiffSummary
        comparison={mockComparison}
        diff={mockDiff}
        loading={false}
      />,
    );

    expect(screen.getByText("退化题目")).toBeInTheDocument();
    expect(screen.getByText("q1")).toBeInTheDocument();
  });

  it("renders improved items", () => {
    render(
      <DiffSummary
        comparison={mockComparison}
        diff={mockDiff}
        loading={false}
      />,
    );

    expect(screen.getByText("进步题目")).toBeInTheDocument();
    expect(screen.getByText("q2")).toBeInTheDocument();
  });

  it("renders new and resolved error types", () => {
    render(
      <DiffSummary
        comparison={mockComparison}
        diff={mockDiff}
        loading={false}
      />,
    );

    expect(screen.getByText("新增错误类型")).toBeInTheDocument();
    expect(screen.getByText("格式与规范错误")).toBeInTheDocument();
    expect(screen.getByText("已解决错误类型")).toBeInTheDocument();
    expect(screen.getByText("解析类错误")).toBeInTheDocument();
  });

  it("shows no-changes message when diff is empty", () => {
    const emptyDiff: VersionDiff = {
      regressed: [],
      improved: [],
      new_errors: [],
      resolved_errors: [],
    };

    render(
      <DiffSummary
        comparison={mockComparison}
        diff={emptyDiff}
        loading={false}
      />,
    );

    expect(screen.getByText("两个版本间没有差异")).toBeInTheDocument();
  });
});
