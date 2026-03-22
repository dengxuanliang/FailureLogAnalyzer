import { jest } from "@jest/globals";
import { fireEvent, render, screen } from "@testing-library/react";

const mockUseErrorDistribution: any = jest.fn();
const mockUseErrorRecords: any = jest.fn();
const mockUseRecordDetail: any = jest.fn();

jest.unstable_mockModule("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "analysis.title": "错因分析",
        "analysis.noErrors": "当前筛选条件下没有错题数据",
        "common.error": "加载失败",
        "common.retry": "重试",
      };
      return map[key] ?? key;
    },
  }),
}));

jest.unstable_mockModule("../../api/queries/analysis", () => ({
  useErrorDistribution: mockUseErrorDistribution,
  useErrorRecords: mockUseErrorRecords,
  useRecordDetail: mockUseRecordDetail,
}));

jest.unstable_mockModule("./components/ErrorTreemap", () => ({
  default: ({ onDrillDown, breadcrumb }: { onDrillDown: (label: string) => void; breadcrumb?: string[] }) => (
    <div>
      <div>错误类型分布</div>
      <div data-testid="breadcrumb">{breadcrumb?.join(" > ")}</div>
      <button type="button" onClick={() => onDrillDown("格式与规范错误")}>
        drilldown
      </button>
    </div>
  ),
}));

jest.unstable_mockModule("./components/ErrorTable", () => ({
  default: ({ onViewDetail }: { onViewDetail: (recordId: string) => void }) => (
    <div>
      <div>错题列表</div>
      <button type="button" onClick={() => onViewDetail("rec-1")}>
        detail
      </button>
    </div>
  ),
}));

jest.unstable_mockModule("./components/RecordDetail", () => ({
  default: ({ detail, open }: { detail: { record?: { id?: string } } | null; open: boolean }) => (
    open && detail ? <div>detail:{detail.record?.id}</div> : null
  ),
}));

const { default: Analysis } = await import("./index");

describe("Analysis page", () => {
  beforeEach(() => {
    jest.clearAllMocks();

    mockUseErrorDistribution.mockImplementation(((_groupBy: string, errorType?: string) => ({
      data: errorType === "格式与规范错误"
        ? [{ label: "数学/计算错误", count: 10, percentage: 50 }]
        : [{ label: "格式与规范错误", count: 42, percentage: 30 }],
      isLoading: false,
      isError: false,
      refetch: jest.fn(),
    })) as any);

    mockUseErrorRecords.mockImplementation((({ errorType }: { errorType?: string }) => ({
      data: {
        items: [
          {
            id: "rec-1",
            session_id: "s1",
            benchmark: "mmlu",
            task_category: "math",
            question_id: "q1",
            question: errorType ? `filtered:${errorType}` : "2+2?",
            is_correct: false,
            score: 0,
            error_tags: [errorType ?? "推理性错误"],
            has_llm_analysis: false,
          },
        ],
        total: 1,
        page: 1,
        size: 20,
      },
      isLoading: false,
      isError: false,
    })) as any);

    mockUseRecordDetail.mockImplementation(((recordId: string | null) => ({
      data: recordId
        ? {
            record: { id: recordId },
            analysis_results: [],
            error_tags: [],
          }
        : null,
      isLoading: false,
    })) as any);
  });

  it("renders the page and wires drill-down and detail state", () => {
    render(<Analysis />);

    expect(screen.getByText("错因分析")).toBeInTheDocument();
    expect(screen.getByText("错误类型分布")).toBeInTheDocument();
    expect(screen.getByText("错题列表")).toBeInTheDocument();
    expect(mockUseErrorDistribution).toHaveBeenCalledWith("error_type", undefined);
    expect(mockUseErrorRecords).toHaveBeenCalledWith({ page: 1, size: 20, errorType: undefined });

    fireEvent.click(screen.getByText("drilldown"));
    expect(mockUseErrorDistribution).toHaveBeenLastCalledWith("error_type", "格式与规范错误");
    expect(mockUseErrorRecords).toHaveBeenLastCalledWith({
      page: 1,
      size: 20,
      errorType: "格式与规范错误",
    });

    fireEvent.click(screen.getByText("detail"));
    expect(mockUseRecordDetail).toHaveBeenLastCalledWith("rec-1");
    expect(screen.getByText("detail:rec-1")).toBeInTheDocument();
  });

  it("shows empty state when there is no distribution data", () => {
    mockUseErrorDistribution.mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
      refetch: jest.fn(),
    });
    mockUseErrorRecords.mockReturnValue({
      data: { items: [], total: 0, page: 1, size: 20 },
      isLoading: false,
      isError: false,
    });

    render(<Analysis />);
    expect(screen.getByText("当前筛选条件下没有错题数据")).toBeInTheDocument();
  });
});
