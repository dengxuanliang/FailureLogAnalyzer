import { MessageOutlined } from "@ant-design/icons";
import { Badge, Drawer, FloatButton } from "antd";
import { useTranslation } from "react-i18next";
import { useAgentChat } from "../../hooks/useAgentChat";
import { ChatActionRouter } from "./ChatActionRouter";
import { MessageInput } from "./MessageInput";
import { MessageList } from "./MessageList";

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
        <MessageList messages={messages} />
        <MessageInput onSend={send} disabled={false} />
      </Drawer>
    </>
  );
}

export default AgentChatWindow;
