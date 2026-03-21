import { jest } from "@jest/globals";
import { fireEvent, render, screen } from "@testing-library/react";
import { ensureMatchMedia } from "../testUtils";

ensureMatchMedia();

const hooksMock = {
  useRules: jest.fn(),
  useCreateRule: jest.fn(),
  useUpdateRule: jest.fn(),
  useDeleteRule: jest.fn(),
};

await jest.unstable_mockModule("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, string>) =>
      ({
        "config.rules.title": "分析规则",
        "config.rules.create": "新建规则",
        "config.rules.columns.name": "规则名称",
        "config.rules.columns.field": "目标字段",
        "config.rules.columns.conditionType": "条件类型",
        "config.rules.columns.tags": "产出标签",
        "config.rules.columns.confidence": "置信度",
        "config.rules.columns.priority": "优先级",
        "config.rules.columns.status": "状态",
        "config.rules.columns.actions": "操作",
        "config.rules.enabled": "启用",
        "config.rules.disabled": "停用",
        "config.rules.delete": "删除",
        "common.edit": "编辑",
      })[key] ?? options?.name ?? key,
  }),
}));

await jest.unstable_mockModule("@/api/queries/config", () => hooksMock);
await jest.unstable_mockModule("@/contexts/AuthContext", () => ({
  useAuth: () => ({ user: { id: "u1", role: "admin" } }),
}));
await jest.unstable_mockModule("./RuleFormModal", () => ({
  __esModule: true,
  default: ({ open, rule }: { open: boolean; rule: { name: string } | null }) =>
    open ? <div data-testid="rule-form-modal">{rule?.name ?? "create"}</div> : null,
}));

const { default: RulesPanel } = await import("./RulesPanel");

describe("RulesPanel", () => {
  beforeEach(() => {
    hooksMock.useRules.mockReturnValue({
      data: [
        {
          id: "r1",
          name: "EmptyAnswerRule",
          description: "",
          field: "model_answer",
          condition: { type: "field_missing" },
          tags: ["格式与规范错误.空回答"],
          confidence: 1,
          priority: 1,
          is_active: true,
          created_by: "system",
          created_at: "2026-01-01T00:00:00Z",
          updated_at: "2026-01-01T00:00:00Z",
        },
      ],
      isLoading: false,
    });
    hooksMock.useCreateRule.mockReturnValue({ mutateAsync: jest.fn(), isPending: false });
    hooksMock.useUpdateRule.mockReturnValue({ mutateAsync: jest.fn(), isPending: false });
    hooksMock.useDeleteRule.mockReturnValue({ mutateAsync: jest.fn(), isPending: false });
  });

  it("renders the panel title and rule row", () => {
    render(<RulesPanel />);

    expect(screen.getByText("分析规则")).toBeInTheDocument();
    expect(screen.getByText("EmptyAnswerRule")).toBeInTheDocument();
    expect(screen.getByText("model_answer")).toBeInTheDocument();
  });

  it("opens the create modal", () => {
    render(<RulesPanel />);

    fireEvent.click(screen.getByText("新建规则"));

    expect(screen.getByTestId("rule-form-modal")).toHaveTextContent("create");
  });
});
