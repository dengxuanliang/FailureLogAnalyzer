import { MessageOutlined } from "@ant-design/icons";
import { Badge, Drawer, FloatButton } from "antd";
import { useTranslation } from "react-i18next";
import { useAgentConversations } from "../../api/queries/agent";
import { useAgentChat } from "../../hooks/useAgentChat";
import { ChatActionRouter } from "./ChatActionRouter";
import { ConversationList } from "./ConversationList";
import { MessageInput } from "./MessageInput";
import { MessageList } from "./MessageList";

export function AgentChatWindow() {
  const { t } = useTranslation();
  const {
    messages,
    conversationId,
    isOpen,
    setIsOpen,
    isConnected,
    send,
    startNewConversation,
    resumeConversation,
    isResumingConversation,
    pendingAction,
    clearPendingAction,
  } = useAgentChat();
  const { data: conversations = [], isLoading: isLoadingConversations } = useAgentConversations();

  const unreadCount = !isOpen ? messages.filter((message) => message.role === "assistant").length : 0;

  return (
    <>
      <ChatActionRouter action={pendingAction} onHandled={clearPendingAction} />
      {!isOpen ? (
        <Badge count={unreadCount}>
          <FloatButton
            icon={<MessageOutlined />}
            tooltip={t("chat.open")}
            aria-label={t("chat.open")}
            onClick={() => setIsOpen(true)}
            style={{ insetInlineEnd: 24, insetBlockEnd: 24 }}
          />
        </Badge>
      ) : null}
      <Drawer
        title={`${t("chat.title")} · ${isConnected ? t("chat.connected") : t("chat.disconnected")}`}
        placement="right"
        width={380}
        open={isOpen}
        onClose={() => setIsOpen(false)}
        mask={false}
        styles={{ body: { display: "flex", flexDirection: "column", height: "100%", padding: 0 } }}
      >
        <ConversationList
          conversations={conversations}
          activeConversationId={conversationId}
          isLoading={isLoadingConversations}
          isResumingConversation={isResumingConversation}
          onSelectConversation={(nextConversationId) => void resumeConversation(nextConversationId)}
          onStartNewConversation={startNewConversation}
          labels={{
            recentConversations: t("chat.recentConversations"),
            newConversation: t("chat.newConversation"),
            noConversations: t("chat.noConversations"),
            loadingConversations: t("chat.loadingConversations"),
          }}
        />
        <MessageList messages={messages} />
        <MessageInput onSend={send} disabled={isResumingConversation} />
      </Drawer>
    </>
  );
}

export default AgentChatWindow;
