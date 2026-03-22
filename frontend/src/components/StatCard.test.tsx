import { AimOutlined } from "@ant-design/icons";
import { render, screen } from "@testing-library/react";
import StatCard from "./StatCard";

describe("StatCard", () => {
  it("renders title and value", () => {
    render(<StatCard title="总评测数" value={42} icon={<AimOutlined />} />);

    expect(screen.getByText("总评测数")).toBeInTheDocument();
    expect(screen.getByText("42")).toBeInTheDocument();
  });

  it("renders prefix and suffix", () => {
    render(
      <StatCard
        title="准确率"
        value={70.5}
        icon={<AimOutlined />}
        suffix="%"
      />,
    );

    expect(screen.getByText("%")).toBeInTheDocument();
  });

  it("shows skeleton when loading", () => {
    const { container } = render(
      <StatCard title="总评测数" value={0} icon={<AimOutlined />} loading />,
    );

    expect(container.querySelector(".ant-skeleton")).toBeInTheDocument();
  });
});
