import { jest } from "@jest/globals";
import { render, screen } from "@testing-library/react";
import type { RadarData } from "../../../types/api";

jest.unstable_mockModule("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "compare.radar.title": "能力雷达图",
      };
      return map[key] ?? key;
    },
  }),
}));

jest.unstable_mockModule("../../../components/EChartsWrapper", () => ({
  default: ({ option }: { option: { radar?: { indicator?: Array<{ name: string }> }; series?: Array<{ data?: Array<{ name: string; value: number[] }> }> } }) => (
    <div data-testid="echarts-mock">
      {JSON.stringify({
        indicators: option.radar?.indicator?.map((indicator) => indicator.name),
        series: option.series?.[0]?.data?.map((item) => ({
          name: item.name,
          value: item.value,
        })),
      })}
    </div>
  ),
}));

const { default: RadarChart } = await import("./RadarChart");

const mockData: RadarData = {
  dimensions: ["math", "logic", "reading", "writing"],
  scores_a: [0.8, 0.7, 0.9, 0.6],
  scores_b: [0.85, 0.75, 0.88, 0.7],
};

describe("RadarChart", () => {
  it("shows a titled skeleton when loading", () => {
    const { container } = render(
      <RadarChart data={mockData} versionA="v1.0" versionB="v2.0" loading />,
    );

    expect(screen.getByText("能力雷达图")).toBeInTheDocument();
    expect(container.querySelector(".ant-skeleton")).toBeInTheDocument();
  });

  it("shows a skeleton when data is null", () => {
    const { container } = render(
      <RadarChart data={null} versionA="v1.0" versionB="v2.0" loading={false} />,
    );

    expect(container.querySelector(".ant-skeleton")).toBeInTheDocument();
  });

  it("renders radar indicators and both version series when data is available", () => {
    render(
      <RadarChart data={mockData} versionA="v1.0" versionB="v2.0" loading={false} />,
    );

    const chart = screen.getByTestId("echarts-mock");
    expect(chart.textContent).toContain("math");
    expect(chart.textContent).toContain("logic");
    expect(chart.textContent).toContain("reading");
    expect(chart.textContent).toContain("writing");
    expect(chart.textContent).toContain("v1.0");
    expect(chart.textContent).toContain("v2.0");
    expect(chart.textContent).toContain("0.8");
    expect(chart.textContent).toContain("0.85");
  });
});
