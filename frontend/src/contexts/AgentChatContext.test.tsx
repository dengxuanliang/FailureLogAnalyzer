import { act, render, screen } from "@testing-library/react";
import { AgentChatProvider, useAgentChatContext } from "./AgentChatContext";

function TestConsumer() {
  const {
    messages,
    conversationId,
    isOpen,
    isConnected,
    pendingAction,
    setIsOpen,
    setIsConnected,
    appendMessage,
    appendToken,
    finalizeStreaming,
    setConversationId,
    setPendingAction,
  } = useAgentChatContext();

  return (
    <div>
      <span data-testid="msg-count">{messages.length}</span>
      <span data-testid="last-content">{messages[messages.length - 1]?.content ?? ""}</span>
      <span data-testid="conv-id">{conversationId ?? "null"}</span>
      <span data-testid="is-open">{String(isOpen)}</span>
      <span data-testid="is-connected">{String(isConnected)}</span>
      <span data-testid="pending-action">{pendingAction?.type ?? "null"}</span>
      <button type="button" onClick={() => setIsOpen(true)}>open</button>
      <button type="button" onClick={() => setIsConnected(true)}>connect</button>
      <button
        type="button"
        onClick={() =>
          appendMessage({
            id: "assistant-stream",
            role: "assistant",
            content: "",
            timestamp: "2026-03-21T00:00:00Z",
            isStreaming: true,
          })
        }
      >
        add streaming
      </button>
      <button type="button" onClick={() => appendToken("hello")}>append token</button>
      <button type="button" onClick={() => finalizeStreaming()}>finalize</button>
      <button type="button" onClick={() => setConversationId("conv-1")}>set conversation</button>
      <button
        type="button"
        onClick={() => setPendingAction({ type: "navigate", page: "compare" })}
      >
        set action
      </button>
    </div>
  );
}

describe("AgentChatProvider", () => {
  it("initial state has empty messages and no conversationId", () => {
    render(
      <AgentChatProvider>
        <TestConsumer />
      </AgentChatProvider>,
    );

    expect(screen.getByTestId("msg-count")).toHaveTextContent("0");
    expect(screen.getByTestId("conv-id")).toHaveTextContent("null");
    expect(screen.getByTestId("is-open")).toHaveTextContent("false");
    expect(screen.getByTestId("is-connected")).toHaveTextContent("false");
    expect(screen.getByTestId("pending-action")).toHaveTextContent("null");
  });

  it("updates streaming message state and metadata through context actions", () => {
    render(
      <AgentChatProvider>
        <TestConsumer />
      </AgentChatProvider>,
    );

    act(() => {
      screen.getByRole("button", { name: "open" }).click();
      screen.getByRole("button", { name: "connect" }).click();
      screen.getByRole("button", { name: "add streaming" }).click();
      screen.getByRole("button", { name: "append token" }).click();
      screen.getByRole("button", { name: "finalize" }).click();
      screen.getByRole("button", { name: "set conversation" }).click();
      screen.getByRole("button", { name: "set action" }).click();
    });

    expect(screen.getByTestId("msg-count")).toHaveTextContent("1");
    expect(screen.getByTestId("last-content")).toHaveTextContent("hello");
    expect(screen.getByTestId("conv-id")).toHaveTextContent("conv-1");
    expect(screen.getByTestId("is-open")).toHaveTextContent("true");
    expect(screen.getByTestId("is-connected")).toHaveTextContent("true");
    expect(screen.getByTestId("pending-action")).toHaveTextContent("navigate");
  });
});
