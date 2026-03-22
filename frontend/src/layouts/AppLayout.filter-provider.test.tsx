import { jest } from "@jest/globals";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { useGlobalFilters } from "@/hooks/useGlobalFilters";

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
  mockLogout.mockReset();
});

jest.unstable_mockModule("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

jest.unstable_mockModule("@/contexts/AuthContext", () => ({
  useAuth: () => ({ logout: mockLogout }),
}));

jest.unstable_mockModule("@/components/FilterBar", () => ({
  default: () => <div data-testid="filter-bar-mock">filter bar</div>,
}));

jest.unstable_mockModule("@/components/AgentChatWindow", () => ({
  default: function MockAgentChatWindow() {
    const { benchmark } = useGlobalFilters();
    return <div data-testid="agent-chat-filter-value">{benchmark ?? "no-benchmark"}</div>;
  },
}));

const { default: AppLayout } = await import("./AppLayout");

describe("AppLayout filter provider integration", () => {
  it("renders AgentChatWindow inside FilterProvider", () => {
    render(
      <MemoryRouter initialEntries={["/overview?benchmark=mmlu"]}>
        <Routes>
          <Route path="/" element={<AppLayout />}>
            <Route path="overview" element={<div data-testid="outlet-content">overview</div>} />
          </Route>
        </Routes>
      </MemoryRouter>,
    );

    expect(screen.getByTestId("filter-bar-mock")).toBeInTheDocument();
    expect(screen.getByTestId("outlet-content")).toBeInTheDocument();
    expect(screen.getByTestId("agent-chat-filter-value")).toHaveTextContent("mmlu");
  });
});
