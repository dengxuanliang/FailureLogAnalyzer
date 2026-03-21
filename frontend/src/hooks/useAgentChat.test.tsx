import { act, renderHook } from "@testing-library/react";
import { jest } from "@jest/globals";
import type { ActionPayload, ChatMessage } from "../types/agent";

const mockSocketSend = jest.fn<(_payload: unknown) => boolean>();
const mockDisconnect = jest.fn();
const mockMutate: any = jest.fn();
let socketHandlers: {
  onToken: (token: string) => void;
  onMessage: (message: ChatMessage) => void;
  onAction: (action: ActionPayload) => void;
  onConnected: () => void;
  onDisconnected: () => void;
  onConversationId?: (conversationId: string) => void;
};

jest.unstable_mockModule("./useAgentWebSocket", () => ({
  useAgentWebSocket: (_url: string, handlers: typeof socketHandlers) => {
    socketHandlers = handlers;
    return {
      send: mockSocketSend,
      disconnect: mockDisconnect,
    };
  },
}));

jest.unstable_mockModule("./useGlobalFilters", () => ({
  useGlobalFilters: () => ({
    benchmark: "mmlu",
    model_version: "v1.0",
    time_range_start: "2026-03-01",
    time_range_end: "2026-03-31",
    setFilter: jest.fn(),
    resetFilters: jest.fn(),
  }),
}));

jest.unstable_mockModule("../api/queries/agent", () => ({
  useAgentChatMutation: () => ({
    mutate: mockMutate,
  }),
}));

const { AgentChatProvider } = await import("../contexts/AgentChatContext");
const { useAgentChat } = await import("./useAgentChat");

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <AgentChatProvider>{children}</AgentChatProvider>
);

describe("useAgentChat", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockSocketSend.mockReturnValue(true);
  });

  it("send() appends a user message and a streaming placeholder, then sends websocket payload with filters", () => {
    const { result } = renderHook(() => useAgentChat(), { wrapper });

    act(() => {
      result.current.send("hello agent");
    });

    expect(result.current.messages).toHaveLength(2);
    expect(result.current.messages[0]).toMatchObject({ role: "user", content: "hello agent" });
    expect(result.current.messages[1]).toMatchObject({ role: "assistant", content: "", isStreaming: true });
    expect(mockSocketSend).toHaveBeenCalledWith({
      message: "hello agent",
      conversation_id: null,
      filters: {
        benchmark: "mmlu",
        model_version: "v1.0",
        time_range_start: "2026-03-01",
        time_range_end: "2026-03-31",
      },
    });
  });

  it("streams websocket tokens into the placeholder and finalizes on done", () => {
    const { result } = renderHook(() => useAgentChat(), { wrapper });

    act(() => {
      socketHandlers.onConnected();
      result.current.send("analyze errors");
      socketHandlers.onToken("Hello");
      socketHandlers.onToken(" world");
      socketHandlers.onToken("\u0000");
    });

    expect(result.current.isConnected).toBe(true);
    expect(result.current.messages[1]).toMatchObject({
      role: "assistant",
      content: "Hello world",
      isStreaming: false,
    });
  });

  it("stores pending actions and clears them on demand", () => {
    const { result } = renderHook(() => useAgentChat(), { wrapper });

    act(() => {
      socketHandlers.onAction({ type: "navigate", page: "compare" });
    });

    expect(result.current.pendingAction).toEqual({ type: "navigate", page: "compare" });

    act(() => {
      result.current.clearPendingAction();
    });

    expect(result.current.pendingAction).toBeNull();
  });

  it("falls back to the REST mutation when websocket send is unavailable", () => {
    mockSocketSend.mockReturnValue(false);
    mockMutate.mockImplementation(
      ((
        _payload: unknown,
        options: {
          onSuccess?: (data: {
            conversation_id: string;
            reply: string;
            messages: ChatMessage[];
            action?: ActionPayload;
          }) => void;
        },
      ) => {
        options.onSuccess?.({
          conversation_id: "conv-rest",
          reply: "Fallback reply",
          messages: [
            {
              id: "assistant-final",
              role: "assistant",
              content: "Fallback reply",
              timestamp: "2026-03-21T00:00:00Z",
            },
          ],
          action: { type: "navigate", page: "analysis" },
        });
      }) as any,
    );

    const { result } = renderHook(() => useAgentChat(), { wrapper });

    act(() => {
      result.current.send("fallback please");
    });

    expect(mockMutate).toHaveBeenCalledTimes(1);
    expect(result.current.conversationId).toBe("conv-rest");
    const lastMessage = result.current.messages[result.current.messages.length - 1];
    expect(lastMessage).toMatchObject({
      role: "assistant",
      content: "Fallback reply",
      isStreaming: false,
    });
    expect(result.current.pendingAction).toEqual({ type: "navigate", page: "analysis" });
  });
});
