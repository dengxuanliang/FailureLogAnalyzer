import { jest } from "@jest/globals";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ensureMatchMedia } from "../testUtils";

ensureMatchMedia();

const hooksMock = {
  useUsers: jest.fn(),
  useCreateUser: jest.fn(),
  useUpdateUser: jest.fn(),
};

await jest.unstable_mockModule("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) =>
      ({
        "config.users.title": "用户管理",
        "config.users.create": "新建用户",
        "config.users.loadError": "用户接口暂不可用",
        "config.users.columns.username": "用户名",
        "config.users.columns.email": "邮箱",
        "config.users.columns.role": "角色",
        "config.users.columns.status": "状态",
        "config.users.columns.createdAt": "创建时间",
        "config.users.columns.actions": "操作",
        "config.users.active": "正常",
        "config.users.inactive": "已停用",
        "config.users.role.admin": "管理员",
        "config.users.role.analyst": "分析师",
        "config.users.role.viewer": "只读用户",
      })[key] ?? key,
  }),
}));

await jest.unstable_mockModule("@/api/queries/config", () => hooksMock);
await jest.unstable_mockModule("@/contexts/AuthContext", () => ({
  useAuth: () => ({ user: { id: "1", role: "admin" } }),
}));
await jest.unstable_mockModule("./UserFormModal", () => ({
  __esModule: true,
  default: () => null,
}));

const { default: UsersPanel } = await import("./UsersPanel");

describe("UsersPanel", () => {
  beforeEach(() => {
    hooksMock.useUsers.mockReturnValue({
      data: [
        {
          id: "1",
          username: "admin",
          email: "a@example.com",
          role: "admin",
          is_active: true,
          created_at: "2026-01-01",
        },
        {
          id: "2",
          username: "viewer1",
          email: "v@example.com",
          role: "viewer",
          is_active: false,
          created_at: "2026-01-02",
        },
      ],
      isLoading: false,
    });
    hooksMock.useCreateUser.mockReturnValue({ mutateAsync: jest.fn(), isPending: false });
    hooksMock.useUpdateUser.mockReturnValue({ mutateAsync: jest.fn(), isPending: false });
  });

  it("renders user rows and create button", () => {
    render(<UsersPanel />);

    expect(screen.getByText("用户管理")).toBeInTheDocument();
    expect(screen.getByText("新建用户")).toBeInTheDocument();
    expect(screen.getByText("admin")).toBeInTheDocument();
    expect(screen.getByText("viewer1")).toBeInTheDocument();
  });

  it("renders active and inactive statuses", () => {
    render(<UsersPanel />);

    expect(screen.getByText("正常")).toBeInTheDocument();
    expect(screen.getByText("已停用")).toBeInTheDocument();
  });

  it("shows an explicit error state when the users API is unavailable", async () => {
    hooksMock.useUsers.mockReturnValue({
      data: [],
      isLoading: false,
      error: new Error("missing /users api"),
    });

    render(<UsersPanel />);

    expect(screen.getByText("用户接口暂不可用")).toBeInTheDocument();
    const createButton = screen.getByRole("button", { name: "新建用户" });
    expect(createButton).toBeDisabled();

    await userEvent.click(createButton);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});
