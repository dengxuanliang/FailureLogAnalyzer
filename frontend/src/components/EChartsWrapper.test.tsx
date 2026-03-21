import { jest } from "@jest/globals";
import { render, screen } from "@testing-library/react";

jest.unstable_mockModule("echarts-for-react", () => ({
  default: (props: { option: unknown; onEvents?: Record<string, unknown> }) => (
    <div
      data-testid="echarts-mock"
      data-events={JSON.stringify(Object.keys(props.onEvents ?? {}))}
    >
      {JSON.stringify(props.option)}
    </div>
  ),
}));

const { default: EChartsWrapper } = await import("./EChartsWrapper");

describe("EChartsWrapper", () => {
  it("renders chart with provided options", () => {
    const option = { title: { text: "Test" } };

    render(<EChartsWrapper option={option} height={300} />);

    expect(screen.getByTestId("echarts-mock")).toBeInTheDocument();
  });

  it("shows skeleton when loading", () => {
    const { container } = render(
      <EChartsWrapper option={{}} height={300} loading />,
    );

    expect(container.querySelector(".ant-skeleton")).toBeInTheDocument();
  });

  it("passes chart events through", () => {
    render(
      <EChartsWrapper
        option={{}}
        onEvents={{ click: () => undefined, mouseover: () => undefined }}
      />,
    );

    expect(screen.getByTestId("echarts-mock")).toHaveAttribute(
      "data-events",
      JSON.stringify(["click", "mouseover"]),
    );
  });
});
