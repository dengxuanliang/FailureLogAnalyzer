import { jest } from "@jest/globals";
import { fireEvent, render, screen } from "@testing-library/react";

const originalMatchMedia = window.matchMedia;
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
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: originalMatchMedia,
  });
  Object.defineProperty(window, "getComputedStyle", {
    writable: true,
    value: originalGetComputedStyle,
  });
});

jest.unstable_mockModule("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "analysis.recordsTitle": "错题列表",
        "analysis.columns.questionId": "题目 ID",
        "analysis.columns.benchmark": "Benchmark",
        "analysis.columns.category": "任务类别",
        "analysis.columns.question": "题目",
        "analysis.columns.errorTags": "错因标签",
        "analysis.columns.hasLlm": "LLM 分析",
        "analysis.columns.actions": "操作",
        "analysis.viewDetail": "查看详情",
      };
      return map[key] ?? key;
    },
  }),
}));

const { default: ErrorTable } = await import("./ErrorTable");

const mockRecords = [
  {
    id: "rec-1",
    session_id: "sess-1",
    benchmark: "mmlu",
    task_category: "math",
    question_id: "q1",
    question: "What is 2+2?",
    is_correct: false,
    score: 0,
    error_tags: ["推理性错误.数学/计算错误"],
    has_llm_analysis: true,
  },
  {
    id: "rec-2",
    session_id: "sess-1",
    benchmark: "mmlu",
    task_category: "logic",
    question_id: "q2",
    question: "All cats are...",
    is_correct: false,
    score: 0,
    error_tags: ["推理性错误.逻辑推理错误"],
    has_llm_analysis: false,
  },
];

describe("ErrorTable", () => {
  it("renders records and the table title", () => {
    render(
      <ErrorTable
        records={mockRecords}
        total={2}
        page={1}
        size={20}
        loading={false}
        onPageChange={jest.fn()}
        onViewDetail={jest.fn()}
      />,
    );

    expect(screen.getByText("错题列表")).toBeInTheDocument();
    expect(screen.getByText("q1")).toBeInTheDocument();
    expect(screen.getByText("q2")).toBeInTheDocument();
  });

  it("calls onViewDetail when view detail is clicked", () => {
    const onViewDetail = jest.fn();

    render(
      <ErrorTable
        records={mockRecords}
        total={2}
        page={1}
        size={20}
        loading={false}
        onPageChange={jest.fn()}
        onViewDetail={onViewDetail}
      />,
    );

    fireEvent.click(screen.getAllByText("查看详情")[0].closest("button") as HTMLButtonElement);
    expect(onViewDetail).toHaveBeenCalledWith("rec-1");
  });

  it("renders llm status icons", () => {
    const { container } = render(
      <ErrorTable
        records={mockRecords}
        total={2}
        page={1}
        size={20}
        loading={false}
        onPageChange={jest.fn()}
        onViewDetail={jest.fn()}
      />,
    );

    expect(container.querySelectorAll(".anticon-check-circle")).toHaveLength(1);
    expect(container.querySelectorAll(".anticon-close-circle")).toHaveLength(1);
  });
});
