import { jest } from "@jest/globals";
import { fireEvent, render, screen } from "@testing-library/react";
import { ensureMatchMedia } from "../testUtils";

ensureMatchMedia();

const hooksMock = {
  useTemplates: jest.fn(),
  useCreateTemplate: jest.fn(),
  useUpdateTemplate: jest.fn(),
  useDeleteTemplate: jest.fn(),
};

await jest.unstable_mockModule("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) =>
      ({
        "config.templates.title": "Prompt 模板",
        "config.templates.create": "新建模板",
        "config.templates.columns.name": "模板名称",
        "config.templates.columns.benchmark": "绑定 Benchmark",
        "config.templates.columns.version": "版本",
        "config.templates.columns.status": "状态",
        "config.templates.columns.actions": "操作",
        "config.templates.generic": "通用",
      })[key] ?? key,
  }),
}));

await jest.unstable_mockModule("@/api/queries/config", () => hooksMock);
await jest.unstable_mockModule("@/contexts/AuthContext", () => ({
  useAuth: () => ({ user: { id: "u1", role: "admin" } }),
}));
await jest.unstable_mockModule("./TemplateFormModal", () => ({
  __esModule: true,
  default: ({ open, template }: { open: boolean; template: { name: string } | null }) =>
    open ? <div data-testid="template-form-modal">{template?.name ?? "create"}</div> : null,
}));

const { default: TemplatesPanel } = await import("./TemplatesPanel");

describe("TemplatesPanel", () => {
  beforeEach(() => {
    hooksMock.useTemplates.mockReturnValue({
      data: [
        {
          id: "t1",
          name: "GeneralTemplate",
          benchmark: null,
          template: "Analyze: {question}",
          version: 2,
          is_active: true,
          created_by: "admin",
          created_at: "2026-01-01T00:00:00Z",
        },
      ],
      isLoading: false,
    });
    hooksMock.useCreateTemplate.mockReturnValue({ mutateAsync: jest.fn(), isPending: false });
    hooksMock.useUpdateTemplate.mockReturnValue({ mutateAsync: jest.fn(), isPending: false });
    hooksMock.useDeleteTemplate.mockReturnValue({ mutateAsync: jest.fn(), isPending: false });
  });

  it("renders title and template row", () => {
    render(<TemplatesPanel />);

    expect(screen.getByText("Prompt 模板")).toBeInTheDocument();
    expect(screen.getByText("GeneralTemplate")).toBeInTheDocument();
    expect(screen.getByText("通用")).toBeInTheDocument();
  });

  it("opens the create modal", () => {
    render(<TemplatesPanel />);

    fireEvent.click(screen.getByText("新建模板"));

    expect(screen.getByTestId("template-form-modal")).toHaveTextContent("create");
  });
});
