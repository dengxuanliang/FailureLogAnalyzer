import { jest } from "@jest/globals";
import { render, screen } from "@testing-library/react";
import type { EChartsOption } from "echarts";
import type { TrendPoint } from "@/types/api";

const echartsWrapperMock = jest.fn();

await jest.unstable_mockModule("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) =>
      ({
        "overview.trendChart": "错误率趋势",
      })[key] ?? key,
  }),
}));

await jest.unstable_mockModule("@/components/EChartsWrapper", () => ({
  __esModule: true,
  default: (props: { option: EChartsOption; height?: number; loading?: boolean }) => {
    echartsWrapperMock(props);
    return <div data-testid="echarts-wrapper-mock" />;
  },
}));

const { default: TrendChart } = await import("./TrendChart");

describe("TrendChart", () => {
  beforeEach(() => {
    echartsWrapperMock.mockClear();
  });

  it("renders the translated card title and line chart data from trend points", () => {
    const data: TrendPoint[] = [
      { period: "2026-03-01", error_rate: 0.35, total: 100, errors: 35 },
      { period: "2026-03-02", error_rate: 0.2, total: 100, errors: 20 },
    ];

    render(<TrendChart data={data} />);

    expect(screen.getByText("错误率趋势")).toBeInTheDocument();
    expect(screen.getByTestId("echarts-wrapper-mock")).toBeInTheDocument();
    expect(echartsWrapperMock).toHaveBeenCalledWith(
      expect.objectContaining({
        height: 350,
        loading: undefined,
        option: expect.objectContaining({
          xAxis: expect.objectContaining({ data: ["2026-03-01", "2026-03-02"] }),
          series: [
            expect.objectContaining({
              type: "line",
              data: [35, 20],
            }),
          ],
        }),
      }),
    );
  });

  it("passes loading through to EChartsWrapper", () => {
    render(<TrendChart data={[]} loading />);

    expect(echartsWrapperMock).toHaveBeenCalledWith(
      expect.objectContaining({
        loading: true,
      }),
    );
  });
});
