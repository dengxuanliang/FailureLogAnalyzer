import { jest } from "@jest/globals";
import { fireEvent, render, screen } from "@testing-library/react";
import { ensureMatchMedia } from "../testUtils";

ensureMatchMedia();

await jest.unstable_mockModule("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) =>
      ({
        "config.strategies.create": "新建策略",
        "config.strategies.edit": "编辑策略",
        "config.strategies.form.name": "策略名称",
        "config.strategies.form.type": "策略类型",
        "config.strategies.form.provider": "LLM 提供商",
        "config.strategies.form.model": "模型名称",
        "config.strategies.form.maxConcurrent": "最大并发",
        "config.strategies.form.dailyBudget": "每日预算",
        "config.strategies.form.isActive": "启用",
        "common.save": "保存",
        "common.cancel": "取消",
      })[key] ?? key,
  }),
}));

await jest.unstable_mockModule("@/api/queries/config", () => ({
  useTemplates: () => ({ data: [], isLoading: false }),
}));

const { default: StrategyFormModal } = await import("./StrategyFormModal");

describe("StrategyFormModal", () => {
  it("renders create title when no strategy is provided", () => {
    render(
      <StrategyFormModal
        open
        strategy={null}
        onSubmit={jest.fn()}
        onCancel={jest.fn()}
        loading={false}
      />,
    );

    expect(screen.getByText("新建策略")).toBeInTheDocument();
  });

  it("renders edit title when a strategy is provided", () => {
    render(
      <StrategyFormModal
        open
        strategy={{
          id: "s1",
          name: "Fallback",
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
        }}
        onSubmit={jest.fn()}
        onCancel={jest.fn()}
        loading={false}
      />,
    );

    expect(screen.getByText("编辑策略")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Fallback")).toBeInTheDocument();
  });

  it("calls onCancel when cancel is clicked", () => {
    const onCancel = jest.fn();
    render(
      <StrategyFormModal
        open
        strategy={null}
        onSubmit={jest.fn()}
        onCancel={onCancel}
        loading={false}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /取\s*消/ }));

    expect(onCancel).toHaveBeenCalledTimes(1);
  });
});
