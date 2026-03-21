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
        "cross.weakness.title": "系统性弱点识别报告",
        "cross.weakness.generatedAt": "生成时间",
        "cross.weakness.noReport": "暂无分析报告，请先完成多个 Benchmark 的评测分析",
      })[key] ?? key,
  }),
}));

const { default: WeaknessReport } = await import("./WeaknessReport");

const mockReport = {
  generated_at: "2026-03-20T10:00:00Z",
  summary: "## 系统性弱点\n\n模型在数学推理方面存在普遍弱点。",
  common_patterns: [],
};

describe("WeaknessReport", () => {
  it("renders the card title", () => {
    render(<WeaknessReport report={mockReport} loading={false} />);

    expect(screen.getByText("系统性弱点识别报告")).toBeInTheDocument();
  });

  it("renders the generated-at label and summary text", () => {
    render(<WeaknessReport report={mockReport} loading={false} />);

    expect(screen.getByText("生成时间")).toBeInTheDocument();
    expect(screen.getByText(/模型在数学推理方面存在普遍弱点/)).toBeInTheDocument();
  });

  it("shows empty state when report is null", () => {
    render(<WeaknessReport report={null} loading={false} />);

    expect(screen.getByText("暂无分析报告，请先完成多个 Benchmark 的评测分析")).toBeInTheDocument();
  });

  it("shows a skeleton while loading", () => {
    const { container } = render(<WeaknessReport report={null} loading />);

    expect(container.querySelector(".ant-skeleton")).toBeInTheDocument();
  });
});
