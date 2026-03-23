import { useMemo } from "react";
import type { AgentConversationListItem } from "../../types/agent";

interface ConversationListProps {
  conversations: AgentConversationListItem[];
  activeConversationId: string | null;
  isLoading: boolean;
  isResumingConversation: boolean;
  onSelectConversation: (conversationId: string) => void;
  onStartNewConversation: () => void;
  labels: {
    recentConversations: string;
    newConversation: string;
    noConversations: string;
    loadingConversations: string;
  };
}

export function ConversationList({
  conversations,
  activeConversationId,
  isLoading,
  isResumingConversation,
  onSelectConversation,
  onStartNewConversation,
  labels,
}: ConversationListProps) {
  const sortedConversations = useMemo(
    () =>
      [...conversations].sort(
        (left, right) => new Date(right.updated_at).getTime() - new Date(left.updated_at).getTime(),
      ),
    [conversations],
  );

  return (
    <div style={{ borderBottom: "1px solid #f0f0f0", padding: 12 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
        <strong>{labels.recentConversations}</strong>
        <button type="button" onClick={onStartNewConversation} disabled={isResumingConversation}>
          {labels.newConversation}
        </button>
      </div>

      {isLoading ? <div>{labels.loadingConversations}</div> : null}
      {!isLoading && sortedConversations.length === 0 ? <div>{labels.noConversations}</div> : null}
      {!isLoading && sortedConversations.length > 0 ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 8, maxHeight: 140, overflowY: "auto" }}>
          {sortedConversations.map((conversation) => (
            <button
              key={conversation.conversation_id}
              type="button"
              onClick={() => onSelectConversation(conversation.conversation_id)}
              disabled={isResumingConversation}
              style={{
                textAlign: "left",
                border: "1px solid #d9d9d9",
                borderRadius: 6,
                padding: "6px 8px",
                background:
                  conversation.conversation_id === activeConversationId ? "rgba(22, 119, 255, 0.1)" : "#fff",
              }}
            >
              <div style={{ fontSize: 12, color: "#595959" }}>
                {new Date(conversation.updated_at).toLocaleString()}
              </div>
              <div style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                {conversation.last_message || conversation.conversation_id}
              </div>
            </button>
          ))}
        </div>
      ) : null}
    </div>
  );
}
