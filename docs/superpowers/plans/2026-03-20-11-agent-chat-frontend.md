# Agent Chat Window Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the Agent 对话窗口 (§9.7) — a floating, collapsible chat panel fixed to the bottom-right corner of every Dashboard page. The window connects to `WS /api/v1/ws/agent`, renders a streaming conversation with the Orchestrator Agent, and **bi-directionally links** with the Dashboard: natural-language replies can trigger page navigation, filter changes, and record highlights, while Dashboard interactions (upload, analyze button, filter change) send structured messages into the chat thread.

**Architecture:** A single `AgentChatWindow` component mounts inside `AppLayout` and is always present regardless of current page. Conversation state lives in a dedicated `AgentChatContext` (persists `conversation_id` for the session). WebSocket connection is managed by a custom `useAgentWebSocket` hook that auto-reconnects and writes streamed tokens into the context. A `ChatActionRouter` interprets structured `action` payloads in agent replies and dispatches navigation/filter/highlight side-effects. Dashboard components that trigger agent actions (Upload, Analyze button, LLM Judge button) call `useAgentChat().send(message)` instead of direct API calls, so the action appears in the chat thread.

**Tech Stack:** React 18, TypeScript 5, Ant Design 5 (Drawer / Badge / Input / Button), TanStack Query v5, React Router v6, native browser `WebSocket`, Jest + React Testing Library

**Prerequisites:** Plans 07–10 complete (layout, pages, global filter context).
Plan 06 complete (backend `WS /api/v1/ws/agent`, `POST /api/v1/agent/chat` endpoints).

---

## File Structure After This Plan

```
frontend/src/
  api/
    queries/
      agent.ts               # useAgentChat REST fallback hook (TanStack Query mutation)
  components/
    AgentChatWindow/
      index.tsx              # Root component: floating button + Drawer/panel
      AgentChatWindow.test.tsx
      MessageList.tsx        # Virtualized message bubble list
      MessageList.test.tsx
      MessageInput.tsx       # Textarea + Send button
      MessageInput.test.tsx
      TypingIndicator.tsx    # Animated dots while agent streams
      TypingIndicator.test.tsx
      ChatActionRouter.tsx   # Interprets action payloads → navigate/filter/highlight
      ChatActionRouter.test.tsx
  contexts/
    AgentChatContext.tsx     # conversation_id, messages, send(), isConnected
    AgentChatContext.test.tsx
  hooks/
    useAgentWebSocket.ts     # WS lifecycle: connect/reconnect/send/receive
    useAgentWebSocket.test.ts
    useAgentChat.ts          # Public hook: send message, read state
    useAgentChat.test.ts
  types/
    agent.ts                 # ChatMessage, AgentReply, ActionPayload, ConnectionStatus
```

**Modified files:**
```
frontend/src/
  layouts/AppLayout.tsx      # Mount <AgentChatWindow /> at bottom-right
  pages/Overview/index.tsx   # Analyze button → useAgentChat().send(...)
  locales/zh.json            # Agent chat i18n strings
  locales/en.json
```

---

## Task 1 — TypeScript Types for Agent Chat

**Files:**
- Create: `frontend/src/types/agent.ts`

### Steps

- [ ] **Step 1: Create `frontend/src/types/agent.ts`**

```typescript
// frontend/src/types/agent.ts
// TypeScript types for the Agent Chat Window — matches Plan 06 backend schemas.

/** A single message in the conversation thread. */
export interface ChatMessage {
  id: string;               // local UUID for React key
  role: "user" | "assistant" | "system";
  content: string;          // markdown text
  timestamp: string;        // ISO 8601
  isStreaming?: boolean;    // true while tokens are arriving
  action?: ActionPayload;   // optional structured side-effect
}

/**
 * Structured action payload included in assistant messages.
 * The ChatActionRouter interprets these to drive Dashboard navigation/state.
 */
export type ActionPayload =
  | { type: "navigate"; page: "overview" | "error-analysis" | "version-compare" | "cross-benchmark" | "config" }
  | { type: "set_filter"; key: "benchmark" | "model_version" | "time_range" | "error_type"; value: string }
  | { type: "highlight_record"; record_id: string }
  | { type: "open_session"; session_id: string };

/** Payload sent over WebSocket from client → server. */
export interface WsClientMessage {
  message: string;
  conversation_id: string | null;
  filters?: Record<string, string>;
}

/** Payload received from server → client over WebSocket. */
export interface WsServerMessage {
  type: "token" | "message" | "action" | "error" | "done";
  token?: string;           // type === "token": streaming text chunk
  message?: ChatMessage;    // type === "message": full message
  action?: ActionPayload;   // type === "action": side-effect
  error?: string;           // type === "error"
  conversation_id?: string; // echoed back so client can persist
}

export type ConnectionStatus = "connecting" | "connected" | "disconnected" | "error";
```

- [ ] **Step 2: Verify `frontend/src/types/agent.ts` compiles**
  ```
  cd frontend && npx tsc --noEmit
  ```
  Expected: no type errors.

---

## Task 2 — `AgentChatContext` (conversation state)

