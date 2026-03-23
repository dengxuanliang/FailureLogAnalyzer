import { useQueryClient } from "@tanstack/react-query";
import { useCallback, useMemo, useState } from "react";
import { agentConversationKeys, fetchAgentConversation, useAgentChatMutation } from "../api/queries/agent";
import { useAuth } from "../contexts/AuthContext";
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

const buildAgentWebSocketUrl = (token: string | null) => {
  const env = (import.meta.env ?? {}) as Partial<ImportMetaEnv>;
  const apiBaseUrl = env.VITE_API_BASE_URL ?? "/api/v1";
  const searchParams = new URLSearchParams();
  if (token) {
    searchParams.set("token", token);
  }

  if (apiBaseUrl.startsWith("http://") || apiBaseUrl.startsWith("https://")) {
    const baseUrl = `${apiBaseUrl.replace(/^http/, "ws")}/ws/agent`;
    return searchParams.size > 0 ? `${baseUrl}?${searchParams.toString()}` : baseUrl;
  }

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const baseUrl = `${protocol}//${window.location.host}${apiBaseUrl}/ws/agent`;
  return searchParams.size > 0 ? `${baseUrl}?${searchParams.toString()}` : baseUrl;
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
  isResumingConversation: boolean;
  setIsOpen: (open: boolean) => void;
  send: (text: string) => void;
  startNewConversation: () => void;
  resumeConversation: (conversationId: string) => Promise<void>;
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
    setMessages,
    clearMessages,
    pendingAction,
    setPendingAction,
  } = useAgentChatContext();
  const [isResumingConversation, setIsResumingConversation] = useState(false);
  const queryClient = useQueryClient();
  const { token } = useAuth();
  const { benchmark, model_version, time_range_start, time_range_end } = useGlobalFilters();
  const agentChatMutation = useAgentChatMutation();

  const websocketUrl = useMemo(() => buildAgentWebSocketUrl(token), [token]);

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

  const startNewConversation = useCallback(() => {
    setConversationId(null);
    clearMessages();
    setPendingAction(null);
  }, [clearMessages, setConversationId, setPendingAction]);

  const resumeConversation = useCallback(
    async (nextConversationId: string) => {
      if (!nextConversationId) {
        return;
      }

      setIsResumingConversation(true);
      try {
        const conversation = await fetchAgentConversation(nextConversationId);
        setConversationId(conversation.conversation_id);
        setMessages(conversation.messages);
        setPendingAction(null);
        queryClient.setQueryData(agentConversationKeys.detail(nextConversationId), conversation);
      } catch {
        // Keep current local state when resuming fails.
      } finally {
        setIsResumingConversation(false);
      }
    },
    [queryClient, setConversationId, setMessages, setPendingAction],
  );

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
          void queryClient.invalidateQueries({ queryKey: agentConversationKeys.lists() });
          queryClient.setQueryData(agentConversationKeys.detail(response.conversation_id), response);
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
      queryClient,
    ],
  );

  return {
    messages,
    conversationId,
    isConnected,
    isOpen,
    isResumingConversation,
    setIsOpen,
    send,
    startNewConversation,
    resumeConversation,
    pendingAction,
    clearPendingAction,
  };
}
