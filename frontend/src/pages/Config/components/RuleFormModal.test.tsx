import { jest } from "@jest/globals";
import { fireEvent, render, screen } from "@testing-library/react";
import { ensureMatchMedia } from "../testUtils";

ensureMatchMedia();

await jest.unstable_mockModule("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) =>
      ({
        "config.rules.create": "新建规则",
        "config.rules.edit": "编辑规则",
        "config.rules.form.name": "规则名称",
        "config.rules.form.field": "目标字段",
        "config.rules.form.conditionType": "条件类型",
        "config.rules.form.pattern": "匹配模式/值",
        "config.rules.form.tags": "产出标签",
        "config.rules.form.confidence": "置信度",
        "config.rules.form.priority": "优先级",
        "config.rules.form.isActive": "启用",
        "common.save": "保存",
        "common.cancel": "取消",
      })[key] ?? key,
  }),
}));

const { default: RuleFormModal } = await import("./RuleFormModal");

const mockRule = {
  id: "r1",
  name: "EmptyAnswerRule",
  description: "Detects empty answers",
  field: "model_answer",
  condition: { type: "field_missing" as const },
  tags: ["格式与规范错误.空回答"],
  confidence: 1,
  priority: 1,
  is_active: true,
  created_by: "system",
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

describe("RuleFormModal", () => {
  it("renders create title when no rule is provided", () => {
    render(<RuleFormModal open rule={null} onSubmit={jest.fn()} onCancel={jest.fn()} loading={false} />);

    expect(screen.getByText("新建规则")).toBeInTheDocument();
  });

  it("renders edit title and prefilled values when editing", () => {
    render(
      <RuleFormModal
        open
        rule={mockRule}
        onSubmit={jest.fn()}
        onCancel={jest.fn()}
        loading={false}
      />,
    );

    expect(screen.getByText("编辑规则")).toBeInTheDocument();
    expect(screen.getByDisplayValue("EmptyAnswerRule")).toBeInTheDocument();
    expect(screen.getByDisplayValue("model_answer")).toBeInTheDocument();
  });

  it("calls onCancel when cancel is clicked", () => {
    const onCancel = jest.fn();
    render(<RuleFormModal open rule={null} onSubmit={jest.fn()} onCancel={onCancel} loading={false} />);

    fireEvent.click(screen.getByRole("button", { name: /取\s*消/ }));

    expect(onCancel).toHaveBeenCalledTimes(1);
  });
});
