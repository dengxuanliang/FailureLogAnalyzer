import { jest } from "@jest/globals";
import { fireEvent, render, screen } from "@testing-library/react";
import { ensureMatchMedia } from "../testUtils";

ensureMatchMedia();

await jest.unstable_mockModule("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) =>
      ({
        "config.templates.create": "新建模板",
        "config.templates.edit": "编辑模板",
        "config.templates.form.name": "模板名称",
        "config.templates.form.benchmark": "绑定 Benchmark",
        "config.templates.form.template": "模板内容",
        "config.templates.form.isActive": "启用",
        "common.save": "保存",
        "common.cancel": "取消",
      })[key] ?? key,
  }),
}));

const { default: TemplateFormModal } = await import("./TemplateFormModal");

describe("TemplateFormModal", () => {
  it("renders create title", () => {
    render(
      <TemplateFormModal
        open
        template={null}
        onSubmit={jest.fn()}
        onCancel={jest.fn()}
        loading={false}
      />,
    );

    expect(screen.getByText("新建模板")).toBeInTheDocument();
  });

  it("renders edit title and prefilled values", () => {
    render(
      <TemplateFormModal
        open
        template={{
          id: "t1",
          name: "GeneralTemplate",
          benchmark: null,
          template: "Analyze: {question}",
          version: 1,
          is_active: true,
          created_by: "admin",
          created_at: "2026-01-01T00:00:00Z",
        }}
        onSubmit={jest.fn()}
        onCancel={jest.fn()}
        loading={false}
      />,
    );

    expect(screen.getByText("编辑模板")).toBeInTheDocument();
    expect(screen.getByDisplayValue("GeneralTemplate")).toBeInTheDocument();
  });

  it("calls onCancel", () => {
    const onCancel = jest.fn();
    render(
      <TemplateFormModal
        open
        template={null}
        onSubmit={jest.fn()}
        onCancel={onCancel}
        loading={false}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /取\s*消/ }));

    expect(onCancel).toHaveBeenCalledTimes(1);
  });
});
