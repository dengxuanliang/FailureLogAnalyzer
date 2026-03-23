import { jest } from "@jest/globals";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const mockNavigate = jest.fn();
const mockLogout = jest.fn();

beforeAll(() => {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: ((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: jest.fn(),
      removeListener: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      dispatchEvent: jest.fn(() => false),
    })) as typeof window.matchMedia,
  });
});

beforeEach(() => {
  mockNavigate.mockReset();
  mockLogout.mockReset();
});

jest.unstable_mockModule("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "app.title": "评测日志错因分析",
        "nav.overview": "总览",
        "nav.analysis": "错因分析",
        "nav.compare": "版本对比",
        "nav.crossBenchmark": "横向分析",
        "nav.sessions": "会话中心",
        "nav.reports": "报告中心",
        "nav.config": "分析配置",
        "nav.logout": "退出",
      };
      return map[key] ?? key;
    },
  }),
}));

jest.unstable_mockModule("react-router-dom", () => ({
  Outlet: () => <div data-testid="outlet-mock">outlet content</div>,
  useNavigate: () => mockNavigate,
  useLocation: () => ({ pathname: "/overview" }),
}));

jest.unstable_mockModule("@/contexts/AuthContext", () => ({
  useAuth: () => ({ logout: mockLogout }),
}));

jest.unstable_mockModule("@/contexts/FilterContext", () => ({
  FilterProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

jest.unstable_mockModule("@/components/FilterBar", () => ({
  default: () => <div data-testid="filter-bar-mock">filter bar</div>,
}));

jest.unstable_mockModule("@/components/AgentChatWindow", () => ({
  default: () => <button type="button">Agent Chat</button>,
}));

const { default: AppLayout } = await import("./AppLayout");

describe("AppLayout", () => {
  it("renders sidebar navigation, filter bar, outlet, and handles logout", async () => {
    render(<AppLayout />);

    expect(screen.getByText("评测日志错因分析")).toBeInTheDocument();
    expect(screen.getByText("总览")).toBeInTheDocument();
    expect(screen.getByText("错因分析")).toBeInTheDocument();
    expect(screen.getByText("版本对比")).toBeInTheDocument();
    expect(screen.getByText("横向分析")).toBeInTheDocument();
    expect(screen.getByText("会话中心")).toBeInTheDocument();
    expect(screen.getByText("报告中心")).toBeInTheDocument();
    expect(screen.getByText("Operations")).toBeInTheDocument();
    expect(screen.getByText("分析配置")).toBeInTheDocument();
    expect(screen.getByText("退出")).toBeInTheDocument();
    expect(screen.getByTestId("filter-bar-mock")).toBeInTheDocument();
    expect(screen.getByTestId("outlet-mock")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Agent Chat" })).toBeInTheDocument();

    await userEvent.click(screen.getByText("错因分析"));
    expect(mockNavigate).toHaveBeenCalledWith("/analysis");

    await userEvent.click(screen.getByText("Operations"));
    expect(mockNavigate).toHaveBeenCalledWith("/operations");

    await userEvent.click(screen.getByText("会话中心"));
    expect(mockNavigate).toHaveBeenCalledWith("/sessions");

    await userEvent.click(screen.getByText("报告中心"));
    expect(mockNavigate).toHaveBeenCalledWith("/reports");

    await userEvent.click(screen.getByText("退出"));
    expect(mockLogout).toHaveBeenCalledTimes(1);
    expect(mockNavigate).toHaveBeenCalledWith("/login", { replace: true });
  });
});
