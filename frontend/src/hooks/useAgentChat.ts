import { useCallback, useMemo } from "react";
import { useAgentChatMutation } from "../api/queries/agent";
import { useAgentChatContext } from "../contexts/AgentChatContext";
import { useGlobalFilters } from "./useGlobalFilters";
import { useAgentWebSocket } from "./useAgentWebSocket";
import type { ActionPayload, AgentChatRequest, ChatMessage } from "../types/agent";

const createLocalId = () => {
  if (typeof globalThis.crypto !== "undefined" && typeof globalThis.crypto.randomUUID === "function") {
    return globalThis.crypto.randomUUID();
  }

  return `agent-${Date.now()}-${Math.random().toString(16).slice(2)}`;
};

const buildAgentWebSocketUrl = () => {
  const env = (import.meta.env ?? {}) as Partial<ImportMetaEnv>;
  const apiBaseUrl = env.VITE_API_BASE_URL ?? "/api/v1";

  if (apiBaseUrl.startsWith("http://") || apiBaseUrl.startsWith("https://")) {
    return `${apiBaseUrl.replace(/^http/, "ws")}/ws/agent`;
  }

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${protocol}//${window.location.host}${apiBaseUrl}/ws/agent`;
};

const createAssistantMessage = (content: string): ChatMessage => ({
  id: createLocalId(),
  role: "assistant",
  content,
  timestamp: new Date().toISOString(),
  isStreaming: false,
});

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
    isConnected,
    isOpen,
    setIsOpen,
    setIsConnected,
    appendMessage,
    appendToken,
    finalizeStreaming,
    replaceLastAssistantMessage,
    setConversationId,
    pendingAction,
    setPendingAction,
  } = useAgentChatContext();
  const { benchmark, model_version, time_range_start, time_range_end } = useGlobalFilters();
  const agentChatMutation = useAgentChatMutation();

  const websocketUrl = useMemo(() => buildAgentWebSocketUrl(), []);

  const { send: sendWebSocket } = useAgentWebSocket(websocketUrl, {
    onConnected: () => setIsConnected(true),
    onDisconnected: () => setIsConnected(false),
    onConversationId: (nextConversationId) => setConversationId(nextConversationId),
    onToken: (token) => {
      if (token === "\u0000") {
        finalizeStreaming();
        return;
      }

      appendToken(token);
    },
    onMessage: (message) => {
      replaceLastAssistantMessage({ ...message, isStreaming: false });
      if (message.action) {
        setPendingAction(message.action);
      }
    },
    onAction: (action) => {
      setPendingAction(action);
    },
  });

  const clearPendingAction = useCallback(() => {
    setPendingAction(null);
  }, [setPendingAction]);

  const send = useCallback(
    (text: string) => {
      const trimmed = text.trim();
      if (!trimmed) {
        return;
      }

      appendMessage({
        id: createLocalId(),
        role: "user",
        content: trimmed,
        timestamp: new Date().toISOString(),
      });

      appendMessage({
        id: createLocalId(),
        role: "assistant",
        content: "",
        timestamp: new Date().toISOString(),
        isStreaming: true,
      });

      const payload: AgentChatRequest = {
        message: trimmed,
        conversation_id: conversationId,
        filters: {
          benchmark: benchmark ?? undefined,
          model_version: model_version ?? undefined,
          time_range_start: time_range_start ?? undefined,
          time_range_end: time_range_end ?? undefined,
        },
      };

      const sentOverWebSocket = sendWebSocket(payload);
      if (sentOverWebSocket) {
        return;
      }

      agentChatMutation.mutate(payload, {
        onSuccess: (response) => {
          setConversationId(response.conversation_id);
          const finalAssistantMessage =
            response.messages.filter((message) => message.role === "assistant").slice(-1)[0] ??
            createAssistantMessage(response.reply);
          replaceLastAssistantMessage({ ...finalAssistantMessage, isStreaming: false });
          if (response.action) {
            setPendingAction(response.action);
          }
        },
        onError: () => {
          replaceLastAssistantMessage(createAssistantMessage("Unable to reach the agent right now."));
        },
      });
    },
    [
      appendMessage,
      agentChatMutation,
      benchmark,
      conversationId,
      model_version,
      replaceLastAssistantMessage,
      sendWebSocket,
      setConversationId,
      setPendingAction,
      time_range_end,
      time_range_start,
    ],
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
