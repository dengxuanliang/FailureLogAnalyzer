import { useMutation, useQuery } from "@tanstack/react-query";
import apiClient from "../client";
import type {
  AgentChatRequest,
  AgentChatResponse,
  AgentConversationDetail,
  AgentConversationListItem,
} from "../../types/agent";

export const agentConversationKeys = {
  all: ["agentConversations"] as const,
  lists: () => [...agentConversationKeys.all, "list"] as const,
  detail: (conversationId: string | null) => [...agentConversationKeys.all, conversationId] as const,
};

export async function fetchAgentConversations() {
  const response = await apiClient.get<AgentConversationListItem[]>("/agent/conversations");
  return response.data;
}

export async function fetchAgentConversation(conversationId: string) {
  const response = await apiClient.get<AgentConversationDetail>(`/agent/conversations/${conversationId}`);
  return response.data;
}

export function useAgentConversations() {
  return useQuery({
    queryKey: agentConversationKeys.lists(),
    queryFn: fetchAgentConversations,
  });
}

export function useAgentConversation(conversationId: string | null) {
  return useQuery({
    queryKey: agentConversationKeys.detail(conversationId),
    queryFn: () => fetchAgentConversation(conversationId as string),
    enabled: Boolean(conversationId),
  });
}

export function useAgentChatMutation() {
  return useMutation<AgentChatResponse, Error, AgentChatRequest>({
    mutationFn: async (payload) => {
      const response = await apiClient.post<AgentChatResponse>("/agent/chat", payload);
      return response.data;
    },
  });
}
