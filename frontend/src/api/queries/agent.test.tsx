import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { jest } from "@jest/globals";
import type { ReactNode } from "react";

const apiClientMock: any = {
  get: jest.fn(),
  post: jest.fn(),
};

await jest.unstable_mockModule("../client", () => ({
  __esModule: true,
  default: apiClientMock,
}));

const {
  useAgentChatMutation,
  useAgentConversation,
  useAgentConversations,
} = await import("./agent");

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe("agent query hooks", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("fetches conversation list", async () => {
    apiClientMock.get.mockResolvedValueOnce({
      data: [
        {
          conversation_id: "conv-1",
          last_message: "Show summary",
          intent: "query",
          current_step: "query_done",
          updated_at: "2026-03-23T00:00:00Z",
        },
      ],
    });

    const { result } = renderHook(() => useAgentConversations(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(apiClientMock.get).toHaveBeenCalledWith("/agent/conversations");
    expect(result.current.data?.[0]?.conversation_id).toBe("conv-1");
  });

  it("fetches one conversation history by id", async () => {
    apiClientMock.get.mockResolvedValueOnce({
      data: {
        conversation_id: "conv-1",
        messages: [
          {
            id: "msg-1",
            role: "user",
            content: "Show summary",
            timestamp: "2026-03-23T00:00:00Z",
          },
          {
            id: "msg-2",
            role: "assistant",
            content: "Here is the summary.",
            timestamp: "2026-03-23T00:00:01Z",
          },
        ],
        reply: "Here is the summary.",
        current_step: "query_done",
        intent: "query",
        needs_human_input: false,
      },
    });

    const { result } = renderHook(() => useAgentConversation("conv-1"), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(apiClientMock.get).toHaveBeenCalledWith("/agent/conversations/conv-1");
    expect(result.current.data?.messages).toHaveLength(2);
  });

  it("posts chat messages", async () => {
    apiClientMock.post.mockResolvedValueOnce({
      data: {
        conversation_id: "conv-1",
        messages: [],
        reply: "ok",
        current_step: "query_done",
        intent: "query",
        needs_human_input: false,
      },
    });

    const { result } = renderHook(() => useAgentChatMutation(), { wrapper: createWrapper() });

    await act(async () => {
      await result.current.mutateAsync({
        message: "hello",
        conversation_id: "conv-1",
      });
    });

    expect(apiClientMock.post).toHaveBeenCalledWith("/agent/chat", {
      message: "hello",
      conversation_id: "conv-1",
    });
  });
});
