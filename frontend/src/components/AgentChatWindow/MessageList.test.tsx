import { jest } from "@jest/globals";
import { render, screen } from "@testing-library/react";
import type { ChatMessage } from "@/types/agent";
import { MessageList } from "./MessageList";

const originalScrollIntoView = HTMLElement.prototype.scrollIntoView;

const messages: ChatMessage[] = [
  { id: "1", role: "user", content: "Hello", timestamp: "2026-03-20T00:00:00Z" },
  { id: "2", role: "assistant", content: "Hi there!", timestamp: "2026-03-20T00:00:01Z" },
];

describe("MessageList", () => {
  beforeAll(() => {
    HTMLElement.prototype.scrollIntoView = jest.fn();
  });

  afterAll(() => {
    HTMLElement.prototype.scrollIntoView = originalScrollIntoView;
  });

  it("renders all messages", () => {
    render(<MessageList messages={messages} />);
    expect(screen.getByText("Hello")).toBeInTheDocument();
    expect(screen.getByText("Hi there!")).toBeInTheDocument();
  });

  it("shows TypingIndicator for a streaming assistant message", () => {
    render(
      <MessageList
        messages={[
          ...messages,
          {
            id: "3",
            role: "assistant",
            content: "",
            timestamp: "2026-03-20T00:00:02Z",
            isStreaming: true,
          },
        ]}
      />,
    );

    expect(document.querySelectorAll(".typing-dot")).toHaveLength(3);
  });
});
