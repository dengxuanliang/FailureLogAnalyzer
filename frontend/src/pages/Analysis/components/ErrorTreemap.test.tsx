import { jest } from "@jest/globals";
import { fireEvent, render, screen } from "@testing-library/react";

jest.unstable_mockModule("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "analysis.treemapTitle": "错误类型分布",
        "analysis.backToL1": "返回 L1 总览",
        "analysis.backToL2": "返回 L2",
        "analysis.errorCount": "错题数",
      };
      return map[key] ?? key;
    },
  }),
}));

jest.unstable_mockModule("../../../components/EChartsWrapper", () => ({
  default: ({ option, onEvents }: { option: { series?: Array<{ data?: Array<{ name: string }> }> }; onEvents?: { click?: (params: { name: string; value: number }) => void } }) => (
    <button
      data-testid="echarts-mock"
      onClick={() => onEvents?.click?.({ name: "格式与规范错误", value: 42 })}
      type="button"
    >
      {JSON.stringify(option.series?.[0]?.data?.map((item) => item.name))}
    </button>
  ),
}));

const { default: ErrorTreemap } = await import("./ErrorTreemap");

const mockData = [
  { label: "格式与规范错误", count: 42, percentage: 30 },
  { label: "推理性错误", count: 28, percentage: 20 },
];

describe("ErrorTreemap", () => {
  it("renders a loading skeleton", () => {
    const { container } = render(
      <ErrorTreemap data={mockData} loading onDrillDown={jest.fn()} />,
    );

    expect(screen.getByText("错误类型分布")).toBeInTheDocument();
    expect(container.querySelector(".ant-skeleton")).toBeInTheDocument();
  });

  it("renders treemap data and handles drill-down clicks", () => {
    const onDrillDown = jest.fn();

    render(<ErrorTreemap data={mockData} loading={false} onDrillDown={onDrillDown} />);

    expect(screen.getByTestId("echarts-mock").textContent).toContain("格式与规范错误");
    fireEvent.click(screen.getByTestId("echarts-mock"));
    expect(onDrillDown).toHaveBeenCalledWith("格式与规范错误");
  });

  it("shows a back button when drilled in and calls onBack", () => {
    const onBack = jest.fn();

    render(
      <ErrorTreemap
        data={mockData}
        loading={false}
        onDrillDown={jest.fn()}
        drillLevel={1}
        breadcrumb={["格式与规范错误"]}
        onBack={onBack}
      />, 
    );

    fireEvent.click(screen.getByText("返回 L1 总览"));
    expect(onBack).toHaveBeenCalledTimes(1);
    expect(screen.getAllByText(/格式与规范错误/).length).toBeGreaterThan(0);
  });
});
