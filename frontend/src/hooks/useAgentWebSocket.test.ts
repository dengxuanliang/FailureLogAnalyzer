import { act, renderHook } from "@testing-library/react";
import { jest } from "@jest/globals";
import type { ActionPayload, ChatMessage } from "@/types/agent";
import { useAgentWebSocket } from "./useAgentWebSocket";

class MockWebSocket {
  static OPEN = 1;
  static CLOSED = 3;
  readyState = MockWebSocket.OPEN;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  sent: string[] = [];

  send(data: string) {
    this.sent.push(data);
  }

  close() {
    this.readyState = MockWebSocket.CLOSED;
  }
}

describe("useAgentWebSocket", () => {
  let mockWs: MockWebSocket;

  beforeEach(() => {
    mockWs = new MockWebSocket();
    Object.defineProperty(globalThis, "WebSocket", {
      writable: true,
      value: Object.assign(jest.fn(() => mockWs), { OPEN: MockWebSocket.OPEN }),
    });
  });

  it("connects on mount and notifies when connected", () => {
    const handlers = {
      onToken: jest.fn(),
      onMessage: jest.fn(),
      onAction: jest.fn(),
      onConnected: jest.fn(),
      onDisconnected: jest.fn(),
    };

    renderHook(() => useAgentWebSocket("ws://localhost/ws", handlers));

    act(() => {
      mockWs.onopen?.();
    });

    expect(handlers.onConnected).toHaveBeenCalledTimes(1);
  });

  it("send() serializes payloads to the websocket", () => {
    const handlers = {
      onToken: jest.fn(),
      onMessage: jest.fn(),
      onAction: jest.fn(),
      onConnected: jest.fn(),
      onDisconnected: jest.fn(),
    };

    const { result } = renderHook(() => useAgentWebSocket("ws://localhost/ws", handlers));

    act(() => {
      mockWs.onopen?.();
      result.current.send({ message: "hello", conversation_id: null });
    });

    expect(mockWs.sent).toHaveLength(1);
    expect(JSON.parse(mockWs.sent[0])).toMatchObject({ message: "hello", conversation_id: null });
  });

  it("dispatches server token, message, action, and disconnect events", () => {
    const onToken = jest.fn();
    const onMessage = jest.fn();
    const onAction = jest.fn();
    const onConversationId = jest.fn();
    const onDisconnected = jest.fn();
    const handlers = {
      onToken,
      onMessage,
      onAction,
      onConnected: jest.fn(),
      onDisconnected,
      onConversationId,
    };
    const message: ChatMessage = {
      id: "msg-1",
      role: "assistant",
      content: "Done",
      timestamp: "2026-03-21T00:00:00Z",
    };
    const action: ActionPayload = { type: "navigate", page: "compare" };

    renderHook(() => useAgentWebSocket("ws://localhost/ws", handlers));

    act(() => {
      mockWs.onmessage?.({ data: JSON.stringify({ type: "token", token: "hel" }) } as MessageEvent);
      mockWs.onmessage?.({ data: JSON.stringify({ type: "message", message }) } as MessageEvent);
      mockWs.onmessage?.({ data: JSON.stringify({ type: "action", action }) } as MessageEvent);
      mockWs.onclose?.();
    });

    expect(onToken).toHaveBeenCalledWith("hel");
    expect(onMessage).toHaveBeenCalledWith(message);
    expect(onAction).toHaveBeenCalledWith(action);
    expect(onDisconnected).toHaveBeenCalledTimes(1);
  });

  it("accepts the legacy backend envelope with data.messages and conversation_id", () => {
    const onMessage = jest.fn();
    const onConversationId = jest.fn();
    const handlers = {
      onToken: jest.fn(),
      onMessage,
      onAction: jest.fn(),
      onConnected: jest.fn(),
      onDisconnected: jest.fn(),
      onConversationId,
    };

    renderHook(() => useAgentWebSocket("ws://localhost/ws", handlers));

    act(() => {
      mockWs.onmessage?.(
        {
          data: JSON.stringify({
            type: "message",
            data: {
              conversation_id: "conv-legacy",
              messages: [
                { role: "user", content: "show compare" },
                {
                  id: "assistant-1",
                  role: "assistant",
                  content: "Opening compare view.",
                  timestamp: "2026-03-21T00:00:00Z",
                },
              ],
            },
          }),
        } as MessageEvent,
      );
    });

    expect(onConversationId).toHaveBeenCalledWith("conv-legacy");
    expect(onMessage).toHaveBeenCalledWith(
      expect.objectContaining({
        id: "assistant-1",
        role: "assistant",
        content: "Opening compare view.",
      }),
    );
  });
});
