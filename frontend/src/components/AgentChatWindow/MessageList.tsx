import { Empty, Typography } from "antd";
import { useEffect, useRef } from "react";
import type { ChatMessage } from "../../types/agent";
import { TypingIndicator } from "./TypingIndicator";

interface MessageListProps {
  messages: ChatMessage[];
}

export function MessageList({ messages }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return <Empty description="Ask the agent to start analyzing" image={Empty.PRESENTED_IMAGE_SIMPLE} />;
  }

  return (
    <div style={{ display: "flex", flex: 1, flexDirection: "column", overflowY: "auto", gap: 8, padding: 12 }}>
      {messages.map((message) => (
        <div
          key={message.id}
          style={{
            alignSelf: message.role === "user" ? "flex-end" : "flex-start",
            background: message.role === "user" ? "#1677ff" : "#f5f5f5",
            borderRadius: 12,
            color: message.role === "user" ? "#fff" : "#000",
            maxWidth: "85%",
            padding: "8px 12px",
          }}
        >
          {message.isStreaming && message.content.length === 0 ? (
            <TypingIndicator />
          ) : (
            <Typography.Text style={{ color: "inherit", whiteSpace: "pre-wrap" }}>
              {message.content}
            </Typography.Text>
          )}
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
