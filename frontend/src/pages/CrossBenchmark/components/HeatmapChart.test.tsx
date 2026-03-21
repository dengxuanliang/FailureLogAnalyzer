import { jest } from "@jest/globals";
import { fireEvent, render, screen } from "@testing-library/react";

const echartsWrapperMock = jest.fn();

await jest.unstable_mockModule("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) =>
      ({
        "cross.heatmap.title": "模型版本 × Benchmark 错误率热力图",
        "cross.heatmap.xAxisLabel": "Benchmark",
        "cross.heatmap.yAxisLabel": "模型版本",
        "cross.heatmap.tooltip": "错误率",
        "cross.heatmap.noData": "暂无跨 Benchmark 数据",
      })[key] ?? key,
  }),
}));

await jest.unstable_mockModule("@/components/EChartsWrapper", () => ({
  __esModule: true,
  default: (props: { option: { xAxis?: { data?: string[] }; yAxis?: { data?: string[] } }; onEvents?: { click?: (params: unknown) => void } }) => {
    echartsWrapperMock(props);
    return (
      <button
        data-testid="echarts-mock"
        data-xaxis={JSON.stringify(props.option.xAxis?.data ?? [])}
        data-yaxis={JSON.stringify(props.option.yAxis?.data ?? [])}
        onClick={() => props.onEvents?.click?.({ value: [0, 0, 0.3] })}
        type="button"
      />
    );
  },
}));

const { default: HeatmapChart } = await import("./HeatmapChart");

const mockMatrix = {
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
    {
      model_version: "v1.0",
      benchmark: "gsm8k",
      error_rate: 0.5,
      error_count: 50,
      total_count: 100,
    },
  ],
};

describe("HeatmapChart", () => {
  beforeEach(() => {
    echartsWrapperMock.mockClear();
  });

  it("renders the translated card title", () => {
    render(<HeatmapChart matrix={mockMatrix} loading={false} onCellClick={jest.fn()} />);

    expect(screen.getByText("模型版本 × Benchmark 错误率热力图")).toBeInTheDocument();
  });

  it("passes benchmark and model version labels into chart axes", () => {
    render(<HeatmapChart matrix={mockMatrix} loading={false} onCellClick={jest.fn()} />);

    const chart = screen.getByTestId("echarts-mock");
    expect(JSON.parse(chart.getAttribute("data-xaxis") ?? "[]")).toEqual(["mmlu", "gsm8k"]);
    expect(JSON.parse(chart.getAttribute("data-yaxis") ?? "[]")).toEqual(["v1.0", "v2.0"]);
  });

  it("emits the clicked cell payload", () => {
    const onCellClick = jest.fn();

    render(<HeatmapChart matrix={mockMatrix} loading={false} onCellClick={onCellClick} />);
    fireEvent.click(screen.getByTestId("echarts-mock"));

    expect(onCellClick).toHaveBeenCalledWith({
      benchmark: "mmlu",
      model_version: "v1.0",
      error_rate: 0.3,
    });
  });

  it("shows empty state when there are no cells", () => {
    render(
      <HeatmapChart
        matrix={{ model_versions: [], benchmarks: [], cells: [] }}
        loading={false}
        onCellClick={jest.fn()}
      />,
    );

    expect(screen.getByText("暂无跨 Benchmark 数据")).toBeInTheDocument();
  });

  it("shows a skeleton while loading", () => {
    const { container } = render(
      <HeatmapChart matrix={null} loading onCellClick={jest.fn()} />,
    );

    expect(container.querySelector(".ant-skeleton")).toBeInTheDocument();
  });
});
