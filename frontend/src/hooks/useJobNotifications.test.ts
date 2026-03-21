import { act, renderHook } from "@testing-library/react";
import { jest } from "@jest/globals";

const mockNotification = {
  success: jest.fn(),
  error: jest.fn(),
};

jest.unstable_mockModule("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string, options?: Record<string, unknown>) => `${key}:${JSON.stringify(options ?? {})}`,
  }),
}));

jest.unstable_mockModule("antd", () => {
  const actual = jest.requireActual("antd") as typeof import("antd");
  return {
    ...actual,
    App: {
      ...actual.App,
      useApp: () => ({ notification: mockNotification }),
    },
  };
});

class MockWebSocket {
  static readonly OPEN = 1;
  readyState = MockWebSocket.OPEN;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  send = jest.fn();
  close = jest.fn();
}

const { useJobNotifications: useJobNotificationsHook } = await import("./useJobNotifications");

describe("useJobNotifications", () => {
  let socket: MockWebSocket;

  beforeEach(() => {
    jest.clearAllMocks();
    socket = new MockWebSocket();
    Object.defineProperty(globalThis, "WebSocket", {
      writable: true,
      value: Object.assign(jest.fn(() => socket), {
        OPEN: MockWebSocket.OPEN,
      }),
    });
  });

  it("fires success notification when ingest job completes", () => {
    renderHook(() => useJobNotificationsHook("job-123", "ingest"));

    act(() => {
      socket.onmessage?.({
        data: JSON.stringify({ status: "done", processed: 500, job_id: "job-123" }),
      } as MessageEvent);
    });

    expect(mockNotification.success).toHaveBeenCalledTimes(1);
  });

  it("fires error notification when llm job fails", () => {
    renderHook(() => useJobNotificationsHook("job-456", "llm"));

    act(() => {
      socket.onmessage?.({
        data: JSON.stringify({ status: "failed", error: "adapter missing", job_id: "job-456" }),
      } as MessageEvent);
    });

    expect(mockNotification.error).toHaveBeenCalledTimes(1);
  });

  it("closes websocket on unmount", () => {
    const { unmount } = renderHook(() => useJobNotificationsHook("job-789", "ingest"));

    unmount();

    expect(socket.close).toHaveBeenCalledTimes(1);
  });
});
