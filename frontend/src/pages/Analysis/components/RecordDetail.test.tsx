import { jest } from "@jest/globals";
import { render, screen } from "@testing-library/react";

const originalMatchMedia = window.matchMedia;

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

jest.unstable_mockModule("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "analysis.detail.title": "错题详情",
        "analysis.detail.question": "题目",
        "analysis.detail.expected": "标准答案",
        "analysis.detail.modelAnswer": "模型回答",
        "analysis.detail.errorTags": "错因标签",
        "analysis.detail.analysisResults": "分析结果",
        "analysis.detail.rootCause": "根因分析",
        "analysis.detail.severity": "严重程度",
        "analysis.detail.confidence": "置信度",
        "analysis.detail.evidence": "证据",
        "analysis.detail.suggestion": "改进建议",
        "analysis.detail.analysisType": "分析方式",
        "analysis.detail.llmModel": "使用模型",
        "analysis.detail.llmCost": "分析成本",
      };
      return map[key] ?? key;
    },
  }),
}));

const { default: RecordDetail } = await import("./RecordDetail");

const mockDetail = {
  record: {
    id: "rec-1",
    question: "What is 2+2?",
    expected_answer: "4",
    model_answer: "5",
    benchmark: "mmlu",
    task_category: "math",
  },
  analysis_results: [
    {
      id: "ar-1",
      analysis_type: "llm",
      error_types: ["推理性错误.数学/计算错误"],
      root_cause: "模型在简单算术计算中出错",
      severity: "medium",
      confidence: 0.92,
      evidence: "模型回答 5，正确答案是 4",
      suggestion: "加强基础算术训练数据",
      llm_model: "gpt-4",
      llm_cost: 0.01,
      unmatched_tags: [],
      created_at: "2026-03-20T00:00:00Z",
    },
  ],
  error_tags: [
    { tag_path: "推理性错误.数学/计算错误.算术错误", tag_level: 3 },
  ],
};

describe("RecordDetail", () => {
  it("renders detail content when open", () => {
    render(<RecordDetail detail={mockDetail} open={true} onClose={jest.fn()} />);

    expect(screen.getByText("What is 2+2?")).toBeInTheDocument();
    expect(screen.getByText("4")).toBeInTheDocument();
    expect(screen.getByText("5")).toBeInTheDocument();
    expect(screen.getByText("推理性错误.数学/计算错误.算术错误")).toBeInTheDocument();
    expect(screen.getByText("模型在简单算术计算中出错")).toBeInTheDocument();
    expect(screen.getByText("gpt-4")).toBeInTheDocument();
  });

  it("does not render drawer content when closed", () => {
    render(<RecordDetail detail={mockDetail} open={false} onClose={jest.fn()} />);

    expect(screen.queryByText("错题详情")).not.toBeInTheDocument();
  });

  it("does not render when detail is null", () => {
    render(<RecordDetail detail={null} open={true} onClose={jest.fn()} />);

    expect(screen.queryByText("错题详情")).not.toBeInTheDocument();
  });
});
