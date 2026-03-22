import { jest } from "@jest/globals";
import { fireEvent, render, screen } from "@testing-library/react";
import { ensureMatchMedia } from "../testUtils";

ensureMatchMedia();

const hooksMock = {
  useStrategies: jest.fn(),
  useCreateStrategy: jest.fn(),
  useUpdateStrategy: jest.fn(),
  useDeleteStrategy: jest.fn(),
};

await jest.unstable_mockModule("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) =>
      ({
        "config.strategies.title": "LLM 策略",
        "config.strategies.create": "新建策略",
        "config.strategies.columns.name": "策略名称",
        "config.strategies.columns.type": "类型",
        "config.strategies.columns.provider": "LLM 提供商",
        "config.strategies.columns.model": "模型",
        "config.strategies.columns.maxConcurrent": "最大并发",
        "config.strategies.columns.dailyBudget": "每日预算",
        "config.strategies.columns.status": "状态",
        "config.strategies.columns.actions": "操作",
        "config.strategies.type.fallback": "规则兜底",
      })[key] ?? key,
  }),
}));

await jest.unstable_mockModule("@/api/queries/config", () => hooksMock);
await jest.unstable_mockModule("@/contexts/AuthContext", () => ({
  useAuth: () => ({ user: { id: "u1", role: "admin" } }),
}));
await jest.unstable_mockModule("./StrategyFormModal", () => ({
  __esModule: true,
  default: ({ open, strategy }: { open: boolean; strategy: { name: string } | null }) =>
    open ? <div data-testid="strategy-form-modal">{strategy?.name ?? "create"}</div> : null,
}));

const { default: StrategiesPanel } = await import("./StrategiesPanel");

describe("StrategiesPanel", () => {
  beforeEach(() => {
    hooksMock.useStrategies.mockReturnValue({
      data: [
        {
          id: "s1",
          name: "FallbackStrategy",
          strategy_type: "fallback",
          config: {},
          llm_provider: "openai",
          llm_model: "gpt-4o",
          prompt_template_id: null,
          max_concurrent: 5,
          daily_budget: 10,
          is_active: true,
          created_by: "admin",
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
        },
      ],
      isLoading: false,
    });
    hooksMock.useCreateStrategy.mockReturnValue({ mutateAsync: jest.fn(), isPending: false });
    hooksMock.useUpdateStrategy.mockReturnValue({ mutateAsync: jest.fn(), isPending: false });
    hooksMock.useDeleteStrategy.mockReturnValue({ mutateAsync: jest.fn(), isPending: false });
  });

  it("renders title and strategy row", () => {
    render(<StrategiesPanel />);

    expect(screen.getByText("LLM 策略")).toBeInTheDocument();
    expect(screen.getByText("FallbackStrategy")).toBeInTheDocument();
    expect(screen.getByText("规则兜底")).toBeInTheDocument();
  });

  it("opens the create modal", () => {
    render(<StrategiesPanel />);

    fireEvent.click(screen.getByText("新建策略"));

    expect(screen.getByTestId("strategy-form-modal")).toHaveTextContent("create");
  });
});
