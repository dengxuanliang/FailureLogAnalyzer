import { jest } from "@jest/globals";
import { fireEvent, render, screen } from "@testing-library/react";
import { ensureMatchMedia } from "../testUtils";

ensureMatchMedia();

await jest.unstable_mockModule("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) =>
      ({
        "config.users.create": "新建用户",
        "config.users.edit": "编辑用户",
        "config.users.form.username": "用户名",
        "config.users.form.email": "邮箱",
        "config.users.form.password": "密码",
        "config.users.form.role": "角色",
        "config.users.role.admin": "管理员",
        "config.users.role.analyst": "分析师",
        "config.users.role.viewer": "只读用户",
        "common.save": "保存",
        "common.cancel": "取消",
      })[key] ?? key,
  }),
}));

const { default: UserFormModal } = await import("./UserFormModal");

describe("UserFormModal", () => {
  it("renders create mode", () => {
    render(<UserFormModal open onSubmit={jest.fn()} onCancel={jest.fn()} />);

    expect(screen.getByText("新建用户")).toBeInTheDocument();
  });

  it("renders edit mode with values", () => {
    render(
      <UserFormModal
        open
        onSubmit={jest.fn()}
        onCancel={jest.fn()}
        initialValues={{ id: "u1", username: "alice", email: "a@example.com", role: "analyst" }}
      />,
    );

    expect(screen.getByText("编辑用户")).toBeInTheDocument();
    expect(screen.getByDisplayValue("alice")).toBeInTheDocument();
  });

  it("calls onCancel", () => {
    const onCancel = jest.fn();
    render(<UserFormModal open onSubmit={jest.fn()} onCancel={onCancel} />);

    fireEvent.click(screen.getByRole("button", { name: /取\s*消/ }));

    expect(onCancel).toHaveBeenCalledTimes(1);
  });
});
