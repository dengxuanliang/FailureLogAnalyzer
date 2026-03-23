import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type PropsWithChildren,
} from "react";
import type { ActionPayload, ChatMessage, ConnectionStatus } from "../types/agent";

export interface AgentChatContextValue {
  messages: ChatMessage[];
  conversationId: string | null;
  isOpen: boolean;
  isConnected: boolean;
  connectionStatus: ConnectionStatus;
  pendingAction: ActionPayload | null;
  setIsOpen: (open: boolean) => void;
  setIsConnected: (connected: boolean) => void;
  setConnectionStatus: (status: ConnectionStatus) => void;
  appendMessage: (message: ChatMessage) => void;
  appendToken: (token: string) => void;
  finalizeStreaming: () => void;
  replaceLastAssistantMessage: (message: ChatMessage) => void;
  setConversationId: (id: string | null) => void;
  clearMessages: () => void;
  setMessages: (messages: ChatMessage[]) => void;
  setPendingAction: (action: ActionPayload | null) => void;
}

const AgentChatContext = createContext<AgentChatContextValue | undefined>(undefined);

export function AgentChatProvider({ children }: PropsWithChildren) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>("disconnected");
  const [pendingAction, setPendingAction] = useState<ActionPayload | null>(null);

  const appendMessage = useCallback((message: ChatMessage) => {
    setMessages((previous) => [...previous, message]);
  }, []);

  const appendToken = useCallback((token: string) => {
    setMessages((previous) => {
      if (previous.length === 0) {
        return previous;
      }

      const lastMessage = previous[previous.length - 1];
      if (lastMessage.role !== "assistant") {
        return previous;
      }

      return [
        ...previous.slice(0, -1),
        {
          ...lastMessage,
          content: `${lastMessage.content}${token}`,
          isStreaming: true,
        },
      ];
    });
  }, []);

  const finalizeStreaming = useCallback(() => {
    setMessages((previous) => {
      if (previous.length === 0) {
        return previous;
      }

      const lastMessage = previous[previous.length - 1];
      if (lastMessage.role !== "assistant") {
        return previous;
      }

      return [...previous.slice(0, -1), { ...lastMessage, isStreaming: false }];
    });
  }, []);

  const replaceLastAssistantMessage = useCallback((message: ChatMessage) => {
    setMessages((previous) => {
      if (previous.length === 0) {
        return [message];
      }

      const lastMessage = previous[previous.length - 1];
      if (lastMessage.role === "assistant") {
        return [...previous.slice(0, -1), { ...message, isStreaming: false }];
      }

      return [...previous, { ...message, isStreaming: false }];
    });
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
  }, []);

  const replaceMessages = useCallback((nextMessages: ChatMessage[]) => {
    setMessages(nextMessages);
  }, []);

  const setIsConnected = useCallback((connected: boolean) => {
    setConnectionStatus(connected ? "connected" : "disconnected");
  }, []);

  const value = useMemo<AgentChatContextValue>(
    () => ({
      messages,
      conversationId,
      isOpen,
      isConnected: connectionStatus === "connected",
      connectionStatus,
      pendingAction,
      setIsOpen,
      setIsConnected,
      setConnectionStatus,
      appendMessage,
      appendToken,
      finalizeStreaming,
      replaceLastAssistantMessage,
      setConversationId,
      clearMessages,
      setMessages: replaceMessages,
      setPendingAction,
    }),
    [
      messages,
      conversationId,
      isOpen,
      connectionStatus,
      pendingAction,
      setIsConnected,
      appendMessage,
      appendToken,
      finalizeStreaming,
      replaceLastAssistantMessage,
      clearMessages,
      replaceMessages,
    ],
  );

  return <AgentChatContext.Provider value={value}>{children}</AgentChatContext.Provider>;
}

export function useAgentChatContext() {
  const context = useContext(AgentChatContext);
  if (!context) {
    throw new Error("useAgentChatContext must be used within an AgentChatProvider");
  }
  return context;
}