**Files:**
- Create: `frontend/src/contexts/AgentChatContext.tsx`
- Create: `frontend/src/contexts/AgentChatContext.test.tsx`

### Steps

- [ ] **Step 1: Write failing test**

```typescript
// frontend/src/contexts/AgentChatContext.test.tsx
import React from "react";
import { render, screen, act } from "@testing-library/react";
import { AgentChatProvider, useAgentChatContext } from "./AgentChatContext";

function TestConsumer() {
  const { messages, conversationId, isOpen, setIsOpen } = useAgentChatContext();
  return (
    <div>
      <span data-testid="msg-count">{messages.length}</span>
      <span data-testid="conv-id">{conversationId ?? "null"}</span>
      <button onClick={() => setIsOpen(true)}>open</button>
      <span data-testid="is-open">{String(isOpen)}</span>
    </div>
  );
}

test("initial state has empty messages and no conversationId", () => {
  render(
    <AgentChatProvider>
      <TestConsumer />
    </AgentChatProvider>
  );
  expect(screen.getByTestId("msg-count").textContent).toBe("0");
  expect(screen.getByTestId("conv-id").textContent).toBe("null");
  expect(screen.getByTestId("is-open").textContent).toBe("false");
});

test("setIsOpen toggles open state", () => {
  render(
    <AgentChatProvider>
      <TestConsumer />
    </AgentChatProvider>
  );
  act(() => {
    screen.getByText("open").click();
  });
  expect(screen.getByTestId("is-open").textContent).toBe("true");
});
```

- [ ] Run: `cd frontend && npx jest AgentChatContext` → **FAILED**

- [ ] **Step 2: Implement `AgentChatContext.tsx`**

```typescript
// frontend/src/contexts/AgentChatContext.tsx
import React, {
  createContext, useContext, useState, useCallback, useRef, ReactNode,
} from "react";
import { v4 as uuidv4 } from "uuid";
import type { ChatMessage, ActionPayload } from "../types/agent";

interface AgentChatContextValue {
  messages: ChatMessage[];
  conversationId: string | null;
  isOpen: boolean;
  isConnected: boolean;
  setIsOpen: (open: boolean) => void;
  setIsConnected: (connected: boolean) => void;
  appendMessage: (msg: ChatMessage) => void;
  appendToken: (token: string) => void;   // append to last streaming message
  finalizeStreaming: () => void;           // mark last message as done streaming
  setConversationId: (id: string) => void;
  clearMessages: () => void;
  pendingAction: ActionPayload | null;
  setPendingAction: (action: ActionPayload | null) => void;
}

const AgentChatContext = createContext<AgentChatContextValue | null>(null);

export function AgentChatProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [pendingAction, setPendingAction] = useState<ActionPayload | null>(null);

  const appendMessage = useCallback((msg: ChatMessage) => {
    setMessages((prev) => [...prev, msg]);
  }, []);

  const appendToken = useCallback((token: string) => {
    setMessages((prev) => {
      if (prev.length === 0) return prev;
      const last = prev[prev.length - 1];
      if (!last.isStreaming) return prev;
      return [
        ...prev.slice(0, -1),
        { ...last, content: last.content + token },
      ];
    });
  }, []);

  const finalizeStreaming = useCallback(() => {
    setMessages((prev) => {
      if (prev.length === 0) return prev;
      const last = prev[prev.length - 1];
      return [...prev.slice(0, -1), { ...last, isStreaming: false }];
    });
  }, []);

  const clearMessages = useCallback(() => setMessages([]), []);

  return (
    <AgentChatContext.Provider
      value={{
        messages,
        conversationId,
        isOpen,
        isConnected,
        setIsOpen,
        setIsConnected,
        appendMessage,
        appendToken,
        finalizeStreaming,
        setConversationId,
        clearMessages,
        pendingAction,
        setPendingAction,
      }}
    >
      {children}
    </AgentChatContext.Provider>
  );
}

export function useAgentChatContext(): AgentChatContextValue {
  const ctx = useContext(AgentChatContext);
  if (!ctx) throw new Error("useAgentChatContext must be used within AgentChatProvider");
  return ctx;
}
```

- [ ] Run: `npx jest AgentChatContext` → **PASSED** (2 tests)

---

## Task 3 — `useAgentWebSocket` hook

**Files:**
- Create: `frontend/src/hooks/useAgentWebSocket.ts`
- Create: `frontend/src/hooks/useAgentWebSocket.test.ts`

### Steps

- [ ] **Step 1: Write failing test**

