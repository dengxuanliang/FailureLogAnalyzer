import { jest } from "@jest/globals";
import { render, screen } from "@testing-library/react";
import { ensureMatchMedia } from "../testUtils";

ensureMatchMedia();

await jest.unstable_mockModule("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) =>
      ({
        "config.adapters.title": "Benchmark Adapter",
        "config.adapters.description": "只读",
        "config.adapters.loadError": "Adapter 接口暂不可用",
        "config.adapters.columns.name": "名称",
        "config.adapters.columns.description": "描述",
        "config.adapters.columns.fields": "检测字段",
        "config.adapters.columns.builtin": "类型",
        "config.adapters.builtin": "内置",
        "config.adapters.custom": "自定义",
      })[key] ?? key,
  }),
}));

const hooksMock = {
  useAdapters: jest.fn(),
};

await jest.unstable_mockModule("@/api/queries/config", () => hooksMock);

const { default: AdaptersPanel } = await import("./AdaptersPanel");

describe("AdaptersPanel", () => {
  beforeEach(() => {
    hooksMock.useAdapters.mockReturnValue({
      data: [
        {
          name: "mmlu",
          description: "MMLU adapter",
          detected_fields: ["subject", "question"],
          is_builtin: true,
        },
      ],
      isLoading: false,
    });
  });

  it("renders adapter information", () => {
    render(<AdaptersPanel />);

    expect(screen.getByText("Benchmark Adapter")).toBeInTheDocument();
    expect(screen.getByText("mmlu")).toBeInTheDocument();
    expect(screen.getByText("MMLU adapter")).toBeInTheDocument();
    expect(screen.getByText("内置")).toBeInTheDocument();
  });

  it("shows an error message when loading fails", () => {
    hooksMock.useAdapters.mockReturnValue({
      data: [],
      isLoading: false,
      error: new Error("boom"),
    });

    render(<AdaptersPanel />);

    expect(screen.getByText("Adapter 接口暂不可用")).toBeInTheDocument();
  });
});
