import { jest } from "@jest/globals";
import { render, screen } from "@testing-library/react";
import type { EChartsOption } from "echarts";
import type { DistributionItem } from "@/types/api";

const echartsWrapperMock = jest.fn();

await jest.unstable_mockModule("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) =>
      ({
        "overview.errorDistribution": "L1 错误类型分布",
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

const { default: ErrorTypeDonut } = await import("./ErrorTypeDonut");

describe("ErrorTypeDonut", () => {
  beforeEach(() => {
    echartsWrapperMock.mockClear();
  });

  it("renders the translated card title and donut chart data from distribution items", () => {
    const data: DistributionItem[] = [
      { label: "推理性错误", count: 12, percentage: 40 },
      { label: "理解性错误", count: 18, percentage: 60 },
    ];

    render(<ErrorTypeDonut data={data} />);

    expect(screen.getByText("L1 错误类型分布")).toBeInTheDocument();
    expect(screen.getByTestId("echarts-wrapper-mock")).toBeInTheDocument();
    expect(echartsWrapperMock).toHaveBeenCalledWith(
      expect.objectContaining({
        height: 350,
        loading: undefined,
        option: expect.objectContaining({
          series: [
            expect.objectContaining({
              type: "pie",
              radius: ["40%", "70%"],
              data: [
                { name: "推理性错误", value: 12 },
                { name: "理解性错误", value: 18 },
              ],
            }),
          ],
        }),
      }),
    );
  });

  it("passes loading through to EChartsWrapper", () => {
    render(<ErrorTypeDonut data={[]} loading />);

    expect(echartsWrapperMock).toHaveBeenCalledWith(
      expect.objectContaining({
        loading: true,
      }),
    );
  });
});