```typescript
// frontend/src/hooks/useAgentWebSocket.test.ts
import { renderHook, act } from "@testing-library/react";
import { useAgentWebSocket } from "./useAgentWebSocket";

// Mock WebSocket
class MockWebSocket {
  static OPEN = 1;
  static CLOSED = 3;
  readyState = MockWebSocket.OPEN;
  onmessage: ((e: MessageEvent) => void) | null = null;
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: ((e: Event) => void) | null = null;
  sent: string[] = [];
  send(data: string) { this.sent.push(data); }
  close() { this.readyState = MockWebSocket.CLOSED; }
}

let mockWs: MockWebSocket;
beforeEach(() => {
  mockWs = new MockWebSocket();
  (global as any).WebSocket = jest.fn(() => mockWs);
});

test("connects on mount and sets status to connected", () => {
  const handlers = {
    onToken: jest.fn(),
    onMessage: jest.fn(),
    onAction: jest.fn(),
    onConnected: jest.fn(),
    onDisconnected: jest.fn(),
  };
  renderHook(() => useAgentWebSocket("ws://localhost/ws", handlers));
  act(() => { mockWs.onopen?.(); });
  expect(handlers.onConnected).toHaveBeenCalledTimes(1);
});

test("send() serializes and calls ws.send()", () => {
  const handlers = { onToken: jest.fn(), onMessage: jest.fn(), onAction: jest.fn(), onConnected: jest.fn(), onDisconnected: jest.fn() };
  const { result } = renderHook(() => useAgentWebSocket("ws://localhost/ws", handlers));
  act(() => { mockWs.onopen?.(); });
  act(() => {
    result.current.send({ message: "hello", conversation_id: null });
  });
  expect(mockWs.sent).toHaveLength(1);
  expect(JSON.parse(mockWs.sent[0]).message).toBe("hello");
});

test("dispatches onToken when type=token message arrives", () => {
  const handlers = { onToken: jest.fn(), onMessage: jest.fn(), onAction: jest.fn(), onConnected: jest.fn(), onDisconnected: jest.fn() };
  renderHook(() => useAgentWebSocket("ws://localhost/ws", handlers));
  act(() => { mockWs.onopen?.(); });
  act(() => {
    mockWs.onmessage?.({ data: JSON.stringify({ type: "token", token: "hello" }) } as MessageEvent);
  });
  expect(handlers.onToken).toHaveBeenCalledWith("hello");
});
```

- [ ] Run: `npx jest useAgentWebSocket` → **FAILED**

- [ ] **Step 2: Implement `useAgentWebSocket.ts`**

```typescript
// frontend/src/hooks/useAgentWebSocket.ts
import { useEffect, useRef, useCallback } from "react";
import type { WsClientMessage, WsServerMessage, ActionPayload, ChatMessage } from "../types/agent";

export interface WebSocketHandlers {
  onToken: (token: string) => void;
  onMessage: (msg: ChatMessage) => void;
  onAction: (action: ActionPayload) => void;
  onConnected: () => void;
  onDisconnected: () => void;
}

export interface UseAgentWebSocketReturn {
  send: (payload: WsClientMessage) => void;
  disconnect: () => void;
}

export function useAgentWebSocket(
  url: string,
  handlers: WebSocketHandlers,
): UseAgentWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const handlersRef = useRef(handlers);
  handlersRef.current = handlers;  // always up-to-date without re-subscribing

  useEffect(() => {
    let ws: WebSocket;
    let reconnectTimer: ReturnType<typeof setTimeout>;

    function connect() {
      ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        handlersRef.current.onConnected();
      };

      ws.onmessage = (event: MessageEvent) => {
        let msg: WsServerMessage;
        try {
          msg = JSON.parse(event.data as string);
        } catch {
          return;
        }
        switch (msg.type) {
          case "token":
            if (msg.token) handlersRef.current.onToken(msg.token);
            break;
          case "message":
            if (msg.message) handlersRef.current.onMessage(msg.message);
            break;
          case "action":
            if (msg.action) handlersRef.current.onAction(msg.action);
            break;
          case "error":
            console.error("[AgentWS] error:", msg.error);
            break;
          case "done":
            // streaming complete — caller finalizes
            handlersRef.current.onToken("\x00");  // sentinel: empty token signals done
            break;
        }
      };

      ws.onclose = () => {
        handlersRef.current.onDisconnected();
        // Auto-reconnect after 3 s
        reconnectTimer = setTimeout(connect, 3000);
      };

      ws.onerror = () => {
        ws.close();
      };
    }

    connect();

    return () => {
      clearTimeout(reconnectTimer);
      ws.onclose = null;  // prevent reconnect on intentional unmount
      ws.close();
    };
  }, [url]);

  const send = useCallback((payload: WsClientMessage) => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(payload));
    }
  }, []);

  const disconnect = useCallback(() => {
    wsRef.current?.close();
  }, []);

  return { send, disconnect };
}
```

- [ ] Run: `npx jest useAgentWebSocket` → **PASSED** (3 tests)

---

## Task 4 — `useAgentChat` public hook

**Files:**
- Create: `frontend/src/hooks/useAgentChat.ts`
- Create: `frontend/src/hooks/useAgentChat.test.ts`

### Steps

- [ ] **Step 1: Write failing test**

