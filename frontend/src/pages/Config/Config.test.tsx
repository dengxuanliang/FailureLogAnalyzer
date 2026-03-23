import { jest } from "@jest/globals";
import { fireEvent, render, screen } from "@testing-library/react";
import { ensureMatchMedia } from "./testUtils";

ensureMatchMedia();

const authState = { role: "admin" as "admin" | "analyst" | "viewer" };

await jest.unstable_mockModule("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) =>
      ({
        "config.title": "分析配置",
        "config.tabs.rules": "规则管理",
        "config.tabs.strategies": "LLM 策略",
        "config.tabs.templates": "Prompt 模板",
        "config.tabs.adapters": "Benchmark Adapter",
        "config.tabs.users": "用户管理",
        "config.tabs.providerSecrets": "Provider 密钥",
      })[key] ?? key,
  }),
}));

await jest.unstable_mockModule("@/contexts/AuthContext", () => ({
  useAuth: () => ({ user: { id: "u1", role: authState.role } }),
}));

await jest.unstable_mockModule("./components/RulesPanel", () => ({
  __esModule: true,
  default: () => <div data-testid="rules-panel">rules</div>,
}));
await jest.unstable_mockModule("./components/StrategiesPanel", () => ({
  __esModule: true,
  default: () => <div data-testid="strategies-panel">strategies</div>,
}));
await jest.unstable_mockModule("./components/TemplatesPanel", () => ({
  __esModule: true,
  default: () => <div data-testid="templates-panel">templates</div>,
}));
await jest.unstable_mockModule("./components/AdaptersPanel", () => ({
  __esModule: true,
  default: () => <div data-testid="adapters-panel">adapters</div>,
}));
await jest.unstable_mockModule("./components/UsersPanel", () => ({
  __esModule: true,
  default: () => <div data-testid="users-panel">users</div>,
}));
await jest.unstable_mockModule("./components/ProviderSecretsPanel", () => ({
  __esModule: true,
  default: () => <div data-testid="provider-secrets-panel">provider-secrets</div>,
}));

const { default: Config } = await import("./index");

describe("Config page", () => {
  it("renders title and base tabs", () => {
    authState.role = "admin";
    render(<Config />);

    expect(screen.getByText("分析配置")).toBeInTheDocument();
    expect(screen.getByText("规则管理")).toBeInTheDocument();
    expect(screen.getByText("LLM 策略")).toBeInTheDocument();
    expect(screen.getByText("Prompt 模板")).toBeInTheDocument();
    expect(screen.getByText("Benchmark Adapter")).toBeInTheDocument();
    expect(screen.getByText("用户管理")).toBeInTheDocument();
    expect(screen.getByText("Provider 密钥")).toBeInTheDocument();
    expect(screen.getByTestId("rules-panel")).toBeInTheDocument();
  });

  it("shows users tab only for admin", () => {
    authState.role = "analyst";
    const { rerender } = render(<Config />);

    expect(screen.queryByText("用户管理")).not.toBeInTheDocument();

    authState.role = "admin";
    rerender(<Config />);

    expect(screen.getByText("用户管理")).toBeInTheDocument();
    expect(screen.getByText("Provider 密钥")).toBeInTheDocument();
  });

  it("switches tabs", () => {
    authState.role = "admin";
    render(<Config />);

    fireEvent.click(screen.getByText("LLM 策略"));
    expect(screen.getByTestId("strategies-panel")).toBeInTheDocument();
  });
});
