import { fireEvent, render, screen } from "@testing-library/react";
import { jest } from "@jest/globals";

const hookState = {
  messages: [] as Array<{ role: string }>,
  conversationId: null as string | null,
  isOpen: false,
  setIsOpen: jest.fn(),
  isConnected: true,
  send: jest.fn(),
  startNewConversation: jest.fn(),
  resumeConversation: jest.fn(),
  isResumingConversation: false,
  pendingAction: null,
  clearPendingAction: jest.fn(),
};

const listState = {
  data: [] as Array<{
    conversation_id: string;
    last_message?: string | null;
    updated_at: string;
  }>,
  isLoading: false,
};

jest.unstable_mockModule("antd", () => ({
  Badge: ({ children }: { children: React.ReactNode }) => <div data-testid="badge">{children}</div>,
  Drawer: ({ open, children, title }: { open: boolean; children: React.ReactNode; title: React.ReactNode }) =>
    open ? (
      <div>
        <div>{title}</div>
        {children}
      </div>
    ) : null,
  FloatButton: ({ onClick, tooltip, "aria-label": ariaLabel }: { onClick?: () => void; tooltip?: string; "aria-label"?: string }) => (
    <button type="button" onClick={onClick} aria-label={ariaLabel ?? tooltip}>
      {tooltip}
    </button>
  ),
}));

jest.unstable_mockModule("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => {
      const map: Record<string, string> = {
        "chat.open": "Open Agent Chat",
        "chat.title": "Agent Chat",
        "chat.connected": "Connected",
        "chat.disconnected": "Disconnected",
        "chat.recentConversations": "Recent Conversations",
        "chat.newConversation": "New Conversation",
        "chat.noConversations": "No conversations yet",
        "chat.loadingConversations": "Loading conversations...",
      };
      return map[key] ?? key;
    },
  }),
}));

jest.unstable_mockModule("../../hooks/useAgentChat", () => ({
  useAgentChat: () => hookState,
}));

jest.unstable_mockModule("../../api/queries/agent", () => ({
  useAgentConversations: () => listState,
}));

jest.unstable_mockModule("./MessageList", () => ({
  MessageList: () => <div data-testid="message-list">messages</div>,
}));

jest.unstable_mockModule("./MessageInput", () => ({
  MessageInput: () => <input placeholder="Ask a question" />,
}));

jest.unstable_mockModule("./ChatActionRouter", () => ({
  ChatActionRouter: () => null,
}));

const { AgentChatWindow } = await import("./index");

describe("AgentChatWindow", () => {
  beforeEach(() => {
    hookState.messages = [];
    hookState.conversationId = null;
    hookState.isOpen = false;
    listState.data = [];
    listState.isLoading = false;
    jest.clearAllMocks();
  });

  it("renders a floating trigger button when closed", () => {
    render(<AgentChatWindow />);
    expect(screen.getByRole("button", { name: "Open Agent Chat" })).toBeInTheDocument();
  });

  it("clicking the trigger button opens the chat panel", () => {
    render(<AgentChatWindow />);
    fireEvent.click(screen.getByRole("button", { name: "Open Agent Chat" }));
    expect(hookState.setIsOpen).toHaveBeenCalledWith(true);
  });

  it("renders the chat content when open", () => {
    hookState.isOpen = true;
    render(<AgentChatWindow />);
    expect(screen.getByText(/Agent Chat/)).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Ask a question")).toBeInTheDocument();
  });

  it("shows recent conversations and resumes a selected one", () => {
    hookState.isOpen = true;
    listState.data = [
      {
        conversation_id: "conv-1",
        last_message: "Show summary",
        updated_at: "2026-03-23T00:00:00Z",
      },
    ];

    render(<AgentChatWindow />);

    fireEvent.click(screen.getByRole("button", { name: /Show summary/i }));
    expect(hookState.resumeConversation).toHaveBeenCalledWith("conv-1");
  });

  it("starts a new conversation from the drawer action", () => {
    hookState.isOpen = true;

    render(<AgentChatWindow />);

    fireEvent.click(screen.getByRole("button", { name: /New Conversation/i }));
    expect(hookState.startNewConversation).toHaveBeenCalledTimes(1);
  });
});