```typescript
// frontend/src/hooks/useAgentChat.test.ts
import { renderHook, act } from "@testing-library/react";
import React from "react";
import { AgentChatProvider } from "../contexts/AgentChatContext";
import { useAgentChat } from "./useAgentChat";
import { useGlobalFilters } from "./useGlobalFilters";

jest.mock("./useGlobalFilters", () => ({
  useGlobalFilters: () => ({ benchmark: "mmlu", model_version: "v1", time_range: "7d" }),
}));

// Suppress WebSocket connection attempt
beforeEach(() => {
  (global as any).WebSocket = jest.fn().mockImplementation(() => ({
    readyState: 1,
    send: jest.fn(),
    close: jest.fn(),
    onopen: null,
    onmessage: null,
    onclose: null,
    onerror: null,
  }));
});

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <AgentChatProvider>{children}</AgentChatProvider>
);

test("send() appends a user message to context immediately", () => {
  const { result } = renderHook(() => useAgentChat(), { wrapper });
  act(() => { result.current.send("hello agent"); });
  expect(result.current.messages).toHaveLength(1);
  expect(result.current.messages[0].role).toBe("user");
  expect(result.current.messages[0].content).toBe("hello agent");
});

test("send() also appends a placeholder streaming assistant message", () => {
  const { result } = renderHook(() => useAgentChat(), { wrapper });
  act(() => { result.current.send("analyze errors"); });
  expect(result.current.messages).toHaveLength(2);
  expect(result.current.messages[1].role).toBe("assistant");
  expect(result.current.messages[1].isStreaming).toBe(true);
});
```

- [ ] Run: `npx jest useAgentChat` → **FAILED**

- [ ] **Step 2: Implement `useAgentChat.ts`**

