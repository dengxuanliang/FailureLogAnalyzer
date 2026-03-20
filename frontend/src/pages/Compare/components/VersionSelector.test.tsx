import { jest } from "@jest/globals";
import { render, screen } from "@testing-library/react";

jest.unstable_mockModule("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "compare.selectVersionA": "选择版本 A",
        "compare.selectVersionB": "选择版本 B",
        "compare.compare": "对比",
      };
      return map[key] ?? key;
    },
  }),
}));

const { default: VersionSelector } = await import("./VersionSelector");

const mockVersions = ["v1.0", "v2.0", "v3.0"];

describe("VersionSelector", () => {
  it("renders two Select dropdowns and a compare button", () => {
    render(
      <VersionSelector
        versions={mockVersions}
        versionA={null}
        versionB={null}
        onVersionAChange={jest.fn()}
        onVersionBChange={jest.fn()}
        onCompare={jest.fn()}
        loading={false}
      />,
    );

    expect(screen.getByText("选择版本 A")).toBeInTheDocument();
    expect(screen.getByText("选择版本 B")).toBeInTheDocument();
    expect(screen.getByText("对比")).toBeInTheDocument();
  });

  it("disables compare button when versions not selected", () => {
    render(
      <VersionSelector
        versions={mockVersions}
        versionA={null}
        versionB={null}
        onVersionAChange={jest.fn()}
        onVersionBChange={jest.fn()}
        onCompare={jest.fn()}
        loading={false}
      />,
    );

    const button = screen.getByText("对比").closest("button");
    expect(button).toBeDisabled();
  });

  it("enables compare button when both versions selected", () => {
    render(
      <VersionSelector
        versions={mockVersions}
        versionA="v1.0"
        versionB="v2.0"
        onVersionAChange={jest.fn()}
        onVersionBChange={jest.fn()}
        onCompare={jest.fn()}
        loading={false}
      />,
    );

    const button = screen.getByText("对比").closest("button");
    expect(button).not.toBeDisabled();
  });
});