```typescript
// frontend/src/hooks/useAgentChat.ts
import { useCallback, useEffect } from "react";
import { v4 as uuidv4 } from "uuid";
import { useAgentChatContext } from "../contexts/AgentChatContext";
import { useAgentWebSocket } from "./useAgentWebSocket";
import { useGlobalFilters } from "./useGlobalFilters";
import type { ChatMessage, ActionPayload } from "../types/agent";

const WS_URL = `${(import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1")
  .replace(/^http/, "ws")}/ws/agent`;

export interface UseAgentChatReturn {
  messages: ChatMessage[];
  conversationId: string | null;
  isConnected: boolean;
  isOpen: boolean;
  setIsOpen: (open: boolean) => void;
  send: (text: string) => void;
  pendingAction: ActionPayload | null;
  clearPendingAction: () => void;
}

export function useAgentChat(): UseAgentChatReturn {
  const {
    messages,
    conversationId,
    isOpen,
    isConnected,
    setIsOpen,
    setIsConnected,
    appendMessage,
    appendToken,
    finalizeStreaming,
    setConversationId,
    pendingAction,
    setPendingAction,
  } = useAgentChatContext();

  const filters = useGlobalFilters();

  const { send: wsSend } = useAgentWebSocket(WS_URL, {
    onConnected: () => setIsConnected(true),
    onDisconnected: () => setIsConnected(false),
    onToken: (token) => {
      if (token === "\x00") {
        finalizeStreaming();
      } else {
        appendToken(token);
      }
    },
    onMessage: (msg) => {
      // Replace placeholder streaming message with final message
      finalizeStreaming();
      appendMessage(msg);
    },
    onAction: (action) => {
      setPendingAction(action);
    },
  });

  const send = useCallback(
    (text: string) => {
      const userMsg: ChatMessage = {
        id: uuidv4(),
        role: "user",
        content: text,
        timestamp: new Date().toISOString(),
      };
      appendMessage(userMsg);

      // Placeholder for streaming assistant reply
      const placeholderMsg: ChatMessage = {
        id: uuidv4(),
        role: "assistant",
        content: "",
        timestamp: new Date().toISOString(),
        isStreaming: true,
      };
      appendMessage(placeholderMsg);

      wsSend({
        message: text,
        conversation_id: conversationId,
        filters: {
          benchmark: filters.benchmark ?? "",
          model_version: filters.model_version ?? "",
          time_range: filters.time_range ?? "",
        },
      });
    },
    [appendMessage, conversationId, filters, wsSend],
  );

  const clearPendingAction = useCallback(
    () => setPendingAction(null),
    [setPendingAction],
  );

  return {
    messages,
    conversationId,
    isConnected,
    isOpen,
    setIsOpen,
    send,
    pendingAction,
    clearPendingAction,
  };
}
```

- [ ] Run: `npx jest useAgentChat` → **PASSED** (2 tests)
- [ ] Commit: `git commit -m "feat(chat): add AgentChatContext + useAgentWebSocket + useAgentChat hooks"`

---

## Task 5 — `ChatActionRouter` (Dashboard linkage)

**Files:**
- Create: `frontend/src/components/AgentChatWindow/ChatActionRouter.tsx`
- Create: `frontend/src/components/AgentChatWindow/ChatActionRouter.test.tsx`

### Steps

- [ ] **Step 1: Write failing test**

```typescript
// frontend/src/components/AgentChatWindow/ChatActionRouter.test.tsx
import React from "react";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { ChatActionRouter } from "./ChatActionRouter";
import { AgentChatProvider } from "../../contexts/AgentChatContext";
import { FilterContext } from "../../contexts/FilterContext";

const mockNavigate = jest.fn();
jest.mock("react-router-dom", () => ({
  ...jest.requireActual("react-router-dom"),
  useNavigate: () => mockNavigate,
}));

const mockSetFilter = jest.fn();
const filterCtxValue = {
  filters: { benchmark: "", model_version: "", time_range: "7d", error_type: "" },
  setFilter: mockSetFilter,
};

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <MemoryRouter>
      <FilterContext.Provider value={filterCtxValue as any}>
        <AgentChatProvider>{children}</AgentChatProvider>
      </FilterContext.Provider>
    </MemoryRouter>
  );
}

test("navigate action calls useNavigate with correct path", () => {
  const { rerender } = render(
    <ChatActionRouter action={{ type: "navigate", page: "error-analysis" }} />,
    { wrapper: Wrapper }
  );
  expect(mockNavigate).toHaveBeenCalledWith("/error-analysis");
});

test("set_filter action calls setFilter with correct key/value", () => {
  render(
    <ChatActionRouter action={{ type: "set_filter", key: "benchmark", value: "mmlu" }} />,
    { wrapper: Wrapper }
  );
  expect(mockSetFilter).toHaveBeenCalledWith("benchmark", "mmlu");
});

test("null action renders nothing", () => {
  const { container } = render(<ChatActionRouter action={null} />, { wrapper: Wrapper });
  expect(container.firstChild).toBeNull();
});
```

- [ ] Run: `npx jest ChatActionRouter` → **FAILED**

- [ ] **Step 2: Implement `ChatActionRouter.tsx`**

```typescript
// frontend/src/components/AgentChatWindow/ChatActionRouter.tsx
/**
 * Interprets structured ActionPayload from agent replies and applies side-effects:
 * - navigate: push to React Router
 * - set_filter: update global FilterContext
 * - highlight_record: dispatch custom DOM event for record pages to handle
 * - open_session: navigate to overview with session pre-selected
 *
 * Renders nothing (null). Mount wherever pendingAction is consumed.
 */
import { useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useGlobalFilters } from "../../hooks/useGlobalFilters";
import type { ActionPayload } from "../../types/agent";

const PAGE_ROUTES: Record<string, string> = {
  overview: "/",
  "error-analysis": "/error-analysis",
  "version-compare": "/version-compare",
  "cross-benchmark": "/cross-benchmark",
  config: "/config",
};

interface Props {
  action: ActionPayload | null;
}

export function ChatActionRouter({ action }: Props): null {
  const navigate = useNavigate();
  const { setFilter } = useGlobalFilters();

  useEffect(() => {
    if (!action) return;

    switch (action.type) {
      case "navigate": {
        const path = PAGE_ROUTES[action.page];
        if (path) navigate(path);
        break;
      }
      case "set_filter": {
        setFilter(action.key, action.value);
        break;
      }
      case "highlight_record": {
        window.dispatchEvent(
          new CustomEvent("agent:highlight_record", { detail: { record_id: action.record_id } }),
        );
        break;
      }
      case "open_session": {
        setFilter("session_id" as any, action.session_id);
        navigate("/");
        break;
      }
    }
  }, [action, navigate, setFilter]);

  return null;
}
```

- [ ] Run: `npx jest ChatActionRouter` → **PASSED** (3 tests)

---

## Task 6 — Message UI Components

**Files:**
- Create: `frontend/src/components/AgentChatWindow/TypingIndicator.tsx`
- Create: `frontend/src/components/AgentChatWindow/TypingIndicator.test.tsx`
- Create: `frontend/src/components/AgentChatWindow/MessageList.tsx`
- Create: `frontend/src/components/AgentChatWindow/MessageList.test.tsx`
- Create: `frontend/src/components/AgentChatWindow/MessageInput.tsx`
- Create: `frontend/src/components/AgentChatWindow/MessageInput.test.tsx`

### Steps

- [ ] **Step 1: Write failing tests**

```typescript
// frontend/src/components/AgentChatWindow/TypingIndicator.test.tsx
import React from "react";
import { render, screen } from "@testing-library/react";
import { TypingIndicator } from "./TypingIndicator";

test("renders three animated dots", () => {
  render(<TypingIndicator />);
  const dots = document.querySelectorAll(".typing-dot");
  expect(dots).toHaveLength(3);
});
```

```typescript
// frontend/src/components/AgentChatWindow/MessageList.test.tsx
import React from "react";
import { render, screen } from "@testing-library/react";
import { MessageList } from "./MessageList";
import type { ChatMessage } from "../../types/agent";

const messages: ChatMessage[] = [
  { id: "1", role: "user", content: "Hello", timestamp: "2026-03-20T00:00:00Z" },
  { id: "2", role: "assistant", content: "Hi there!", timestamp: "2026-03-20T00:00:01Z" },
];

test("renders all messages", () => {
  render(<MessageList messages={messages} />);
  expect(screen.getByText("Hello")).toBeInTheDocument();
  expect(screen.getByText("Hi there!")).toBeInTheDocument();
});

test("shows TypingIndicator for streaming message", () => {
  const streaming: ChatMessage[] = [
    ...messages,
    { id: "3", role: "assistant", content: "", timestamp: "2026-03-20T00:00:02Z", isStreaming: true },
  ];
  render(<MessageList messages={streaming} />);
  expect(document.querySelectorAll(".typing-dot")).toHaveLength(3);
});
```

```typescript
// frontend/src/components/AgentChatWindow/MessageInput.test.tsx
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { MessageInput } from "./MessageInput";

test("calls onSend with input value on button click", () => {
  const onSend = jest.fn();
  render(<MessageInput onSend={onSend} disabled={false} />);
  const input = screen.getByRole("textbox");
  fireEvent.change(input, { target: { value: "test query" } });
  fireEvent.click(screen.getByRole("button", { name: /send/i }));
  expect(onSend).toHaveBeenCalledWith("test query");
});

test("clears input after send", () => {
  const onSend = jest.fn();
  render(<MessageInput onSend={onSend} disabled={false} />);
  const input = screen.getByRole("textbox");
  fireEvent.change(input, { target: { value: "hello" } });
  fireEvent.click(screen.getByRole("button", { name: /send/i }));
  expect((input as HTMLInputElement).value).toBe("");
});

test("Enter key triggers send", () => {
  const onSend = jest.fn();
  render(<MessageInput onSend={onSend} disabled={false} />);
  const input = screen.getByRole("textbox");
  fireEvent.change(input, { target: { value: "enter test" } });
  fireEvent.keyDown(input, { key: "Enter", code: "Enter" });
  expect(onSend).toHaveBeenCalledWith("enter test");
});
```

- [ ] Run: `npx jest TypingIndicator MessageList MessageInput` → **FAILED** (3 suites)

- [ ] **Step 2: Implement components**

```typescript
// frontend/src/components/AgentChatWindow/TypingIndicator.tsx
import React from "react";

export function TypingIndicator() {
  return (
    <div className="typing-indicator">
      <span className="typing-dot" />
      <span className="typing-dot" />
      <span className="typing-dot" />
    </div>
  );
}
```

```typescript
// frontend/src/components/AgentChatWindow/MessageList.tsx
import React, { useEffect, useRef } from "react";
import { Typography } from "antd";
import type { ChatMessage } from "../../types/agent";
import { TypingIndicator } from "./TypingIndicator";

interface Props {
  messages: ChatMessage[];
}

export function MessageList({ messages }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to latest message
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div style={{ overflowY: "auto", flex: 1, padding: "8px 12px" }}>
      {messages.map((msg) => (
        <div
          key={msg.id}
          style={{
            display: "flex",
            justifyContent: msg.role === "user" ? "flex-end" : "flex-start",
            marginBottom: 8,
          }}
        >
          <div
            style={{
              maxWidth: "80%",
              padding: "8px 12px",
              borderRadius: 12,
              background: msg.role === "user" ? "#1677ff" : "#f0f0f0",
              color: msg.role === "user" ? "#fff" : "#000",
            }}
          >
            {msg.isStreaming && msg.content === "" ? (
              <TypingIndicator />
            ) : (
              <Typography.Text style={{ color: "inherit", whiteSpace: "pre-wrap" }}>
                {msg.content}
              </Typography.Text>
            )}
          </div>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
```

```typescript
// frontend/src/components/AgentChatWindow/MessageInput.tsx
import React, { useState, useCallback, KeyboardEvent } from "react";
import { Input, Button, Space } from "antd";
import { SendOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";

interface Props {
  onSend: (text: string) => void;
  disabled: boolean;
}

export function MessageInput({ onSend, disabled }: Props) {
  const { t } = useTranslation();
  const [value, setValue] = useState("");

  const handleSend = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed) return;
    onSend(trimmed);
    setValue("");
  }, [value, onSend]);

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <Space.Compact style={{ width: "100%", padding: "8px 12px" }}>
      <Input.TextArea
        value={value}
        onChange={(e) => setValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={t("chat.placeholder")}
        autoSize={{ minRows: 1, maxRows: 4 }}
        disabled={disabled}
      />
      <Button
        type="primary"
        icon={<SendOutlined />}
        onClick={handleSend}
        disabled={disabled || !value.trim()}
        aria-label={t("chat.send")}
      >
        {t("chat.send")}
      </Button>
    </Space.Compact>
  );
}
```

- [ ] Run: `npx jest TypingIndicator MessageList MessageInput` → **PASSED** (7 tests total)

---

## Task 7 — `AgentChatWindow` root component

**Files:**
- Create: `frontend/src/components/AgentChatWindow/index.tsx`
- Create: `frontend/src/components/AgentChatWindow/AgentChatWindow.test.tsx`

### Steps

- [ ] **Step 1: Write failing test**

```typescript
// frontend/src/components/AgentChatWindow/AgentChatWindow.test.tsx
import React from "react";
import { render, screen, fireEvent } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { AgentChatWindow } from "./index";
import { AgentChatProvider } from "../../contexts/AgentChatContext";
import { FilterContext } from "../../contexts/FilterContext";

const filterCtxValue = {
  filters: { benchmark: "", model_version: "", time_range: "7d", error_type: "" },
  setFilter: jest.fn(),
};

// Mock WebSocket
beforeEach(() => {
  (global as any).WebSocket = jest.fn().mockImplementation(() => ({
    readyState: 1, send: jest.fn(), close: jest.fn(),
    onopen: null, onmessage: null, onclose: null, onerror: null,
  }));
});

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <MemoryRouter>
      <FilterContext.Provider value={filterCtxValue as any}>
        <AgentChatProvider>{children}</AgentChatProvider>
      </FilterContext.Provider>
    </MemoryRouter>
  );
}

test("renders floating trigger button", () => {
  render(<AgentChatWindow />, { wrapper: Wrapper });
  expect(screen.getByRole("button", { name: /agent|chat|ai/i })).toBeInTheDocument();
});

test("clicking trigger button opens the chat panel", () => {
  render(<AgentChatWindow />, { wrapper: Wrapper });
  fireEvent.click(screen.getByRole("button", { name: /agent|chat|ai/i }));
  expect(screen.getByPlaceholderText(/输入|message|ask/i)).toBeInTheDocument();
});
```

- [ ] Run: `npx jest AgentChatWindow/index` → **FAILED**

- [ ] **Step 2: Implement `AgentChatWindow/index.tsx`**

```typescript
// frontend/src/components/AgentChatWindow/index.tsx
import React from "react";
import { Drawer, Badge, Tooltip, FloatButton } from "antd";
import { MessageOutlined, CloseOutlined } from "@ant-design/icons";
import { useTranslation } from "react-i18next";
import { useAgentChat } from "../../hooks/useAgentChat";
import { MessageList } from "./MessageList";
import { MessageInput } from "./MessageInput";
import { ChatActionRouter } from "./ChatActionRouter";

export function AgentChatWindow() {
  const { t } = useTranslation();
  const {
    messages,
    isOpen,
    setIsOpen,
    isConnected,
    send,
    pendingAction,
    clearPendingAction,
  } = useAgentChat();

  // Consume and execute any pending action
  const handleActionExecuted = () => clearPendingAction();

  const unreadCount = messages.filter(
    (m) => m.role === "assistant" && !isOpen,
  ).length;

  return (
    <>
      {/* Execute side-effects from agent action payloads */}
      <ChatActionRouter action={pendingAction} />

      {/* Floating trigger button — fixed bottom-right */}
      {!isOpen && (
        <Badge count={unreadCount} offset={[-4, 4]}>
          <FloatButton
            icon={<MessageOutlined />}
            tooltip={t("chat.open")}
            onClick={() => setIsOpen(true)}
            style={{ insetInlineEnd: 24, insetBlockEnd: 24 }}
            aria-label={t("chat.open")}
          />
        </Badge>
      )}

      {/* Chat panel as a right-anchored Drawer */}
      <Drawer
        title={
          <span>
            {t("chat.title")}
            <Badge
              status={isConnected ? "success" : "error"}
              text={isConnected ? t("chat.connected") : t("chat.disconnected")}
              style={{ marginLeft: 8, fontSize: 12 }}
            />
          </span>
        }
        placement="right"
        width={380}
        open={isOpen}
        onClose={() => setIsOpen(false)}
        mask={false}           // non-blocking — user can still interact with Dashboard
        styles={{ body: { display: "flex", flexDirection: "column", padding: 0, height: "100%" } }}
      >
        <MessageList messages={messages} />
        <MessageInput onSend={send} disabled={!isConnected} />
      </Drawer>
    </>
  );
}
```

- [ ] Run: `npx jest AgentChatWindow/index` → **PASSED** (2 tests)
- [ ] Commit: `git commit -m "feat(chat): add AgentChatWindow with MessageList, MessageInput, TypingIndicator"`

---

## Task 8 — REST fallback API hook

**Files:**
- Create: `frontend/src/api/queries/agent.ts`

### Steps

- [ ] **Step 1: Create REST fallback for environments without WebSocket support**

```typescript
// frontend/src/api/queries/agent.ts
import { useMutation } from "@tanstack/react-query";
import { apiClient } from "../client";
import type { ChatMessage } from "../../types/agent";

interface ChatRequest {
  message: string;
  conversation_id: string | null;
  filters?: Record<string, string>;
}

interface ChatResponse {
  conversation_id: string;
  reply: string;
  messages: ChatMessage[];
  action?: import("../../types/agent").ActionPayload;
}

/** REST fallback for agent chat (non-streaming). Used when WS unavailable. */
export function useAgentChatMutation() {
  return useMutation<ChatResponse, Error, ChatRequest>({
    mutationFn: (payload) =>
      apiClient.post<ChatResponse>("/agent/chat", payload).then((r) => r.data),
  });
}
```

- [ ] No test required (trivial wrapper, tested via integration).

---

## Task 9 — i18n strings

**Files:**
- Edit: `frontend/src/locales/zh.json`
- Edit: `frontend/src/locales/en.json`

### Steps

- [ ] **Step 1: Add Agent Chat keys to `zh.json`**

```json
{
  "chat": {
    "open": "打开 Agent 对话",
    "title": "Agent 对话",
    "connected": "已连接",
    "disconnected": "未连接",
    "placeholder": "输入问题，例如：分析 mmlu 的错题...",
    "send": "发送",
    "empty": "向 Agent 提问，驱动分析流程"
  }
}
```

- [ ] **Step 2: Add Agent Chat keys to `en.json`**

```json
{
  "chat": {
    "open": "Open Agent Chat",
    "title": "Agent Chat",
    "connected": "Connected",
    "disconnected": "Disconnected",
    "placeholder": "Ask a question, e.g.: Analyze errors in mmlu...",
    "send": "Send",
    "empty": "Ask the Agent to drive analysis"
  }
}
```

---

## Task 10 — Wire into `AppLayout` + add `AgentChatProvider`

**Files:**
- Edit: `frontend/src/layouts/AppLayout.tsx`
- Edit: `frontend/src/App.tsx`

### Steps

- [ ] **Step 1: Wrap root providers in `App.tsx`**

  Add `AgentChatProvider` inside existing providers (after `FilterContextProvider`, before `RouterProvider`):

  ```typescript
  // In App.tsx — add import:
  import { AgentChatProvider } from "./contexts/AgentChatContext";

  // Wrap provider:
  <FilterContextProvider>
    <AgentChatProvider>
      <RouterProvider router={router} />
    </AgentChatProvider>
  </FilterContextProvider>
  ```

- [ ] **Step 2: Mount `<AgentChatWindow />` inside `AppLayout.tsx`**

  ```typescript
  // In AppLayout.tsx — add import:
  import { AgentChatWindow } from "../components/AgentChatWindow";

  // Inside the layout JSX, after <Outlet />:
  <AgentChatWindow />
  ```

- [ ] **Step 3: Write AppLayout test for AgentChatWindow presence**

  ```typescript
  // Add to AppLayout.test.tsx:
  test("renders AgentChatWindow floating button", () => {
    render(<AppLayout />, { wrapper: AllProviders });
    expect(screen.getByRole("button", { name: /agent|chat|ai/i })).toBeInTheDocument();
  });
  ```

- [ ] Run: `npx jest AppLayout` → **PASSED**
- [ ] Commit: `git commit -m "feat(chat): mount AgentChatWindow in AppLayout, wrap AgentChatProvider in App"`

---

## Task 11 — Dashboard linkage: Overview Analyze button

**Files:**
- Edit: `frontend/src/pages/Overview/index.tsx`

### Steps

- [ ] **Step 1: Replace direct API call with `useAgentChat().send()`**

  In the Overview page, find the "开始分析" / "Analyze" button handler. Replace the existing `useMutation` dispatch with:

  ```typescript
  // In Overview/index.tsx — add import:
  import { useAgentChat } from "../../hooks/useAgentChat";

  // Inside component:
  const { send: sendToAgent, setIsOpen: openChat } = useAgentChat();

  // In button onClick:
  const handleAnalyze = () => {
    openChat(true);
    sendToAgent(`分析当前会话的错题，benchmark: ${filters.benchmark}, 模型版本: ${filters.model_version}`);
  };
  ```

  > **Note:** This makes the Analyze button send a natural-language instruction to the Agent, which appears in the chat window and triggers the backend Analyze subgraph — the two interaction channels are now equivalent (§3.5 of design doc).

- [ ] **Step 2: Verify existing Overview tests still pass**
  ```
  npx jest Overview
  ```
  Expected: **PASSED** (update test if needed to mock `useAgentChat`).

---

## Task 12 — Full test suite pass

- [ ] Run complete frontend test suite:
  ```
  cd frontend && npx jest --coverage
  ```
- [ ] Expected: all tests pass, no regressions in Plans 07–10 components
- [ ] Agent Chat coverage targets:
  - `contexts/AgentChatContext.tsx` ≥ 90%
  - `hooks/useAgentWebSocket.ts` ≥ 85%
  - `hooks/useAgentChat.ts` ≥ 85%
  - `components/AgentChatWindow/` ≥ 80%
- [ ] Commit: `git commit -m "feat(chat): complete Agent Chat Window frontend implementation"`

---

## Test Summary

| Task | Tests | Key assertions |
|------|-------|----------------|
| Task 2 — AgentChatContext | 2 | Initial state; setIsOpen toggle |
| Task 3 — useAgentWebSocket | 3 | WS connects; send serializes; token dispatch |
| Task 4 — useAgentChat | 2 | User msg appended; streaming placeholder added |
| Task 5 — ChatActionRouter | 3 | navigate(); setFilter(); null no-op |
| Task 6 — TypingIndicator | 1 | 3 animated dots rendered |
| Task 6 — MessageList | 2 | All messages rendered; streaming shows indicator |
| Task 6 — MessageInput | 3 | Send on click; clears input; Enter key sends |
| Task 7 — AgentChatWindow | 2 | Float button present; click opens Drawer |
| Task 10 — AppLayout | 1 | Window mounted in layout |
| **Total** | **19** | |

---

## Handoff Contract for Future Plans

- **`useAgentChat().send(text)`** — any page/component can inject a message into the chat thread and trigger the Agent without opening the chat window manually.
- **`window.dispatchEvent(new CustomEvent("agent:highlight_record", { detail: { record_id } }))`** — record detail pages listen for this event to highlight a row (implement the listener in the Error Analysis page's table).
- **`AgentChatProvider`** must wrap the entire app (already done in `App.tsx`).
- **WebSocket URL**: constructed from `VITE_API_BASE_URL` env var (same as REST base URL, protocol swapped to `ws:`).
- **conversation_id** is persisted in `AgentChatContext` for the browser session. A full page reload starts a new conversation (no localStorage persistence by design — keeps implementation simple).
